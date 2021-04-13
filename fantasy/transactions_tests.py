from django.test import TestCase, tag
from django.contrib.auth import models as auth

from . import models
from . import errors
from .constants import Genders, money
from .transactions import buy, sell, switch, _buy_body, _sell_body, _switch_body


class Test__Buy(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.seat = models.Seat.objects.first()
        cls.crew = models.Crew.objects.filter(gender = Genders.WOMEN).first()
        cls.crew_mens = models.Crew.objects.filter(gender = Genders.MEN).first()
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
    
    
    def setUp(self):
        self.budgets = self.team.entries.get(event = self.day.event)
    
    
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
        """Creates a purchase without a named athlete if athlete already picked."""
        
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

        buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 2)
        self.assertEqual(self.team.purchases.first().athlete, athlete)
        self.assertIsNone(self.team.purchases.last().athlete)
    
    
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
            (1) SELECT crew's position
            (1) UPDATE budgets
            (1) SELECT and LOCK crew list, seats, and athletes for duplication check
            (1) INSERT new purchase
        """
        
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
        
        fresh_day = models.Day.objects.select_related().get(id = self.day.id)
        
        with self.assertNumQueries(5):
            _buy_body(self.team, fresh_day, self.seat, self.crew, athlete)
    
    
    @tag('query-count')
    def test__query_count__without_budgets(self):
        """ Expect:
            (5) Queried as standard
            (2) Internal transaction overhead
            (1) INSERT new budget
        """
        
        fresh_day = models.Day.objects.select_related().get(id = self.day.id)
        self.budgets.delete()
        
        with self.assertNumQueries(8):
            _buy_body(self.team, fresh_day, self.seat, self.crew)



class Test__Sell(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.user = auth.User.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.seat = models.Seat.objects.first()
        cls.crew = models.Crew.objects.filter(gender = Genders.WOMEN).first()
        cls.crew_mens = models.Crew.objects.filter(gender = Genders.MEN).first()
        
        cls.budgets = cls.user.team.entries.create(event = cls.day.event)
        
        cls.purchase = cls.user.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )

    
    def setUp(self):
        self.budgets = self.user.team.entries.get(event = self.day.event)
        self.purchase.save()
    
    
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
            (1) SELECT crew's position
            (1) UPDATE budget/gameentry
            (1) DELETE purchase
        """
        
        fresh_purchase = models.Purchase.objects.select_related().get(id = self.purchase.id)
        with self.assertNumQueries(3):
            _sell_body(fresh_purchase)



class Test__Switch(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.filter(gender = Genders.WOMEN).first()
        cls.crew_alt = models.Crew.objects.filter(gender = Genders.WOMEN).last()
        
        cls.seat_bow = models.Seat.objects.get(name = 'Bow')
        cls.seat_two = models.Seat.objects.get(name = '2')
        cls.seat_cox = models.Seat.objects.get(name = 'Cox')
        
        cls.athlete = cls.crew.crew_lists.create(
            event = cls.day.event,
            seat = cls.seat_bow,
            name = 'Switch',
        )
        
        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat_bow,
            crew = cls.crew,
            athlete = cls.athlete,
        )
    
    def setUp(self):
        self.purchase.refresh_from_db()
    
    
    def test__athlete__not_in_crew(self):
        """Performs no action and raises an error."""
        
        ath_other = self.crew_alt.crew_lists.create(
            event = self.day.event,
            seat = self.seat_bow,
            name = 'Other',
        )
        
        with self.assertRaises(models.Athlete.DoesNotExist):
            switch(self.purchase, str(ath_other.id), int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__cox(self):
        """Performs no action and raises an error."""
        
        cox = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_cox,
            name = 'Cox',
        )
        
        with self.assertRaises(models.Athlete.DoesNotExist):
            switch(self.purchase, str(cox.id), int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__set(self):
        """Adds an athlete to the purchase."""
        
        self.purchase.athlete = None
        self.purchase.save()
        
        switch(self.purchase, str(self.athlete.id), int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__unset(self):
        """Removes the athlete from the purchase."""
        
        switch(self.purchase, '0', int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)
    
    
    def test__athlete__switch(self):
        """Switches the athlete on the purchase."""
        
        athlete_alt = self.purchase.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_two,
            name = 'Alternative',
        )
        
        switch(self.purchase, str(athlete_alt.id), int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, athlete_alt)
    
    
    def test__athlete__already_purchased(self):
        """Performs no action and raises an error."""
        
        athlete_alt = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_two,
            name = 'Alternative',
        )
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = athlete_alt,
        )
        
        with self.assertRaises(errors.DuplicateAthleteError):
            switch(self.purchase, str(athlete_alt.id), int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__allow_double_unnamed(self):
        """Removes the athlete from the purchase."""
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
        )
        
        switch(self.purchase, '0', int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)
        
    
    def test__seat__unknown(self):
        """Performs no action and raises an error."""
        
        with self.assertRaises(models.Seat.DoesNotExist):
            switch(self.purchase, '0', '0')
    
    
    def test__seat__cox(self):
        """Performs no action and raises an error."""
        
        with self.assertRaises(errors.NinthSeatError):
            switch(self.purchase, '0', str(self.seat_cox.id))
    
    
    def test__seat__unchanged(self):
        """Makes no change."""
        
        switch(self.purchase, '0', int(self.purchase.seat.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_bow)
    
    
    def test__seat__unoccupied(self):
        """Moves the purchase to the new seat and vacates the original seat."""
        
        switch(self.purchase, '0', int(self.seat_two.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)
        self.assertFalse(
            self.team.get_crew(self.day, self.crew.gender).filter(seat = self.seat_bow).exists(),
        )
    
    
    def test__seat__occupied(self):
        """Moves the purchase to the new seat, and moves the other purchase back."""
        
        other_purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew_alt,
        )
        
        switch(self.purchase, '0', int(self.seat_two.id))
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)
        
        other_purchase.refresh_from_db()
        self.assertEqual(other_purchase.seat, self.seat_bow)
    
    
    @tag('query-count')
    def test__query_count(self):
        """Expect:
            (1) SELECT new athlete
            (1) SELECT and LOCK other purchases, and athletes
            (1) SELECT new seat
            (1) UPDATE purchase of target seat
            (1) UPDATE main purchase
        """
        
        self.purchase.athlete = None
        self.purchase.save()
        
        athlete_alt = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_two,
            name = 'Alternative',
        )
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = athlete_alt,
        )
        
        fresh_purchase = models.Purchase.objects.select_related().get(id = self.day.id)
        
        with self.assertNumQueries(5):
            _switch_body(fresh_purchase, int(self.athlete.id), int(self.seat_two.id))

