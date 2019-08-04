from django.test import TestCase, tag
from django.contrib.auth import models as auth

from . import models
from .constants import genders
from .transactions import sell, _sell_body


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
        
        with self.assertRaisesRegex(AssertionError, 'Sell failed - Did not update singular row.'):
            sell(self.purchase, 150)
        
        self.purchase.refresh_from_db()  # Does not fail
    
    
    def test__already_deleted(self):
        """Performs no action and fails an assertion."""
        
        self.purchase.delete()  # Do not check for purchase-delete side effect
        
        with self.assertRaisesRegex(AssertionError, 'Sell failed - Did not delete singular row.'):
            sell(self.purchase, 150)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, 1000)
        self.assertEqual(self.budgets.womens_budget, 1000)
        self.assertEqual(self.budgets.mens_balance, 1000)
        self.assertEqual(self.budgets.womens_balance, 1000)
    
    
    def test__mens_crew(self):
        """Adds the sale value to the men's balance and deletes the instance."""
        self.skipTest('See issue #4.')
        
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

