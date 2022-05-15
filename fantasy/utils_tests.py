from unittest.mock import patch

from django.test import TestCase, tag

from .constants import Series, Genders, Clubs
from . import models
from . import utils
from . import errors


class Test__Ordered_Events(TestCase):
    
    def test__ordered_events(self):
        
        division_structure = {
            'mens_divisions_count': 6,
            'mens_divisions_size': 12,
            'womens_divisions_count': 5,
            'womens_divisions_size': 12,
            'mens_division_sizes': [12, 12, 12, 12, 12, 13],
            'womens_division_sizes': [12, 12, 12, 12, 13],
        }
        
        t14 = models.Event(series = Series.TORPIDS, year = 2014, tag = 't14', **division_structure)
        t14.save()
        t14.days.create(date = '2014-02-28')
        
        t15 = models.Event(series = Series.TORPIDS, year = 2015, tag = 't15', **division_structure)
        t15.save()
        t15.days.create(date = '2015-03-02')
        
        t13 = models.Event(series = Series.TORPIDS, year = 2013, tag = 't13', **division_structure)
        t13.save()
        t13.days.create(date = '2013-02-27')
        
        t12 = models.Event(series = Series.TORPIDS, year = 2012, tag = 't12', **division_structure)
        t12.save()
        t12.days.create(date = '2012-02-26')
        
        self.assertQuerysetEqual(utils.ordered_events(), [t15, t14, t13, t12])



@tag('game-core')
class Test__Has_All_Seats(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.MEN, rank = 1)
        
        cls.all_seats = models.Seat.objects.all()
    
    
    def test__empty_crew(self):
        """Returns false if there are no seats filled."""
        
        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertFalse(value)
    
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertTrue(value)
    
    
    def test__all_seats_as_list(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        purchase_list = list(models.Purchase.objects.all())
        seat_list = list(self.all_seats)
        value = utils.has_all_seats(purchase_list, seat_list)
        self.assertTrue(value)
    
    
    def subtest__missing_seat(self, missing_seat):
        """Returns false if a specific seat is missing."""
        
        for seat in models.Seat.objects.exclude(name__iexact = missing_seat):
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        value = utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
        self.assertFalse(value)
    
    def test__missing_seat__bow(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('bow')
    
    def test__missing_seat__2(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('2')
    
    def test__missing_seat__3(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('3')
    
    def test__missing_seat__4(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('4')
    
    def test__missing_seat__5(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('5')
    
    def test__missing_seat__6(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('6')
    
    def test__missing_seat__7(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('7')
    
    def test__missing_seat__stroke(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('stroke')
    
    def test__missing_seat__cox(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('cox')
    
    
    def subtest__extra_seat(self, extra_seat):
        """Raises ValueError if any seat present twice."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        extra_seat = models.Seat.objects.get(name__iexact = extra_seat)
        self.team.purchases.create(day = self.day, crew = self.crew, seat = extra_seat)
        
        with self.assertRaises(errors.DuplicateSeatError):
            utils.has_all_seats(models.Purchase.objects.all(), self.all_seats)
    
    def test__extra_seat__bow(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('bow')
    
    def test__extra_seat__2(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('2')
    
    def test__extra_seat__3(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('3')
    
    def test__extra_seat__4(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('4')
    
    def test__extra_seat__5(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('5')
    
    def test__extra_seat__6(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('6')
    
    def test__extra_seat__7(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('7')
    
    def test__extra_seat__stroke(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('stroke')
    
    def test__extra_seat__cox(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('cox')



class Test__Reverse_Gender(TestCase):
    
    def test__men_to_women(self):
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(Genders.MEN), Genders.WOMEN)
    
    def test__women_to_men(self):
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(Genders.WOMEN), Genders.MEN)



@tag('game-core')
class Test__Pricing(TestCase):
    
    def test__bungline_2(self):
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



@tag('game-core')
class Test__Payouts(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_start_day2']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
    
    
    def test__individual__row_over(self):
        """No change in value but a small payout."""
        
        old_ranking = 5
        new_ranking = 5
        
        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN.value)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN.value)
        value_change = new_price - old_price
        
        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )
        
        self.assertEqual(value_change, 0)
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], round(0.07 * old_price))
    
    
    def test__individual__bump_up(self):
        """An increase in value and a larger payout."""
        
        old_ranking = 5
        new_ranking = 4
        
        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN.value)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN.value)
        value_change = new_price - old_price
        
        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )
        
        self.assertTrue(value_change > 0)
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], round(0.21 * old_price))
    
    
    def test__individual__bump_down(self):
        """A decrease in value and no payout."""
        
        old_ranking = 5
        new_ranking = 6
        
        old_price = utils.pricing_by_day_gender(old_ranking, self.day, Genders.WOMEN.value)
        new_price = utils.pricing_by_day_gender(new_ranking, self.day, Genders.WOMEN.value)
        value_change = new_price - old_price
        
        delta_crabs = utils.payout_by_day_gender_positions(
            self.day,
            Genders.WOMEN,
            old_ranking,
            new_ranking,
        )
        
        self.assertTrue(value_change < 0)
        self.assertEqual(delta_crabs['value_change'], value_change)
        self.assertEqual(delta_crabs['payout'], 0)
    
    
    @tag('query-count')
    def test__individual__query_count(self):
        """Expect no queries if Day has Event pre-selected."""
        
        day = models.Day.objects.select_related('event').first()
        
        with self.assertNumQueries(0):
            utils.payout_by_day_gender_positions(day, Genders.WOMEN, 5, 5)
    
    
    @patch(
        'fantasy.utils.payout_by_day_gender_positions',
        autospec = True,
        side_effect = lambda w, x, y, z: (w, x, y, z),
    )
    def test__matrix__individual_calls(self, payouts_mock):
        """Checks that the matrix is constructed from payout calls for individual crews."""
        
        matrix = utils.create_payout_matrix(self.day)
        for crew, delta_crabs in matrix.items():
            with self.subTest(crew = str(crew)):
                self.assertEqual(delta_crabs[0], self.day)
                self.assertEqual(delta_crabs[1], crew.gender)
                self.assertEqual(delta_crabs[2], self.day.ranking.get(crew = crew).rank)
                self.assertEqual(delta_crabs[3], self.day.next.ranking.get(crew = crew).rank)
    
    
    @tag('query-count')
    def test__matrix__query_count(self):
        """Expect:
            (1) SELECT next day of event (can be cached)
            (1) SELECT crews with positions on day
            (1) SELECT positions for crews on day
            (1) SELECT positions for crews on the next day
        """
        
        fresh_day = models.Day.objects.select_related().get(pk = self.day.pk)
        
        with self.assertNumQueries(4):
            utils.create_payout_matrix(fresh_day)

