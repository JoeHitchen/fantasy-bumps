from django.test import TestCase
from django.db import models as db

from core.tests import exists

from .constants import Series, Genders, Clubs
from . import models
from . import utils
from . import errors


class Test__Ordered_Events(TestCase):

    def test__ordered_events(self) -> None:

        extra_fields = {
            'mens_division_sizes': [12, 12, 12, 12, 12, 13],
            'womens_division_sizes': [12, 12, 12, 12, 13],
            'initial_market_open': '2019-02-24T20:00:00Z',
        }

        t14 = models.Event(series = Series.TORPIDS, year = 2014, tag = 't14', **extra_fields)
        t14.save()
        t14.days.create(date = '2014-02-28')

        t15 = models.Event(series = Series.TORPIDS, year = 2015, tag = 't15', **extra_fields)
        t15.save()
        t15.days.create(date = '2015-03-02')

        t13 = models.Event(series = Series.TORPIDS, year = 2013, tag = 't13', **extra_fields)
        t13.save()
        t13.days.create(date = '2013-02-27')

        t12 = models.Event(series = Series.TORPIDS, year = 2012, tag = 't12', **extra_fields)
        t12.save()
        t12.days.create(date = '2012-02-26')

        self.assertQuerySetEqual(utils.ordered_events(), [t15, t14, t13, t12])



