from django.test import TestCase, tag
from django.contrib.auth import models as auth

from .constants import genders, money
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
        cls.crew = models.Crew.objects.create(gender = genders.MENS)
    
    
    def test__empty_crew(self):
        """Returns false if there are no seats filled."""
        
        value = utils.has_all_seats(models.Purchase.objects.all())
        self.assertFalse(value)
    
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        value = utils.has_all_seats(models.Purchase.objects.all())
        self.assertTrue(value)
    
    
    def subtest__missing_seat(self, missing_seat):
        """Returns false if a specific seat is missing."""
        
        for seat in models.Seat.objects.exclude(name__iexact = missing_seat):
            self.team.purchases.create(day = self.day, crew = self.crew, seat = seat)
        
        value = utils.has_all_seats(models.Purchase.objects.all())
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
            utils.has_all_seats(models.Purchase.objects.all())
    
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



class Test__All_Investments(TestCase):
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'seats',
        'dev_team',
    ]
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        
        days = cls.event.days.all()
        cls.day1 = days[0]
        cls.day2 = days[1]
        cls.day3 = days[2]
        
        cls.crew_hert = models.Crew.objects.get(name = 'Hertford W1')  # Bump both days
        cls.crew_orie = models.Crew.objects.get(name = 'Oriel W1')  # Got bumped both days
        cls.crew_wolf = models.Crew.objects.get(name = 'Wolfson W1')  # Rowed over day 1
        
        cls.team = models.Team.objects.first()
        cls.budgets = cls.team.entries.create(event = cls.event)
        
        cls.seat = models.Seat.objects.first()
    
    
    def test__bump_up(self):
        """Increases the budget for the correct gender, but not the balance."""
        
        value_change = self.crew_hert.value(self.day2) - self.crew_hert.value(self.day1)
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        utils.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + value_change)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__row_over(self):
        """Does not affect either the budget or the balance."""
        
        value_change = self.crew_wolf.value(self.day2) - self.crew_wolf.value(self.day1)
        self.assertEqual(value_change, 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_wolf, seat = self.seat)
        
        utils.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bumped_down(self):
        """Decreases the budget for the correct gender, but not the balance."""
        
        value_change = self.crew_orie.value(self.day2) - self.crew_orie.value(self.day1)
        self.assertTrue(value_change < 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_orie, seat = self.seat)
        
        utils.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + value_change)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__different_day(self):
        """Ignores purchases for other days."""
        
        value_change = self.crew_hert.value(self.day2) - self.crew_hert.value(self.day1)
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        utils.evaluate_all_investments(self.day2)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__different_team(self):
        """Ignores purchases for other teams."""
        
        other_team = auth.User.objects.create_user('Other').team
        
        value_change = self.crew_hert.value(self.day2) - self.crew_hert.value(self.day1)
        self.assertTrue(value_change > 0)
        
        other_team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        utils.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    @tag('query-count')
    def test__query_count(self):
        """ Expect:
            (1) SELECT entries
            (2) SELECT mens's & women's crews as prefetch objects
            (1) UPDATE entries
            
            Assumes crew value lookups are query-free (e.g. from caching)
        """
        
        value_change = self.crew_hert.value(self.day2) - self.crew_hert.value(self.day1)
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        with self.assertNumQueries(4):
            utils.evaluate_all_investments(self.day1)

