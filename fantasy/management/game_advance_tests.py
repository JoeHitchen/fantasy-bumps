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

from ..constants import Series, Clubs, Genders, money, CoachingCompetitions
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


    @patch('fantasy.management.game_advance.run_blades_or_bust')
    @patch('fantasy.management.game_advance.run_coaching_refund')
    def test__coaching__none(self, refund_mock: Mock, blades_mock: Mock) -> None:
        """Only the relevant coaching competition function is called."""

        game_advance.perform_advance(self.event, roll_over_positions)

        blades_mock.assert_not_called()
        refund_mock.assert_not_called()


    @patch('fantasy.management.game_advance.run_blades_or_bust')
    @patch('fantasy.management.game_advance.run_coaching_refund')
    def test__coaching__blades(self, refund_mock: Mock, blades_mock: Mock) -> None:
        """Only the relevant coaching competition function is called."""

        self.event.coaching_competition = CoachingCompetitions.BLADES
        self.event.save()

        game_advance.perform_advance(self.event, roll_over_positions)

        blades_mock.assert_called_once()
        refund_mock.assert_not_called()


    @patch('fantasy.management.game_advance.run_blades_or_bust')
    @patch('fantasy.management.game_advance.run_coaching_refund')
    def test__coaching__refund(self, refund_mock: Mock, blades_mock: Mock) -> None:
        """Only the relevant coaching competition function is called."""

        self.event.coaching_competition = CoachingCompetitions.REFUND
        self.event.save()

        game_advance.perform_advance(self.event, roll_over_positions)

        blades_mock.assert_not_called()
        refund_mock.assert_called_once()


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


    @classmethod
    def setUp(cls) -> None:
        game_advance.create_payout_matrix.cache_clear()


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


    @classmethod
    def setUp(cls) -> None:
        game_advance.create_payout_matrix.cache_clear()


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