class Test__Has_All_Seats(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']

    team: models.Team
    day: models.Day
    crew: models.Crew
    all_seats: db.QuerySet[models.Seat]


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())
        cls.crew = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.MEN, rank = 1)

        cls.all_seats = models.Seat.objects.all()


    def test__empty_crew(self) -> None:
        """Returns false if there are no seats filled."""

        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertFalse(value)


    def test__all_seats(self) -> None:
        """Returns true if all seats are present exactly once."""

        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertTrue(value)


    def test__all_seats_as_list(self) -> None:
        """Returns true if all seats are present exactly once."""

        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        purchase_list = models.Purchase.objects.all()
        seat_list = self.all_seats
        value = utils.has_all_seats(purchase_list, seat_list)
        self.assertTrue(value)


    def subtest__missing_seat(self, missing_seat: str) -> None:
        """Returns false if a specific seat is missing."""

        for seat in models.Seat.objects.exclude(name__iexact = missing_seat):
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertFalse(value)

    def test__missing_seat__bow(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('bow')

    def test__missing_seat__2(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('2')

    def test__missing_seat__3(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('3')

    def test__missing_seat__4(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('4')

    def test__missing_seat__5(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('5')

    def test__missing_seat__6(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('6')

    def test__missing_seat__7(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('7')

    def test__missing_seat__stroke(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('stroke')

    def test__missing_seat__cox(self) -> None:
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('cox')


    def subtest__extra_seat(self, extra_seat_str: str) -> None:
        """Raises ValueError if any seat present twice."""

        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        extra_seat = models.Seat.objects.get(name__iexact = extra_seat_str)
        self.team.purchases.create(day = self.day, crew = self.crew, seat = extra_seat)

        with self.assertRaises(errors.DuplicateSeatError):
            utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)

    def test__extra_seat__bow(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('bow')

    def test__extra_seat__2(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('2')

    def test__extra_seat__3(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('3')

    def test__extra_seat__4(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('4')

    def test__extra_seat__5(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('5')

    def test__extra_seat__6(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('6')

    def test__extra_seat__7(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('7')

    def test__extra_seat__stroke(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('stroke')

    def test__extra_seat__cox(self) -> None:
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('cox')



class Test__Crew_List_By_Seat(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']

    team: models.Team
    day: models.Day
    crew: models.Crew
    all_seats: db.QuerySet[models.Seat]


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())
        cls.crew = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.MEN, rank = 1)

        cls.all_seats = models.Seat.objects.order_by('pk').all()


    def test__empty_crew(self) -> None:
        """Returns dict with all seats mapping to None."""

        crew_list = utils.crew_list_by_seat(models.Purchase.objects.all(), self.all_seats)
        self.assertQuerySetEqual(self.all_seats, list(crew_list.keys()))

        for seat, purchase in crew_list.items():
            with self.subTest(seat = seat.name):
                self.assertIsNone(purchase)


    def test__all_seats_filled(self) -> None:
        """Returns dict mapping each seat to its corresponding purchase."""

        for seat in self.all_seats:
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        crew_list = utils.crew_list_by_seat(self.team.purchases.all(), self.all_seats)
        self.assertQuerySetEqual(self.all_seats, list(crew_list.keys()))

        for seat, purchase in crew_list.items():
            with self.subTest(seat = seat.name):
                self.assertIsNotNone(purchase)
                self.assertEqual(exists(purchase).seat, seat)


    def test__partial_seats_filled(self) -> None:
        """Returns dict with some seats filled and some None."""

        seats_to_fill = list(self.all_seats)[:5]
        for seat in seats_to_fill:
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)

        crew_list = utils.crew_list_by_seat(self.team.purchases.all(), self.all_seats)
        self.assertQuerySetEqual(self.all_seats, list(crew_list.keys()))

        for seat, purchase in crew_list.items():
            with self.subTest(seat = seat.name):
                if seat in seats_to_fill:
                    self.assertIsNotNone(purchase)
                    self.assertEqual(exists(purchase).seat, seat)
                else:
                    self.assertIsNone(purchase)



class Test__Reverse_Gender(TestCase):

    def test__men_to_women(self) -> None:
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(Genders.MEN), Genders.WOMEN)

    def test__women_to_men(self) -> None:
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(Genders.WOMEN), Genders.MEN)



class Test__Pricing(TestCase):

    def test__bungline_2(self) -> None:
        """Ensures a sensible price is given for bungline 2.

        The price gap between bungline 1 and bungline 2 should be equal-to or greater than that of
        bungline 2 to bungline 3.

        See #68
        """

        for num_crews in [61, 73, 79, 92]:
            with self.subTest(num_crews = num_crews):
                bungline_1 = utils.pricing(1, num_crews)
                bungline_2 = utils.pricing(2, num_crews)
                bungline_3 = utils.pricing(3, num_crews)

                self.assertGreaterEqual(bungline_1 - bungline_2, bungline_2 - bungline_3)



class Test__Payouts(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_start_day2']

    day: models.Day


    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())


    def test__individual__row_over(self) -> None:
        """No change in value but a small payout."""

        old_ranking = 5
        new_ranking = 5

        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN)
        value_change = new_price - old_price

        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )

        self.assertEqual(value_change, 0)
        self.assertEqual(delta_crabs['position_change'], 0)
        self.assertFalse(delta_crabs['headship'])
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], round(0.07 * old_price))


    def test__individual__headship(self) -> None:
        """Headship row overs get a larger payout than a standard row over."""

        old_ranking = 1
        new_ranking = 1

        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN)
        value_change = new_price - old_price

        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )

        self.assertEqual(value_change, 0)
        self.assertEqual(delta_crabs['position_change'], 0)
        self.assertTrue(delta_crabs['headship'])
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], round(0.175 * old_price))


    def test__individual__bump_up(self) -> None:
        """An increase in value and a larger payout."""

        old_ranking = 5
        new_ranking = 4

        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN)
        value_change = new_price - old_price

        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )

        self.assertTrue(value_change > 0)
        self.assertEqual(delta_crabs['position_change'], 1)
        self.assertFalse(delta_crabs['headship'])
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], round(0.21 * old_price))


    def test__individual__bump_down(self) -> None:
        """A decrease in value and no payout."""

        old_ranking = 5
        new_ranking = 6

        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN)
        value_change = new_price - old_price

        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )

        self.assertTrue(value_change < 0)
        self.assertEqual(delta_crabs['position_change'], -1)
        self.assertFalse(delta_crabs['headship'])
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], 0)


    def test__individual__query_count(self) -> None:
        """Expect no queries if Day has Event pre-selected."""

        day = exists(models.Day.objects.select_related('event').first())

        with self.assertNumQueries(0):
            utils.payout_by_day_gender_positions(day, Genders.WOMEN, 5, 5)

