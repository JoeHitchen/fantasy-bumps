from datetime import time
from unittest.mock import patch, Mock
from datetime import timedelta
import logging

from django.test import TestCase
from django.db import models as db
from django.utils import timezone
from django.contrib.auth import models as auth
from django.core import mail

from integrations.types import PositionMap
from core.tests import exists

from ..constants import Series, Clubs, Genders, money
from .. import models
from . import game_advance

logging.disable(logging.CRITICAL)


def roll_over_positions(series: str, year: int, day_number: int) -> PositionMap:
    days = list(exists(models.Event.objects.first()).days.all())
    positions = days[day_number - 2].ranking.all()
    return {
        position.crew.as_tuple(): (position.rank, True)
        for position in positions
    }


class Test__PerformAdvance(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']

    event: models.Event
    day: models.Day
    entry: models.GameEntry

    @classmethod
    def setUpTestData(cls) -> None:

        cls.event = models.Event.objects.get(tag = 'devgame')
        cls.event.series = Series.TORPIDS
        cls.event.save()

        date_shift = timezone.localtime().date() - cls.event.first_day.date
        cls.event.days.update(date = db.F('date') + date_shift, first_race_time = time(00, 00))
        last_day = exists(cls.event.days.last())
        last_day.first_race_time = None
        last_day.save()
        cls.day = cls.event.first_day  # Should now always be today with first race in the past

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


    def assertGameDidAdvance(self) -> None:
        """A group of assertions for game state after a successful advance."""

        self.day.refresh_from_db()
        self.assertTrue(self.day.advanced)

        next_day = exists(self.day.next)
        self.assertEqual(next_day.ranking.count(), 18)
        self.assertEqual(next_day.purchases.count(), 18)

        self.entry.refresh_from_db()
        self.assertNotEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertNotEqual(self.entry.womens_balance, money.INITIAL_BALANCE)


    def assertGameDidNotAdvance(self, advanced_flag: bool = False) -> None:
        """A group of assertions for game state after an unsuccessful advance."""

        self.day.refresh_from_db()
        self.assertEqual(self.day.advanced, advanced_flag)

        next_day = exists(self.day.next)
        self.assertEqual(next_day.ranking.count(), 0)
        self.assertEqual(next_day.purchases.count(), 0)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.entry.womens_balance, money.INITIAL_BALANCE)


    def test__core__success(self) -> None:
        """Loads positions, rolls over purchases, and awards payouts."""

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertTrue(success)
        self.assertGameDidAdvance()

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)


    def test__core__already_advanced(self) -> None:
        """The advance is rejected if the day has already been advanced."""

        self.day.advanced = True
        self.day.save()

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertFalse(success)
        self.assertGameDidNotAdvance(advanced_flag = True)

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)


    def test__core__market_hold(self) -> None:
        """The advance is rejected if the markets are held closed."""

        self.day.event.market_held_closed = True
        self.day.event.save()

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertFalse(success)
        self.assertGameDidNotAdvance()

        self.event.refresh_from_db()
        self.assertTrue(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 0)


    def test__core__market_hold_override(self) -> None:
        """The market hold rejection can be overriden if desired."""

        self.day.event.market_held_closed = True
        self.day.event.save()

        success = game_advance.perform_advance(
            self.event,
            roll_over_positions,
            override_hold = True,
        )

        self.assertTrue(success)
        self.assertGameDidAdvance()

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)  # Hold removed on override success
        self.assertEqual(len(mail.outbox), 0)


    @patch('fantasy.management.game_advance.evaluate_investments')
    def test__core__error_rollback(self, evaluate_mock: Mock) -> None:
        """All changes should be rolled back if an error occurs."""

        def evaluate_then_error(day: models.Day) -> None:
            game_advance.evaluate_investments(day)
            raise Exception('Rollback Test')

        evaluate_mock.side_effect = evaluate_then_error

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertFalse(success)
        self.assertGameDidNotAdvance()

        self.event.refresh_from_db()
        self.assertTrue(self.event.market_held_closed)
        self.assertEqual(len(mail.outbox), 1)


    @patch('fantasy.management.trophies.identify_new_veterans')
    @patch('fantasy.management.trophies.award_event_trophies')
    def test__trophies__last_day(self, trophies_mock: Mock, veterans_mock: Mock) -> None:
        """On the last day, the game advance additionally awards trophies."""

        self.event.days.update(date = db.F('date') - timedelta(1))

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertTrue(success)

        trophies_mock.assert_called_once_with(self.event)
        veterans_mock.assert_called_once_with(self.event)
        self.assertEqual(len(mail.outbox), 0)


    @patch('fantasy.management.trophies.identify_new_veterans')
    @patch('fantasy.management.trophies.award_event_trophies')
    def test__trophies__last_day_error(self, trophies_mock: Mock, veterans_mock: Mock) -> None:
        """A message should be sent if there is an error awarding trophies."""

        self.event.days.update(date = db.F('date') - timedelta(1))
        veterans_mock.side_effect = Exception('An unknown error occurred')

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertTrue(success)

        trophies_mock.assert_called_once_with(self.event)
        veterans_mock.assert_called_once_with(self.event)
        self.assertEqual(len(mail.outbox), 1)


    @patch('fantasy.management.trophies.identify_new_veterans')
    @patch('fantasy.management.trophies.award_event_trophies')
    def test__trophies__earlier_day(self, trophies_mock: Mock, veterans_mock: Mock) -> None:
        """On earlier days, the game advance should not awards trophies."""

        success = game_advance.perform_advance(self.event, roll_over_positions)

        self.assertTrue(success)

        trophies_mock.assert_not_called()
        veterans_mock.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)