class Test__CoachingCompetition(TestCase):
    fixtures = [
        'demo_event',
        'demo_days',
        'demo_crews',
        'demo_start_day1',
        'demo_start_day2',
        'demo_start_day3',
        'demo_start_day4',
        'demo_start_day5',
    ]

    event: models.Event
    entries: list[models.GameEntry]

    mens_budget = 900
    womens_budget = 1000
    mens_balance = 700
    womens_balance = 600

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())
        day = exists(cls.event.days.first())

        mdiv1 = list(day.ranking.filter(crew__gender = Genders.MEN))[0:12]
        wdiv1 = list(day.ranking.filter(crew__gender = Genders.WOMEN))[0:12]

        cls.entries = []
        for i in range(0, 12):
            team = auth.User.objects.create(username = f'Team {i+1}').team
            cls.entries.append(team.entries.create(
                event = cls.event,
                mens_coach = mdiv1[i].crew,
                womens_coach = wdiv1[i].crew,
                mens_budget = cls.mens_budget,
                womens_budget = cls.womens_budget,
                mens_balance = cls.mens_balance,
                womens_balance = cls.womens_balance,
            ))


    def test__blades__not_last_day(self) -> None:
        """Payouts are only awarded on the final day of racing to coaches who win blades.

        Expected queries:
            (1) SELECT Next racing day
        """

        for day in self.event.days.all()[0:3]:
            with self.subTest(day = str(day)):
                with self.assertNumQueries(1):
                    self.assertIsNone(game_advance.run_blades_or_bust(day))


    def test__blades__last_day(self) -> None:
        """Payouts are only awarded on the final day of racing to coaches who win blades.

        Expected queries:
            (1) SELECT Next racing day
            (2) SELECT Days & prefetch positions
            (2) UPDATE Men's & women's finances
        """

        saturday = exists(exists(self.event.days.last()).prev)

        with self.assertNumQueries(5):
            winners = game_advance.run_blades_or_bust(saturday)
            self.assertEqual(winners, 4)

        for rank, entry in enumerate(self.entries, start = 1):
            with self.subTest(rank = rank):
                entry.refresh_from_db()

                mens_increase = money.BLADES_BONUS if rank == 1 else 0
                self.assertEqual(entry.mens_budget, self.mens_budget + mens_increase)
                self.assertEqual(entry.mens_balance, self.mens_balance + mens_increase)

                womens_increase = money.BLADES_BONUS if rank in [1, 8, 10] else 0
                self.assertEqual(entry.womens_budget, self.womens_budget + womens_increase)
                self.assertEqual(entry.womens_balance, self.womens_balance + womens_increase)


    def test__refund(self) -> None:
        """Issues a payout for every place the coach's crew has dropped.

        Expected queries:
            (1) SELECT Current day ranking
            (2) SELECT Next day & next day ranking
            (2) SELECT Men's & Women's fantasies that got bumped
            (2) UPDATE Men's & women's finances
        """

        mens_places_lost = [
            {6: 1, 8: 5},
            {2: 1, 5: 1, 6: 2, 8: 6, 10: 1, 12: 1},
            {2: 1, 5: 2, 6: 2, 8: 7, 10: 2, 11: 1, 12: 1},
            {2: 1, 5: 2, 6: 3, 8: 8, 10: 3, 11: 2, 12: 2},
        ]
        womens_places_lost = [
            {5: 1, 7: 1, 9: 1, 12: 1},
            {5: 2, 7: 6, 9: 1, 12: 2},
            {3: 1, 5: 3, 6: 1, 7: 8, 9: 2, 12: 2},
            {3: 2, 5: 4, 6: 2, 7: 9, 9: 4, 12: 2},
        ]

        for num, day in enumerate(self.event.days.filter(first_race_time__isnull = False)):

            with self.assertNumQueries(7):
                game_advance.run_coaching_refund(day)


            for rank, entry in enumerate(self.entries, start = 1):
                with self.subTest(day = day, rank = rank):
                    entry.refresh_from_db()

                    mens_increase = money.TORPIDS_REFUND * mens_places_lost[num].get(rank, 0)
                    self.assertEqual(entry.mens_budget, self.mens_budget + mens_increase)
                    self.assertEqual(entry.mens_balance, self.mens_balance + mens_increase)

                    womens_increase = money.TORPIDS_REFUND * womens_places_lost[num].get(rank, 0)
                    self.assertEqual(entry.womens_budget, self.womens_budget + womens_increase)
                    self.assertEqual(entry.womens_balance, self.womens_balance + womens_increase)


class Test__EntryValidity(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_team', 'seats']

    day: models.Day
    team: models.Team
    entry: models.GameEntry
    crew_men: models.Crew
    crew_women: models.Crew

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())

        cls.team = exists(models.Team.objects.first())
        cls.entry = cls.team.entries.create(event = cls.day.event)

        cls.crew_men = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.MEN, rank = 1)
        cls.crew_women = models.Crew.objects.get(
            club = Clubs.HERT,
            gender = Genders.WOMEN,
            rank = 1,
        )

        for seat in models.Seat.objects.all():
            cls.team.purchases.create(day = cls.day, seat = seat, crew = cls.crew_men)
            cls.team.purchases.create(day = cls.day, seat = seat, crew = cls.crew_women)


    def test__missing_entry(self) -> None:
        """The entry is not judged if it is missing all seats."""

        self.team.purchases.all().delete()

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.valid_entry)


    def test__valid_entry(self) -> None:
        """The entry is valid if both crews have all seats."""

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.valid_entry)


    def test__invalid_entry__mens_crew_missing_seat(self) -> None:
        """The entry is invalid if the mens's crew is missing a seat."""

        self.team.purchases.filter(
            day = self.day,
            crew__gender = Genders.MEN,
            seat__name = '4',
        ).delete()

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.valid_entry, False)  # Testing explicitly for boolean False


    def test__invalid_entry__womens_crew_missing_seat(self) -> None:
        """The entry is invalid if the womens's crew is missing a seat."""

        self.team.purchases.filter(
            day = self.day,
            crew__gender = Genders.WOMEN,
            seat__name = '6',
        ).delete()

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.valid_entry, False)  # Testing explicitly for boolean False


    def test__invalid_to_valid(self) -> None:
        """A previously invalid entry cannot later become valid."""

        self.entry.valid_entry = False
        self.entry.save()

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.valid_entry, False)  # Testing explicitly for boolean False


    def test__invalid_entry__valid_to_invalid(self) -> None:
        """A previously valid entry cannot later become invalid."""

        self.entry.valid_entry = True
        self.entry.save()

        self.team.purchases.filter(
            day = self.day,
            crew__gender = Genders.MEN,
            seat__name = '4',
        ).delete()

        self.team.purchases.filter(
            day = self.day,
            crew__gender = Genders.WOMEN,
            seat__name = '4',
        ).delete()

        game_advance.update_entry_validity(self.day)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.valid_entry)


