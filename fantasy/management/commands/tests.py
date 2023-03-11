from unittest.mock import patch, Mock, call
from typing import Dict
from datetime import date, time, timedelta
import logging

from django.test import TestCase
from django.utils import timezone
from django.core import mail

from integrations.types import PositionMap
from integrations import live_bumps, anu_html, camfm, ourcs
from core.tests import exists

from ... import models
from ...constants import Locations, Series, Clubs, Genders, money
from ...game_tools import evaluate_all_investments
from ..actions import create_days
from .game_start import Command as GameStart
from .game_advance import Command as GameAdvance
from .renumbered_crew import Command as RenumberedCrew
from .update_live_bumps import Command as UpdateLiveBumps
from .wipe_live_bumps import Command as WipeLiveBumps
from . import utils, parsers

logging.disable(logging.CRITICAL)


def prepare_event(series: Series, start_date: date) -> models.Event:
    event = models.Event.objects.create(
        series = series,
        year = start_date.year,
        tag = f'{series.label.lower()}{start_date.year}',
    )
    create_days(event, start_date, time(12, 00))
    return event


def roll_over_positions(series: str, year: int, day_number: int) -> PositionMap:
    days = list(exists(models.Event.objects.first()).days.all())
    positions = days[day_number - 2].ranking.all()
    return {
        position.crew.as_tuple(): (position.rank, True)
        for position in positions
    }


def dummy_positions_by_gender(
    series: str,
    year: int,
    gender: Genders,
    day_number: int,
) -> Dict[models.Crew.Tuple, int]:
    return {
        (Clubs.HERT, gender, 1): day_number + 1,
        (Clubs.LADY, gender, 1): day_number + 2,
    }


def dummy_start_order_source(_: Locations, __: str) -> parsers.StartOrderSource:
    return {
        'source': parsers.Sources.NOOP,
        'function': lambda series, year, day: [{
            'gender': '',
            'number': 0,
            'size': 0,
            'race_time': time(12, 00),
            'crews': [],
            'finalised': False,
        }],
    }


start_order_source_patch = patch(
    'fantasy.management.commands.parsers.get_validated_start_order_source',
    side_effect = dummy_start_order_source,
)