class Test__PurchaseRollover(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']

    day: models.Day
    team: models.Team
    crews: list[models.Crew]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())
        cls.team = exists(models.Team.objects.first())
        cls.crews = list(models.Crew.objects.all())


    def test__without_athlete(self) -> None:
        """Copies all purchases to the next day, including null athlete references."""

        # Create simple set of purchases
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                seat = seat,
                crew = self.crews[seat.id],
            )

        # Test method
        game_advance.roll_over_purchases(self.day)

        self.assertEqual(
            list(self.day.purchases.values('team', 'crew', 'seat', 'athlete')),
            list(exists(self.day.next).purchases.values('team', 'crew', 'seat', 'athlete')),
        )


    def test__with_athlete(self) -> None:
        """Copies all purchases to the next day, including athlete references."""

        # Create athlete
        athlete = models.Athlete.objects.create(
            event = self.day.event,
            crew = self.crews[0],
            seat = exists(models.Seat.objects.first()),
            name = 'Test Athlete',
        )

        # Create simple set of purchases
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                seat = seat,
                crew = self.crews[seat.id],
                athlete = athlete,
            )

        # Test method
        game_advance.roll_over_purchases(self.day)

        self.assertEqual(
            list(self.day.purchases.values('team', 'crew', 'seat', 'athlete')),
            list(exists(self.day.next).purchases.values('team', 'crew', 'seat', 'athlete')),
        )


    def test__query_count(self) -> None:
        """Expect:
            (2) Access day.next  (Affected by .next caching, or fetching day with select_related)
            (1) SELECT purchases for current day
            (1) INSERT purchases for next day
        """

        # Create simple set of purchases
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                seat = seat,
                crew = self.crews[seat.id],
            )

        # Test method
        with self.assertNumQueries(4):
            game_advance.roll_over_purchases(self.day)


