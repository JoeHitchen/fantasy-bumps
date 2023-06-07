from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone
from django.core import mail

from integrations.types import PositionMap
from core.tests import exists

from ..constants import Clubs, Genders, money
from .. import models
from ..game_tools import evaluate_all_investments
from . import game_advance


def roll_over_positions(series: str, year: int, day_number: int) -> PositionMap:
    days = list(exists(models.Event.objects.first()).days.all())
    positions = days[day_number - 2].ranking.all()
    return {
        position.crew.as_tuple(): (position.rank, True)
        for position in positions
    }


class Test__PerformAdvance(TestCase):
    fixtures = ['dev_event', 'dev_days']
    
    event: models.Event
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = models.Event.objects.get(tag = 'devgame')
    
    
    @patch('fantasy.management.game_advance.advance_core')
    def test__perform__success(self, core_mock: Mock) -> None:
        """No special actions are performed upon success."""
        
        game_advance.perform_advance(self.event, roll_over_positions)
        core_mock.assert_called_once()
        
        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)
    
    
    @patch('fantasy.management.game_advance.advance_core')
    def test__perform__unknown_core_error(self, core_mock: Mock) -> None:
        """Markets are held closed and an e-mail sent upon unknown core error."""
        
        core_mock.side_effect = ValueError('Unknown Error')
        
        game_advance.perform_advance(self.event, roll_over_positions)
        core_mock.assert_called_once()

        self.event.refresh_from_db()
        self.assertTrue(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 1)
    
    
    @patch('fantasy.management.game_advance.advance_core')
    def test__perform__core_rejection(self, core_mock: Mock) -> None:
        """No special actions are if the advance is rejected."""
        
        core_mock.side_effect = models.Day.DoesNotExist
        
        game_advance.perform_advance(self.event, roll_over_positions)
        core_mock.assert_called_once()

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)


class Test__AdvanceCore(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']
    
    event: models.Event
    day: models.Day
    entry: models.GameEntry
    
    today = timezone.now().date()
    
    @classmethod
    def setUpTestData(cls) -> None:
        
        cls.event = models.Event.objects.get(tag = 'devgame')
        cls.day = cls.event.first_day
        crew_men = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.MEN, rank = 1)
        crew_women = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)
        
        team = models.Team.objects.get(user__username = 'DevTeam')
        cls.entry = team.entries.create(event = cls.day.event)
        
        for seat in models.Seat.objects.all():
            team.purchases.create(
                day = cls.day,
                seat = seat,
                crew = crew_men,
            )
            team.purchases.create(
                day = cls.day,
                seat = seat,
                crew = crew_women,
            )
    
    
    def test__core__success(self) -> None:
        """Loads positions, rolls over purchases, and awards payouts."""
        
        game_advance.advance_core(self.day, roll_over_positions)
        
        self.day.refresh_from_db()
        self.assertTrue(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 18)
        self.assertEqual(self.day.next.purchases.count(), 18)
        
        self.entry.refresh_from_db()
        self.assertNotEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__core__already_advanced(self) -> None:
        """The advance is rejected with an error if the day has already been advanced."""
        
        self.day.advanced = True
        self.day.save()
        
        with self.assertRaises(models.Day.DoesNotExist):
            game_advance.advance_core(self.day, roll_over_positions)
        
        self.day.refresh_from_db()
        self.assertTrue(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 0)
        self.assertEqual(self.day.next.purchases.count(), 0)
        
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__core__market_hold(self) -> None:
        """The advance is rejected with an error if the markets are held closed."""
        
        self.day.event.market_held_closed = True
        self.day.event.save()
        
        with self.assertRaises(models.Day.DoesNotExist):
            game_advance.advance_core(self.day, roll_over_positions)
        
        self.day.refresh_from_db()
        self.assertFalse(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 0)
        self.assertEqual(self.day.next.purchases.count(), 0)
        
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__core__market_hold_override(self) -> None:
        """The market hold rejection can be overriden if desired."""
        
        self.day.event.market_held_closed = True
        self.day.event.save()
        
        game_advance.advance_core(self.day, roll_over_positions, override_hold = True)
        
        self.day.refresh_from_db()
        self.assertTrue(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 18)
        self.assertEqual(self.day.next.purchases.count(), 18)
        
        self.entry.refresh_from_db()
        self.assertNotEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_balance, money.INITIAL_BALANCE)
    
    
    @patch('fantasy.game_tools.evaluate_all_investments')
    def test__core__error_rollback(self, evaluate_mock: Mock) -> None:
        """All changes should be rolled back if an error occurs."""
        
        def evaluate_then_error(day: models.Day) -> None:
            evaluate_all_investments(day)
            raise Exception('Rollback Test')
        
        evaluate_mock.side_effect = evaluate_then_error
        
        with self.assertRaises(Exception):
            game_advance.advance_core(self.day, roll_over_positions)
        
        self.day.refresh_from_db()
        self.assertFalse(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 0)
        self.assertEqual(self.day.next.purchases.count(), 0)
        
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_balance, money.INITIAL_BALANCE)