class Test__SubsUsage(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_team', 'seats']

    day_one: models.Day
    day_two: models.Day
    entry: models.GameEntry

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day_one = exists(models.Day.objects.first())
        cls.day_two = exists(cls.day_one.next)

        team = exists(models.Team.objects.first())
        cls.entry = team.entries.create(event = cls.day_one.event)

        crew_men = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.MEN, rank = 1)
        crew_women = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)

        for seat in models.Seat.objects.all():
            for day in [cls.day_one, cls.day_two]:
                team.purchases.create(day = day, seat = seat, crew = crew_men)
                team.purchases.create(day = day, seat = seat, crew = crew_women)


    def test__update_subs_usage__first_day(self) -> None:
        """Raises an assertion error if called for the first day of the event."""

        with self.assertRaises(AssertionError):
            game_advance.update_subs_usage(self.day_one)


    def test__update_subs_usage__no_subs(self) -> None:
        """Sub-free status is retained if subs are not used."""

        game_advance.update_subs_usage(self.day_two)

        self.entry.refresh_from_db()
        self.assertFalse(self.entry.has_subs)


    def test__update_subs_usage__mens_sub(self) -> None:
        """Sub-free status is lost if subs are used."""

        sub = models.Purchase.objects.get(
            day = self.day_two,
            seat = models.Seat.objects.get(name = '5'),
            crew__gender = Genders.MEN,
        )
        sub.crew = models.Crew.objects.get(club = Clubs.SCAT, gender = Genders.MEN, rank = 1)
        sub.save()

        game_advance.update_subs_usage(self.day_two)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.has_subs)


    def test__update_subs_usage__womens_sub(self) -> None:
        """Sub-free status is lost if subs are used."""

        sub = models.Purchase.objects.get(
            day = self.day_two,
            seat = models.Seat.objects.get(name = '3'),
            crew__gender = Genders.WOMEN,
        )
        sub.crew = models.Crew.objects.get(club = Clubs.PEMB, gender = Genders.WOMEN, rank = 1)
        sub.save()

        game_advance.update_subs_usage(self.day_two)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.has_subs)


    def test__update_subs_usage__not_restored(self) -> None:
        """A lost sub-free status is not restored if subs are not used."""

        self.entry.has_subs = True
        self.entry.save()

        game_advance.update_subs_usage(self.day_two)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.has_subs)


    def test__crew_used_subs__first_day(self) -> None:
        """Raises an assertion error if called for the first day of the event."""

        with self.assertRaises(AssertionError):
            game_advance.crew_used_subs(self.entry, self.day_one, Genders.WOMEN)


    def test__crew_used_subs__no_subs(self) -> None:
        """Returns False if the crew list matches the previous day's crew list."""

        self.assertFalse(game_advance.crew_used_subs(self.entry, self.day_two, Genders.WOMEN))


    def test__crew_used_subs__crew_changed(self) -> None:
        """Returns True if the crew list does not match the previous day's crew list."""

        sub = models.Purchase.objects.get(
            day = self.day_two,
            seat = models.Seat.objects.get(name = '3'),
            crew__gender = Genders.WOMEN,
        )
        sub.crew = models.Crew.objects.get(club = Clubs.PEMB, gender = Genders.WOMEN, rank = 1)
        sub.save()

        self.assertTrue(game_advance.crew_used_subs(self.entry, self.day_two, Genders.WOMEN))