class Test__EvaluateInvestments(TestCase):
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'dev_start_day3',
        'seats',
        'dev_team',
    ]

    event: models.Event
    day1: models.Day
    day2: models.Day
    day3: models.Day
    crew_wadh_w: models.Crew
    crew_orie_w: models.Crew
    crew_wolf_w: models.Crew
    crew_ball_m: models.Crew
    crew_hert_m: models.Crew
    crew_pemb_m: models.Crew
    crew_catz_m: models.Crew

    team: models.Team
    budgets: models.GameEntry
    seat: models.Seat
    all_seats: db.QuerySet[models.Seat]


    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())

        days = cls.event.days.all()
        cls.day1 = days[0]
        cls.day2 = days[1]
        cls.day3 = days[2]

        # Wadham bumped day 1; Oriel got bumped both days; Wolfson rowed over day 1
        cls.crew_wadh_w = models.Crew.objects.get(club = Clubs.WADH, gender = Genders.WOMEN)
        cls.crew_orie_w = models.Crew.objects.get(club = Clubs.ORIE, gender = Genders.WOMEN)
        cls.crew_wolf_w = models.Crew.objects.get(club = Clubs.WOLF, gender = Genders.WOMEN)

        # Balliol bumped day 1; Hertford got bumped day 1; Pembroke rowed over both days
        cls.crew_ball_m = models.Crew.objects.get(club = Clubs.BALL, gender = Genders.MEN)
        cls.crew_hert_m = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.MEN)
        cls.crew_pemb_m = models.Crew.objects.get(club = Clubs.PEMB, gender = Genders.MEN)
        cls.crew_catz_m = models.Crew.objects.get(club = Clubs.SCAT, gender = Genders.MEN)
        # ^ Catz bumped day 2

        cls.team = exists(models.Team.objects.first())
        cls.budgets = cls.team.entries.create(event = cls.event)

        cls.seat = exists(models.Seat.objects.first())
        cls.all_seats = models.Seat.objects.all()


    def test__bump_down__men_complete(self) -> None:
        """Crews lose value and no bonuses are awarded, regardless of completeness."""

        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)

        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 1 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__bump_down__women_complete(self) -> None:
        """Crews lose value and no bonuses are awarded, regardless of completeness."""

        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)

        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 1 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__bump_down__both_complete(self) -> None:
        """Crews lose value and no bonuses are awarded, regardless of completeness."""

        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)

        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__row_over__men_complete(self) -> None:
        """No value changes, but bonuses are awarded if both crews complete."""

        value_change_men = self.crew_pemb_m.value(self.day2) - self.crew_pemb_m.value(self.day1)
        self.assertEqual(value_change_men, 0)

        value_change_women = self.crew_wolf_w.value(self.day2) - self.crew_wolf_w.value(self.day1)
        self.assertEqual(value_change_women, 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__row_over__women_complete(self) -> None:
        """No value changes, but bonuses are awarded if both crews complete."""

        value_change_men = self.crew_pemb_m.value(self.day2) - self.crew_pemb_m.value(self.day1)
        self.assertEqual(value_change_men, 0)

        value_change_women = self.crew_wolf_w.value(self.day2) - self.crew_wolf_w.value(self.day1)
        self.assertEqual(value_change_women, 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__row_over__both_complete(self) -> None:
        """No value changes, but bonuses are awarded if both crews complete."""

        start_value_men = self.crew_pemb_m.value(self.day1)
        payout_men = round(0.07 * start_value_men)
        value_change_men = self.crew_pemb_m.value(self.day2) - start_value_men
        self.assertEqual(value_change_men, 0)

        start_value_women = self.crew_wolf_w.value(self.day1)
        payout_women = round(0.07 * start_value_women)
        value_change_women = self.crew_wolf_w.value(self.day2) - start_value_women
        self.assertEqual(value_change_women, 0)

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + 9 * payout_women)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout_women)


    def test__bump_up__men_complete(self) -> None:
        """Values increase regardless of completeness, bonuses awarded only if both complete."""

        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)

        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 1 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__bump_up__women_complete(self) -> None:
        """Values increase regardless of completeness, bonuses awarded only if both complete."""

        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)

        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)

        self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 1 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__bump_up__both_complete(self) -> None:
        """Values increase regardless of completeness, bonuses awarded only if both complete."""

        start_value_men = self.crew_ball_m.value(self.day1)
        payout_men = round(0.21 * start_value_men)
        value_change_men = self.crew_ball_m.value(self.day2) - start_value_men
        self.assertTrue(value_change_men > 0)

        start_value_women = self.crew_wadh_w.value(self.day1)
        payout_women = round(0.21 * start_value_women)
        value_change_women = self.crew_wadh_w.value(self.day2) - start_value_women
        self.assertTrue(value_change_women > 0)

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * (value_change_men + payout_men),
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * (value_change_women + payout_women),
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout_women)


    def test__different_day(self) -> None:
        """Ignores purchases for other days."""

        value_change_men = self.crew_catz_m.value(self.day3) - self.crew_catz_m.value(self.day2)
        self.assertTrue(value_change_men > 0)

        value_change_women = self.crew_wolf_w.value(self.day3) - self.crew_wolf_w.value(self.day2)
        self.assertTrue(value_change_women > 0)

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day2, crew = self.crew_catz_m, seat = seat)
            self.team.purchases.create(day = self.day2, crew = self.crew_wolf_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__different_team(self) -> None:
        """Ignores purchases for other teams."""

        other_team = auth.User.objects.create_user('Other').team

        value_change_men = self.crew_catz_m.value(self.day3) - self.crew_catz_m.value(self.day2)
        self.assertTrue(value_change_men > 0)

        value_change_women = self.crew_wolf_w.value(self.day3) - self.crew_wolf_w.value(self.day2)
        self.assertTrue(value_change_women > 0)

        for seat in self.all_seats:
            other_team.purchases.create(day = self.day2, crew = self.crew_catz_m, seat = seat)
            other_team.purchases.create(day = self.day2, crew = self.crew_wolf_w, seat = seat)

        game_advance.evaluate_investments(self.day1)

        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)


    def test__query_count(self) -> None:
        """ Expect:
            (1) SELECT entries
            (2) SELECT mens's & women's crews as prefetch objects
            (1) SELECT all seats
            (4) Create payout matrix  (3 if day.next is cached)
            (1) UPDATE entries
        """

        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)

        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)

        fresh_day = models.Day.objects.select_related().get(pk = self.day1.pk)

        with self.assertNumQueries(9):
            game_advance.evaluate_investments(fresh_day)


