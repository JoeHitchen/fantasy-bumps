from django.test import TestCase, tag
from django.contrib.auth import models as auth

from . import models
from . import errors
from .constants import genders
from .transactions import buy, sell, _buy_body, _sell_body


class Test__Buy(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.seat = models.Seat.objects.first()
        cls.crew = models.Crew.objects.filter(gender = genders.WOMENS).first()
        cls.crew_mens = models.Crew.objects.filter(gender = genders.MENS).first()
        
        cls.crew.positions.create(day = cls.day, rank = 1)
        cls.crew_mens.positions.create(day = cls.day, rank = 1)
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
    
    
    def test__insufficient_funds(self):
        """Performs no action and fails an assertion."""
        
        self.budgets.womens_balance = 100
        self.budgets.save()
        
        with self.assertRaises(errors.InsufficientFundsError):
            buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 100)
        
        self.assertEqual(self.team.purchases.count(), 0)
    
    
    def test__womens_crew(self):
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 850)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__mens_crew(self):
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew_mens)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 850)
        self.assertEqual(self.budgets.womens_balance, 1000)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__already_filled(self):
        """Rejects the purchase if the team/seat/day/gender combination is already occupied."""
        
        self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        
        with self.assertRaises(errors.DuplicateSeatError):
            buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 1000)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__other_gender_filled(self):
        """Doesn't block a team/seat/day combination if the genders don't match."""
        
        self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew_mens)
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 850)
        
        self.assertEqual(self.team.purchases.count(), 2)
    
    
    def test__budgets_missing(self):
        """Creates the missing budgets and then performs the standard action."""
        
        self.budgets.delete()
        self.assertEqual(models.GameEntry.objects.count(), 0)
        
        buy(self.team, self.day, self.seat, self.crew)
        
        new_budgets = self.team.entries.get(event = self.day.event)
        self.assertEqual(new_budgets.mens_budget, 1000)
        self.assertEqual(new_budgets.womens_budget, 1000)
        self.assertEqual(new_budgets.mens_balance, 1000)
        self.assertEqual(new_budgets.womens_balance, 850)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    @tag('query-count')
    def test__query_count__standard(self):
        """ Expect:
            (1) SELECT day's event  (Can be avoided with select_related)
            (1) SELECT budgets
            (1) SELECT crew's position  (Affected by caching)
            (1) UPDATE budgets
            (1) INSERT new purchase
            (1) SELECT day/seat/gender duplication check
        """
        
        fresh_day = models.Day.objects.get(id = self.day.id)
        self.crew.value.cache_clear()
        
        with self.assertNumQueries(6):
            _buy_body(self.team, fresh_day, self.seat, self.crew)
    
    
    @tag('query-count')
    def test__query_count__without_budgets(self):
        """ Expect:
            (6) Queried as standard
            (2) Internal transaction overhead
            (1) INSERT new budget
        """
        
        fresh_day = models.Day.objects.get(id = self.day.id)
        self.crew.value.cache_clear()
        self.budgets.delete()
        
        with self.assertNumQueries(9):
            _buy_body(self.team, fresh_day, self.seat, self.crew)



class Test__Sell(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.user = auth.User.objects.first()
        cls.day = models.Day.objects.first()
        cls.seat = models.Seat.objects.first()
        cls.crew = models.Crew.objects.filter(gender = genders.WOMENS).first()
        cls.crew_mens = models.Crew.objects.filter(gender = genders.MENS).first()
        
        cls.budgets = cls.user.team.entries.create(event = cls.day.event)
        
        cls.purchase = cls.user.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )
    
    
    def test__missing_budgets(self):
        """Performs no action and fails an assertion."""
        
        self.budgets.delete()  # Do not check for budget-update side effect
        
        with self.assertRaises(models.GameEntry.DoesNotExist):
            sell(self.purchase, 150)
        
        self.purchase.refresh_from_db()  # Does not fail
    
    
    def test__already_deleted(self):
        """Performs no action and fails an assertion."""
        
        self.purchase.delete()  # Do not check for purchase-delete side effect
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            sell(self.purchase, 150)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 1000)
    
    
    def test__mens_crew(self):
        """Adds the sale value to the men's balance and deletes the instance."""
        
        purchase = self.user.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew_mens,
        )
        sell(purchase, 150)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1150)
        self.assertEqual(self.budgets.womens_balance, 1000)
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            purchase.refresh_from_db()
    
    
    def test__womens_crew(self):
        """Adds the sale value to the women's balance and deletes the instance."""
        
        sell(self.purchase, 150)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 1150)
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            self.purchase.refresh_from_db()
    
    
    @tag('query-count')
    def test__query_count__without_related(self):
        """ Expect:
            1. SELECT purchase
            2. SELECT crew
            3. SELECT team
            4. SELECT day
            5. SELECT event
            6. UPDATE budget/gameentry
            7. DELETE purchase
        """
        
        with self.assertNumQueries(7):
            
            fresh_purchase = (
                models.Purchase.objects
                .get(id = self.purchase.id)
            )
            _sell_body(fresh_purchase, 150)
    
    
    @tag('query-count')
    def test__query_count__with_related(self):
        """ Expect:
            1. SELECT purchase, crew, team, day, event
            2. UPDATE budget/gameentry
            3. DELETE purchase
        """
        
        with self.assertNumQueries(3):
            
            fresh_purchase = (
                models.Purchase.objects
                .select_related()
                .get(id = self.purchase.id)
            )
            _sell_body(fresh_purchase, 150)

