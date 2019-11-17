from django.test import TestCase, tag
from django.contrib.auth import models as auth

from . import models
from . import errors
from .constants import genders, money
from .transactions import buy, sell, _buy_body, _sell_body


class Test__Buy(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.seat = models.Seat.objects.first()
        cls.crew = models.Crew.objects.filter(gender = genders.WOMENS).first()
        cls.crew_mens = models.Crew.objects.filter(gender = genders.MENS).first()
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
    
    
    def setUp(self):
        models.Crew.value.cache_clear()
        self.budgets.refresh_from_db()
    
    
    def test__not_racing(self):
        """Performs no action and raises an error."""
        
        self.crew.positions.filter(day = self.day).delete()
        
        with self.assertRaises(errors.NotRacingError):
            buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
        
        self.assertEqual(self.team.purchases.count(), 0)
    
    
    def test__insufficient_funds(self):
        """Performs no action and raises an error."""
        
        self.budgets.womens_balance = 0
        self.budgets.save()
        
        with self.assertRaises(errors.InsufficientFundsError):
            buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, 0)
        
        self.assertEqual(self.team.purchases.count(), 0)
    
    
    def test__womens_crew(self):
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__mens_crew(self):
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew_mens)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__already_filled(self):
        """Rejects the purchase if the team/seat/day/gender combination is already occupied."""
        
        self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        
        with self.assertRaises(errors.DuplicateSeatError):
            buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__other_gender_filled(self):
        """Doesn't block a team/seat/day combination if the genders don't match."""
        
        self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew_mens)
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 2)
    
    
    def test__budgets_missing(self):
        """Creates the missing budgets and then performs the standard action."""
        
        self.budgets.delete()
        self.assertEqual(models.GameEntry.objects.count(), 0)
        
        buy(self.team, self.day, self.seat, self.crew)
        
        new_budgets = self.team.entries.get(event = self.day.event)
        self.assertEqual(new_budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(new_budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(new_budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(new_budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__with_athlete(self):
        """Performs the standard action and creates a Purchase that references the Athlete."""
        
        athlete = models.Athlete.objects.create(
            event = self.day.event,
            crew = self.crew,
            seat = self.seat,
            name = 'Test Athlete',
        )
        
        buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 1)
        self.assertEqual(self.team.purchases.first().athlete, athlete)
    
    
    def test__with_duplicate_athlete(self):
        """Rejects the purchase if the team/athlete/day/gender combination is already occupied."""
        
        athlete = models.Athlete.objects.create(
            event = self.day.event,
            crew = self.crew,
            seat = self.seat,
            name = 'Test Athlete',
        )
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = models.Seat.objects.last(),
            athlete = athlete,
        )

        with self.assertRaises(errors.DuplicateAthleteError):
            buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__with_duplicate_absent_athlete(self):
        """Performs the standard action and creates a second Purchase with no athlete."""
        
        athlete = None
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = models.Seat.objects.last(),
            athlete = athlete,
        )

        buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
    
    
    @tag('query-count')
    def test__query_count__standard(self):
        """ Expect:
            (1) SELECT budgets
            (1) SELECT crew's position  (Affected by caching)
            (1) SELECT day's maximum rank  (Affected by caching)
            (1) UPDATE budgets
            (1) INSERT new purchase
            (1) SELECT team/day/seat/gender duplication check
            (1) SELECT tea/day/athlete/gender duplication check
        """
        
        fresh_day = models.Day.objects.select_related().get(id = self.day.id)
        
        with self.assertNumQueries(7):
            _buy_body(self.team, fresh_day, self.seat, self.crew)
    
    
    @tag('query-count')
    def test__query_count__without_budgets(self):
        """ Expect:
            (7) Queried as standard
            (2) Internal transaction overhead
            (1) INSERT new budget
        """
        
        fresh_day = models.Day.objects.select_related().get(id = self.day.id)
        self.budgets.delete()
        
        with self.assertNumQueries(10):
            _buy_body(self.team, fresh_day, self.seat, self.crew)



class Test__Sell(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.user = auth.User.objects.first()
        cls.day = models.Day.objects.select_related().first()
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
        """Performs no action and raises an error."""
        
        self.budgets.delete()  # Do not check for budget-update side effect
        
        with self.assertRaises(models.GameEntry.DoesNotExist):
            sell(self.purchase)
        
        self.purchase.refresh_from_db()  # Does not fail
    
    
    def test__already_deleted(self):
        """Performs no action and raises an error."""
        
        self.purchase.delete()  # Do not check for purchase-delete side effect
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            sell(self.purchase)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__mens_crew(self):
        """Adds the sale value to the men's balance and deletes the instance."""
        
        purchase = self.user.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew_mens,
        )
        sell(purchase)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE + money.PRICE_MAX)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            purchase.refresh_from_db()
    
    
    def test__womens_crew(self):
        """Adds the sale value to the women's balance and deletes the instance."""
        
        sell(self.purchase)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + money.PRICE_MAX)
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            self.purchase.refresh_from_db()
    
    
    @tag('query-count')
    def test__query_count(self):
        """ Expect:
            (1) SELECT crew's position  (Affected by caching)
            (1) SELECT day's maximum rank  (Affected by caching)
            (1) UPDATE budget/gameentry
            (1) DELETE purchase
        """
        
        self.crew.value.cache_clear()
        
        fresh_purchase = models.Purchase.objects.select_related().get(id = self.purchase.id)
        with self.assertNumQueries(4):
            _sell_body(fresh_purchase)