class Test__Utils(TestCase):
    fixtures = ['dev_event', 'seats']
    event: models.Event
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = prepare_event(Series.TORPIDS, timezone.now().date())
    
    
    def test__crew_map__empty(self) -> None:
        """Returns an empty map if no crews supplied."""
        
        crew_map = utils.create_crew_tuple_map([])
        self.assertEqual(crew_map, {})
    
    
    def test__crew_map__create(self) -> None:
        """Creates missing crew records."""
        
        crew_lady = (Clubs.LADY, Genders.WOMEN, 1)
        crew_wolf = (Clubs.WOLF, Genders.WOMEN, 2)
        crews_in_event = [crew_lady, crew_wolf]
        
        crew_map = utils.create_crew_tuple_map(crews_in_event)
        self.assertEqual(set(crew_map.keys()), set(crews_in_event))
        
        self.assertEqual(models.Crew.objects.count(), 2)
    
    
    def test__crew_map__use_existing(self) -> None:
        """References existing crew records where possible."""
        
        crew_hert = models.Crew.objects.create(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)
        crew_newc = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.WOMEN, rank = 2)
        models.Crew.objects.create(club = Clubs.MANS, gender = Genders.MEN, rank = 1)
        
        crews_in_event = [crew_hert.as_tuple(), crew_newc.as_tuple()]
        
        crew_map = utils.create_crew_tuple_map(crews_in_event)
        self.assertEqual(set(crew_map.keys()), set(crews_in_event))
        
        self.assertEqual(crew_map[crew_hert.as_tuple()], crew_hert)
        self.assertEqual(crew_map[crew_newc.as_tuple()], crew_newc)
        self.assertEqual(models.Crew.objects.count(), 3)
    
    
    def test__crew_map__mixed(self) -> None:
        """Will both create a reference crew records as required."""
        
        crew_lady_tuple = (Clubs.LADY, Genders.WOMEN, 1)
        crew_wolf_tuple = (Clubs.WOLF, Genders.WOMEN, 2)
        
        crew_hert = models.Crew.objects.create(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)
        crew_newc = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.WOMEN, rank = 2)
        models.Crew.objects.create(club = Clubs.MANS, gender = Genders.MEN, rank = 1)
        
        crews_in_event = [
            crew_lady_tuple,
            crew_wolf_tuple,
            crew_hert.as_tuple(),
            crew_newc.as_tuple(),
        ]
        
        crew_map = utils.create_crew_tuple_map(crews_in_event)
        self.assertEqual(set(crew_map.keys()), set(crews_in_event))
        
        self.assertEqual(crew_map[crew_hert.as_tuple()], crew_hert)
        self.assertEqual(crew_map[crew_newc.as_tuple()], crew_newc)
        self.assertEqual(models.Crew.objects.count(), 5)
    
    
    def test__rankings__first_day(self) -> None:
        """The event information and automatically-calculated day are passed to the source."""
        
        source_mock = Mock(return_value = {})
        
        utils.load_crew_rankings(source_mock, exists(self.event.days.first()))
        source_mock.assert_called_once_with(self.event.series, self.event.year, 1)
    
    
    def test__rankings__last_day(self) -> None:
        """The event information and automatically-calculated day are passed to the source."""
        
        source_mock = Mock(return_value = {})
        
        utils.load_crew_rankings(source_mock, exists(self.event.days.last()))
        source_mock.assert_called_once_with(self.event.series, self.event.year, 5)
   
   
    def test__rankings__create(self) -> None:
        """The rankings provided by the source are stored against the day."""
        
        rankings = {
            (Clubs.LADY, Genders.WOMEN, 1): (13, True),
            (Clubs.WOLF, Genders.WOMEN, 2): (21, True),
            (Clubs.HERT, Genders.WOMEN, 1): (8, True),
            (Clubs.NEWC, Genders.WOMEN, 2): (37, False),
            (Clubs.MANS, Genders.MEN, 1): (25, True),
        }
        source_mock = Mock(return_value = rankings)
        
        utils.load_crew_rankings(source_mock, exists(self.event.days.first()))
        
        positions = models.Position.objects.all()
        self.assertEqual(len(positions), 5)
        for position in positions:
            with self.subTest(crew = str(position.crew)):
                self.assertEqual(position.rank, rankings[position.crew.as_tuple()][0])
    
    
    def test__crew_lists__source_call(self) -> None:
        """The event information is passed to the source."""
        
        source_mock = Mock(return_value = {})
        
        utils.load_crew_lists(source_mock, self.event)
        source_mock.assert_called_once_with(self.event.series, self.event.year)
    
    
    def test__crew_lists__create(self) -> None:
        """The crew lists provided by the source are stored against the event."""
        
        crew_lady = models.Crew.objects.create(club = Clubs.LADY, gender = Genders.WOMEN, rank = 1)
        crew_wolf = models.Crew.objects.create(club = Clubs.WOLF, gender = Genders.WOMEN, rank = 2)
        
        day = exists(self.event.days.first())
        models.Position.objects.create(day = day, crew = crew_lady, rank = 13)
        models.Position.objects.create(day = day, crew = crew_wolf, rank = 21)
        
        crew_lists = {
            crew_lady.as_tuple(): {1: 'L1', 2: 'L2', 3: 'L3', 8: 'L8', 9: 'L9'},
            crew_wolf.as_tuple(): {1: 'W1', 2: 'W2', 3: 'W3', 8: 'W8', 9: 'W9'},
        }
        source_mock = Mock(return_value = crew_lists)
        
        utils.load_crew_lists(source_mock, self.event)
        
        athletes = models.Athlete.objects.all()
        self.assertEqual(len(athletes), 10)
        for athlete in athletes:
            with self.subTest(athlete = athlete.name):
                self.assertEqual(
                    crew_lists[athlete.crew.as_tuple()][athlete.seat.id],
                    athlete.name,
                )


