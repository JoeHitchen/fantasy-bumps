from django.test import TestCase, tag

from .constants import genders
from . import models
from . import utils
from . import errors


@tag('game-core')
class Test__Has_All_Seats(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.create(club = 'newc', gender = genders.MENS, rank = 1)
        
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
        self.assertEqual(utils.reverse_gender(genders.MENS), genders.WOMENS)
    
    def test__women_to_men(self):
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(genders.WOMENS), genders.MENS)



@tag('game-core')
class Test__Create_Payout_Matrix(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_start_day2']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
    
    
    def test__row_over(self):
        """No change in value but a small payout."""
        
        matrix = utils.create_payout_matrix(self.day)
        crew = models.Crew.objects.get(club = 'jesu', gender = genders.MENS, rank = 1)
        
        crew_payout = matrix[crew]
        
        old_price = new_price = utils.pricing(9, 9)
        self.assertEqual(crew_payout['value_change'], new_price - old_price)
        self.assertEqual(crew_payout['payout'], round(0.05 * old_price))
    
    
    def test__bump_up(self):
        """An increase in value and a larger payout."""
        
        matrix = utils.create_payout_matrix(self.day)
        crew = models.Crew.objects.get(club = 'magd', gender = genders.WOMENS, rank = 1)
        
        crew_payout = matrix[crew]
        
        old_price = utils.pricing(9, 9)
        new_price = utils.pricing(8, 9)
        self.assertEqual(crew_payout['value_change'], new_price - old_price)
        self.assertEqual(crew_payout['payout'], round(0.15 * old_price))
    
    
    def test__bump_down(self):
        """A decrease in value and no payout."""
        
        matrix = utils.create_payout_matrix(self.day)
        crew = models.Crew.objects.get(club = 'orie', gender = genders.WOMENS, rank = 1)
        
        crew_payout = matrix[crew]
        
        old_price = utils.pricing(1, 9)
        new_price = utils.pricing(2, 9)
        self.assertEqual(crew_payout['value_change'], new_price - old_price)
        self.assertEqual(crew_payout['payout'], 0)
    
    
    @tag('query-count')
    def test__query_count(self):
        """Expect:
            (1) SELECT crews with positions on day
            (1) SELECT positions for crews on day
            (1) SELECT positions for crews on the next day
        
        Assuming crew values are all previously cached.
        """
        
        for crew in models.Crew.objects.all():
            crew.value(self.day)
            crew.value(self.day.next)
        
        with self.assertNumQueries(3):
            utils.create_payout_matrix(self.day)