class Test__PayoutMatrix(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_start_day2']

    day: models.Day

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())

    @patch(
        'fantasy.utils.payout_by_day_gender_positions',
        autospec = True,
        side_effect = lambda w, x, y, z: (w, x, y, z),
    )
    def test__matrix__individual_calls(self, payouts_mock: Mock) -> None:
        """Checks that the matrix is constructed from payout calls for individual crews.

        N.B. This test using a non-type-compliant hack to ensure the correct construction of the
        payout matrix.
        """

        matrix = game_advance.create_payout_matrix(self.day)

        crews = models.Crew.objects.filter(positions__day = self.day)
        for crew in crews:
            with self.subTest(crew = str(crew)):

                delta_crabs = matrix[crew]
                self.assertEqual(delta_crabs[0], self.day)  # type: ignore
                self.assertEqual(delta_crabs[1], crew.gender)  # type: ignore
                self.assertEqual(
                    delta_crabs[2],  # type: ignore
                    self.day.ranking.get(crew = crew).rank,
                )
                self.assertEqual(
                    delta_crabs[3],  # type: ignore
                    exists(self.day.next).ranking.get(crew = crew).rank,
                )


    def test__matrix__query_count(self) -> None:
        """Expect:
            (1) SELECT next day of event (can be cached)
            (1) SELECT crews with positions on day
            (1) SELECT positions for crews on day
            (1) SELECT positions for crews on the next day
        """

        fresh_day = models.Day.objects.select_related().get(pk = self.day.pk)

        with self.assertNumQueries(4):
            game_advance.create_payout_matrix(fresh_day)