class Test__Game_Start(TestCase):
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__date_year__default(self, _: Mock, __: Mock) -> None:
        """By default, the game is set to start in five days' time."""
        
        expected_date = timezone.now().date() + timedelta(5)
        GameStart().handle(series = 'torpids', date = None, year = None)
        
        event = exists(models.Event.objects.first())
        self.assertEqual(event.first_day.date, expected_date)
        self.assertEqual(event.year, expected_date.year)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__date_year__start_date(self, _: Mock, __: Mock) -> None:
        """A specific start date can be provided to start the game on that date."""
        
        expected_date = date.fromisoformat('2022-11-30')
        GameStart().handle(series = 'torpids', date = expected_date, year = None)
        
        event = exists(models.Event.objects.first())
        self.assertEqual(event.first_day.date, expected_date)
        self.assertEqual(event.year, expected_date.year)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__date_year__year(self, _: Mock, __: Mock) -> None:
        """A year can be provided to use data from that year with the default start date."""
        
        expected_date = timezone.now().date() + timedelta(5)
        GameStart().handle(series = 'torpids', date = None, year = 2013)
        
        event = exists(models.Event.objects.first())
        self.assertEqual(event.first_day.date, expected_date)
        self.assertEqual(event.year, 2013)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__date_year__both(self, _: Mock, __: Mock) -> None:
        """When both are provided, the provided year overrides the year of the given date."""
        
        expected_date = date.fromisoformat('2022-11-30')
        GameStart().handle(series = 'torpids', date = expected_date, year = 2013)
        
        event = exists(models.Event.objects.first())
        self.assertEqual(event.first_day.date, expected_date)
        self.assertEqual(event.year, 2013)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__event_source__demo_default(self, _: Mock, start_order_mock: Mock) -> None:
        """The default source for Demo events is the demo handler."""
        self.skipTest('Temporarily invalid')
        
        GameStart().handle(series = 'demo', date = None, year = None)
        start_order_mock.assert_called_once_with(Locations.DEMO, '')
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__event_source__oxford_default(self, _: Mock, start_order_mock: Mock) -> None:
        """The default source for Oxford events is Live Bumps."""
        
        GameStart().handle(series = 'torpids', date = None, year = None)
        start_order_mock.assert_called_once_with(Locations.OXFORD, '')
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__event_source__oxford_alternate(
        self,
        _: Mock,
        start_order_mock: Mock,
    ) -> None:
        """Anu can be used as an alternative source for Oxford events."""
        
        GameStart().handle(series = 'torpids', date = None, year = None, source = 'anu-html')
        start_order_mock.assert_called_once_with(Locations.OXFORD, 'anu-html')
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__event_source__cambridge_default(
        self,
        _: Mock,
        start_order_mock: Mock,
    ) -> None:
        """The default source for Cambridge events is CamFM."""
        
        GameStart().handle(series = 'mays', date = None, year = None)
        start_order_mock.assert_called_once_with(Locations.CAMBRIDGE, '')
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__event_source__invalid(self, _: Mock, start_order_mock: Mock) -> None:
        """An error is thrown if the preferred source is invalid."""
        self.skipTest('Temporarily invalid')
        
        with self.assertRaises(AssertionError):
            GameStart().handle(
                series = 'torpids',
                date = None,
                year = None,
                source = 'camfm',
            )
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__crew_lists_source__demo_default(
        self,
        crew_lists_mock: Mock,
        __: Mock,
    ) -> None:
        """The default crew list source for Demo events is the demo handler."""
        self.skipTest('Temporarily invalid')
        
        GameStart().handle(series = 'demo', date = None, year = None)
        
        event = exists(models.Event.objects.first())
        crew_lists_mock.assert_called_once_with(parsers._demo_crew_lists, event)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__crew_lists_source__oxford_default(
        self,
        crew_lists_mock: Mock,
        __: Mock,
    ) -> None:
        """The default crew list source for Oxford events is Live Bumps."""
        
        GameStart().handle(series = 'torpids', date = None, year = None)
        
        event = exists(models.Event.objects.first())
        crew_lists_mock.assert_called_once_with(live_bumps.get_crew_lists, event)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__crew_lists_source__oxford_alternate(
        self,
        crew_lists_mock: Mock,
        __: Mock,
    ) -> None:
        """OURCs can be used as an alternative crew list source for Oxford events."""
        
        GameStart().handle(series = 'torpids', date = None, year = None, crew_lists = 'ourcs')
        
        event = exists(models.Event.objects.first())
        crew_lists_mock.assert_called_once_with(ourcs.get_crew_lists, event)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__crew_lists_source__cambridge_default(
        self,
        crew_lists_mock: Mock,
        __: Mock,
    ) -> None:
        """The default crew list source for Cambridge events is no-op source."""
        
        GameStart().handle(series = 'mays', date = None, year = None)
        
        event = exists(models.Event.objects.first())
        crew_lists_mock.assert_called_once_with(parsers._noop_crew_lists, event)
    
    
    @start_order_source_patch
    @patch('fantasy.management.commands.utils.load_crew_lists')
    def test__handle__crew_lists_source__invalid(self, crew_lists_mock: Mock, __: Mock) -> None:
        """An error is thrown if the preferred crew list source is invalid."""
        
        with self.assertRaises(AssertionError):
            GameStart().handle(
                series = 'torpids',
                date = None,
                year = None,
                crew_lists = 'camfm',
            )


class Test__Game_Advance(TestCase):
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
        
        GameAdvance.advance_core(self.day, roll_over_positions)
        
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
            GameAdvance.advance_core(self.day, roll_over_positions)
        
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
            GameAdvance.advance_core(self.day, roll_over_positions)
        
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
        
        GameAdvance.advance_core(self.day, roll_over_positions, override_hold = True)
        
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
            GameAdvance.advance_core(self.day, roll_over_positions)
        
        self.day.refresh_from_db()
        self.assertFalse(self.day.advanced)
        self.assertEqual(self.day.next.ranking.count(), 0)
        self.assertEqual(self.day.next.purchases.count(), 0)
        
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_balance, money.INITIAL_BALANCE)
    
    
    @patch.object(GameAdvance, 'advance_core')
    def test__perform__success(self, core_mock: Mock) -> None:
        """No special actions are performed upon success."""
        
        GameAdvance.perform_game_advance(roll_over_positions, self.event)
        core_mock.assert_called_once()
        
        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)
    
    
    @patch.object(GameAdvance, 'advance_core')
    def test__perform__unknown_core_error(self, core_mock: Mock) -> None:
        """Markets are held closed and an e-mail sent upon unknown core error."""
        
        core_mock.side_effect = ValueError('Unknown Error')
        
        GameAdvance.perform_game_advance(roll_over_positions, self.event)

        self.event.refresh_from_db()
        self.assertTrue(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 1)
    
    
    @patch.object(GameAdvance, 'advance_core')
    def test__perform__core_rejection(self, core_mock: Mock) -> None:
        """No special actions are if the advance is rejected."""
        
        core_mock.side_effect = models.Day.DoesNotExist
        
        GameAdvance.perform_game_advance(roll_over_positions, self.event)

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__oxford_default_source(self, perform_mock: Mock) -> None:
        """Live Bumps is the default source used for Oxford events."""
        
        event = prepare_event(Series.TORPIDS, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(live_bumps.get_positions, event, False)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__oxford_specified_source(self, perform_mock: Mock) -> None:
        """Alternative sources can be used for Oxford events."""
        
        event = prepare_event(Series.TORPIDS, self.today)
        
        GameAdvance().handle(oxf_source = 'anu-html')
        perform_mock.assert_called_once_with(anu_html.get_positions, event, False)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__cambridge_default_source(self, perform_mock: Mock) -> None:
        """CamFM is the default source used for Cambridge events."""
        
        event = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(camfm.get_positions, event, False)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__demo_default_source(self, perform_mock: Mock) -> None:
        """An internal method is the default source used for Demo events."""
        
        event = prepare_event(Series.DEMO, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(parsers._demo_positions, event, False)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__two_events(self, perform_mock: Mock) -> None:
        """Two events can be updated simultaneously."""
        
        torpids = prepare_event(Series.TORPIDS, self.today)
        lents = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle()
        self.assertEqual(perform_mock.call_count, 2)
        perform_mock.assert_any_call(live_bumps.get_positions, torpids, False)
        perform_mock.assert_any_call(camfm.get_positions, lents, False)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__held_closed(self, perform_mock: Mock) -> None:
        """Events held closed are excluded from advancement."""
        
        torpids = prepare_event(Series.TORPIDS, self.today)
        torpids.market_held_closed = True
        torpids.save()
        lents = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(camfm.get_positions, lents, False)
        # ^ Does not call Torpids
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__held_closed_override(self, perform_mock: Mock) -> None:
        """The market hold status can be ignored on demand."""
        
        torpids = prepare_event(Series.TORPIDS, self.today)
        torpids.market_held_closed = True
        torpids.save()
        lents = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle(override = True)
        self.assertEqual(perform_mock.call_count, 2)
        perform_mock.assert_any_call(live_bumps.get_positions, torpids, True)
        perform_mock.assert_any_call(camfm.get_positions, lents, True)


class Test__Renumbered_Crew(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats']
    event: models.Event
    target_crew: models.Crew
    source_crew_rank: int
    source_crew_tpl: models.Crew.Tuple
    
    crew_list = {
        1: 'Test 1',
        2: 'Test 2',
        3: 'Test 3',
        4: 'Test 4',
        5: 'Test 5',
        6: 'Test 6',
        7: 'Test 7',
        8: 'Test 8',
        9: 'Test 9',
        10: 'Test 10',
    }
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())
        cls.event.series = Series.TORPIDS
        cls.event.save()
        
        cls.target_crew = exists(models.Crew.objects.filter(club = Clubs.HERT).first())
        cls.source_crew_rank = cls.target_crew.rank + 1
        cls.source_crew_tpl = (
            cls.target_crew.club,
            cls.target_crew.gender,
            cls.source_crew_rank,
        )
    
    
    def test__handle__event_missing(self) -> None:
        """Raises an error the event does not exist."""
        
        with self.assertRaises(models.Event.DoesNotExist):
            RenumberedCrew().handle(
                event_tag = 'other2022',
                club = self.target_crew.club,
                gender = self.target_crew.gender,
                new_rank = self.target_crew.rank,
                old_rank = self.source_crew_rank,
            )
    
    
    def test__handle__crew_not_in_event(self) -> None:
        """Raises an error if the target crew has no positions for the event."""
        
        with self.assertRaises(models.Crew.DoesNotExist):
            RenumberedCrew().handle(
                event_tag = self.event.tag,
                club = self.target_crew.club,
                gender = self.target_crew.gender,
                new_rank = self.source_crew_rank,
                old_rank = self.source_crew_rank + 1,
            )
    
    
    @patch.object(RenumberedCrew, 'perform_crew_list_update')
    def test__handle__valid(self, perform_mock: Mock) -> None:
        """Converts inputs to python objects for the `perform` function."""
        
        RenumberedCrew().handle(
            event_tag = self.event.tag,
            club = self.target_crew.club,
            gender = self.target_crew.gender,
            new_rank = self.target_crew.rank,
            old_rank = self.source_crew_rank,
        )
        
        perform_mock.assert_called_once_with(
            live_bumps.get_crew_lists,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
    
    
    @patch.object(RenumberedCrew, 'perform_crew_list_update')
    def test__handle__ourcs_source(self, perform_mock: Mock) -> None:
        """Can use the OURCs website as an alternative crew list source."""
        
        RenumberedCrew().handle(
            event_tag = self.event.tag,
            club = self.target_crew.club,
            gender = self.target_crew.gender,
            new_rank = self.target_crew.rank,
            old_rank = self.source_crew_rank,
            source = parsers.Sources.OURCS.value,
        )
        
        perform_mock.assert_called_once_with(
            ourcs.get_crew_lists,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
    
    
    def test__perform__source_call(self) -> None:
        """Calls the crew list source function with the event series and year."""
        
        source_mock = Mock(return_value = {self.source_crew_tpl: self.crew_list})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        source_mock.assert_called_once_with(self.event.series, self.event.year)
    
    
    def test__perform__no_crew_list_found(self) -> None:
        """Raises an error if no crew list is found for the source crew designation."""
        
        source_mock = Mock(return_value = {})
        
        with self.assertRaises(ValueError):
            RenumberedCrew.perform_crew_list_update(
                source_mock,
                self.event,
                self.target_crew,
                self.source_crew_tpl,
            )
    
    
    def test__perform__original_athletes_removed(self) -> None:
        """Athletes already recorded against the target crew should be removed."""
        
        for seat in range(1, 10):
            self.target_crew.crew_lists.create(
                event = self.event,
                seat_id = seat,
                name = f'Old {seat}',
            )
        
        source_mock = Mock(return_value = {self.source_crew_tpl: {}})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        self.assertFalse(list((
            self.target_crew.crew_lists
            .filter(event = self.event)
            .values_list('seat', 'name')
        )))
    
    
    def test__perform__new_athletes_added(self) -> None:
        """The crew list from the source crew should be loaded into the database."""
        
        source_mock = Mock(return_value = {self.source_crew_tpl: self.crew_list})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        self.assertEqual(
            list((
                self.target_crew.crew_lists
                .filter(event = self.event)
                .values_list('seat', 'name')
            )),
            [(seat, name) for seat, name in self.crew_list.items() if seat < 10],
        )


class Test__Live_Bumps(TestCase):
    
    now = timezone.now()
    
    @patch('integrations.anu_dat.get_positions_by_gender')
    def test__update__before_first_day(self, positions_mock: Mock) -> None:
        """No action is taken before the first day."""
        
        event = prepare_event(Series.TORPIDS, timezone.now().date() + timedelta(1))
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        positions_mock.assert_not_called()
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__first_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        event = prepare_event(Series.TORPIDS, timezone.now().date())
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 3)
            ],
        )
        start_order_mock.assert_called_once_with(event.series, event.year, Genders.WOMEN, 1)
        write_mock.assert_called_once_with(
            event.series,
            event.year,
            [
                dummy_positions_by_gender(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 3)
            ],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__second_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        event = prepare_event(Series.TORPIDS, timezone.now().date() - timedelta(1))
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 4)
            ],
        )
        start_order_mock.assert_called_once_with(event.series, event.year, Genders.WOMEN, 2)
        write_mock.assert_called_once_with(
            event.series,
            event.year,
            [
                dummy_positions_by_gender(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 4)
            ],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__final_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        event = prepare_event(Series.TORPIDS, timezone.now().date() - timedelta(3))
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
        start_order_mock.assert_called_once_with(event.series, event.year, Genders.WOMEN, 4)
        write_mock.assert_called_once_with(
            event.series,
            event.year,
            [
                dummy_positions_by_gender(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__after_event(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the whole event after it has finished."""
        
        event = prepare_event(Series.TORPIDS, timezone.now().date() - timedelta(4))
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
        start_order_mock.assert_not_called()
        write_mock.assert_called_once_with(
            event.series,
            event.year,
            [
                dummy_positions_by_gender(event.series, event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__racetime_filter(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Crews that have not raced on the current day are masked from the Live Bumps update."""
        
        start_order_mock.return_value = [
            {
                'race_time': (self.now - timedelta(minutes = 2)).time(),
                'crews': [((Clubs.HERT, Genders.WOMEN, 1), None)],
            },
            {
                'race_time': (self.now + timedelta(minutes = 2)).time(),
                'crews': [((Clubs.LADY, Genders.WOMEN, 1), None)],
            },
        ]
        
        event = prepare_event(Series.TORPIDS, timezone.now().date() - timedelta(1))
        UpdateLiveBumps().handle(
            series = Series.TORPIDS.label.lower(),
            year = event.year,
            gender = Genders.WOMEN.label.lower(),
        )
        
        expected_positions = [
            dummy_positions_by_gender(event.series, event.year, Genders.WOMEN, day_number)
            for day_number in range(1, 4)
        ]
        expected_positions[-1].pop((Clubs.LADY, Genders.WOMEN, 1))
        write_mock.assert_called_once_with(event.series, event.year, expected_positions)
    
    
    @patch('integrations.live_bumps.wipe_positions')
    def test__wipe(self, wipe_mock: Mock) -> None:
        """Provides an interface to the Live Bumps wipe command."""
        
        WipeLiveBumps().handle(series = 'torpids', year = 2022)
        
        wipe_mock.assert_called_once_with(Series.TORPIDS, 2022)

