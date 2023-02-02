from django.test import TestCase, tag
from django.contrib.auth import models as auth

from core.tests import exists

from . import models
from . import errors
from .constants import Genders, money
from .transactions import buy, sell, switch, _buy_body, _sell_body, _switch_body


class Test__Buy(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    
    team: models.Team
    day: models.Day
    seat: models.Seat
    crew: models.Crew
    crew_mens: models.Crew
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.select_related().first())
        cls.seat = exists(models.Seat.objects.first())
        cls.crew = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())
        cls.crew_mens = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
    
    
    def setUp(self) -> None:
        self.budgets = self.team.entries.get(event = self.day.event)
    
    
    def test__not_racing(self) -> None:
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
    
    
    def test__insufficient_funds(self) -> None:
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
    
    
    def test__womens_crew(self) -> None:
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__mens_crew(self) -> None:
        """Deducts the crew's value from the women's balance and creates the purchase."""
        
        buy(self.team, self.day, self.seat, self.crew_mens)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
        
        self.assertEqual(self.team.purchases.count(), 1)
    
    
    def test__already_filled(self) -> None:
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
    
    
    def test__other_gender_filled(self) -> None:
        """Doesn't block a team/seat/day combination if the genders don't match."""
        
        self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew_mens)
        
        buy(self.team, self.day, self.seat, self.crew)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 2)
    
    
    def test__budgets_missing(self) -> None:
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
    
    
    def test__with_athlete(self) -> None:
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
        self.assertEqual(exists(self.team.purchases.first()).athlete, athlete)
    
    
    def test__with_duplicate_athlete(self) -> None:
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
            seat = exists(models.Seat.objects.last()),
            athlete = athlete,
        )

        buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
        
        self.assertEqual(self.team.purchases.count(), 2)
        self.assertEqual(exists(self.team.purchases.first()).athlete, athlete)
        self.assertIsNone(exists(self.team.purchases.last()).athlete)
    
    
    def test__with_duplicate_absent_athlete(self) -> None:
        """Performs the standard action and creates a second Purchase with no athlete."""
        
        athlete = None
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = exists(models.Seat.objects.last()),
            athlete = athlete,
        )

        buy(self.team, self.day, self.seat, self.crew, athlete)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE - money.PRICE_MAX)
    
    
    @tag('query-count')
    def test__query_count__standard(self) -> None:
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
            seat = exists(models.Seat.objects.last()),
            athlete = athlete,
        )
        
        fresh_day = models.Day.objects.select_related().get(id = self.day.id)
        
        with self.assertNumQueries(5):
            _buy_body(self.team, fresh_day, self.seat, self.crew, athlete)
    
    
    @tag('query-count')
    def test__query_count__without_budgets(self) -> None:
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
    
    user: auth.User
    day: models.Day
    seat: models.Seat
    crew: models.Crew
    crew_mens: models.Crew
    budgets: models.GameEntry
    purchase: models.Purchase
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = exists(auth.User.objects.first())
        cls.day = exists(models.Day.objects.select_related().first())
        cls.seat = exists(models.Seat.objects.first())
        cls.crew = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())
        cls.crew_mens = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        
        cls.budgets = cls.user.team.entries.create(event = cls.day.event)
        
        cls.purchase = cls.user.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )

    
    def setUp(self) -> None:
        self.budgets = self.user.team.entries.get(event = self.day.event)
        self.purchase.save()
    
    
    def test__missing_budgets(self) -> None:
        """Performs no action and raises an error."""
        
        self.budgets.delete()  # Do not check for budget-update side effect
        
        with self.assertRaises(models.GameEntry.DoesNotExist):
            sell(self.purchase)
        
        self.purchase.refresh_from_db()  # Does not fail
    
    
    def test__already_deleted(self) -> None:
        """Performs no action and raises an error."""
        
        self.purchase.delete()  # Do not check for purchase-delete side effect
        
        with self.assertRaises(models.Purchase.DoesNotExist):
            sell(self.purchase)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__mens_crew(self) -> None:
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
    
    
    def test__womens_crew(self) -> None:
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
    def test__query_count(self) -> None:
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
    
    team: models.Team
    day: models.Day
    crew: models.Crew
    crew_alt: models.Crew
    seat_bow: models.Seat
    seat_two: models.Seat
    seat_cox: models.Seat
    athlete: models.Athlete
    purchase: models.Purchase
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())
        cls.crew = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())
        cls.crew_alt = exists(models.Crew.objects.filter(gender = Genders.WOMEN).last())
        
        cls.seat_bow = exists(models.Seat.objects.get(name = 'Bow'))
        cls.seat_two = exists(models.Seat.objects.get(name = '2'))
        cls.seat_cox = exists(models.Seat.objects.get(name = 'Cox'))
        
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
    
    def setUp(self) -> None:
        self.purchase.refresh_from_db()
    
    
    def test__athlete__not_in_crew(self) -> None:
        """Performs no action and raises an error."""
        
        ath_other = self.crew_alt.crew_lists.create(
            event = self.day.event,
            seat = self.seat_bow,
            name = 'Other',
        )
        
        with self.assertRaises(errors.WrongCrewError):
            switch(self.purchase, self.purchase.seat, ath_other)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__cox(self) -> None:
        """Performs no action and raises an error."""
        
        cox = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_cox,
            name = 'Cox',
        )
        
        with self.assertRaises(errors.ReverseNinthSeatError):
            switch(self.purchase, self.purchase.seat, cox)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__set(self) -> None:
        """Adds an athlete to the purchase."""
        
        self.purchase.athlete = None
        self.purchase.save()
        
        switch(self.purchase, self.purchase.seat, self.athlete)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__unset(self) -> None:
        """Removes the athlete from the purchase."""
        
        switch(self.purchase, self.purchase.seat, None)
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)
    
    
    def test__athlete__switch(self) -> None:
        """Switches the athlete on the purchase."""
        
        athlete_alt = self.purchase.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat_two,
            name = 'Alternative',
        )
        
        switch(self.purchase, self.purchase.seat, athlete_alt)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, athlete_alt)
    
    
    def test__athlete__already_purchased(self) -> None:
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
            switch(self.purchase, self.purchase.seat, athlete_alt)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.athlete)
    
    
    def test__athlete__allow_double_unnamed(self) -> None:
        """Removes the athlete from the purchase."""
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
        )
        
        switch(self.purchase, self.purchase.seat, None)
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)
    
    
    def test__seat__cox(self) -> None:
        """Performs no action and raises an error."""
        
        with self.assertRaises(errors.NinthSeatError):
            switch(self.purchase, self.seat_cox, None)
    
    
    def test__seat__unchanged(self) -> None:
        """Makes no change."""
        
        switch(self.purchase, self.purchase.seat, None)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_bow)
    
    
    def test__seat__unoccupied(self) -> None:
        """Moves the purchase to the new seat and vacates the original seat."""
        
        switch(self.purchase, self.seat_two, None)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)
        self.assertFalse(
            self.team.get_crew(self.day, self.crew.gender).filter(seat = self.seat_bow).exists(),
        )
    
    
    def test__seat__occupied(self) -> None:
        """Moves the purchase to the new seat, and moves the other purchase back."""
        
        other_purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew_alt,
        )
        
        switch(self.purchase, self.seat_two, None)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)
        
        other_purchase.refresh_from_db()
        self.assertEqual(other_purchase.seat, self.seat_bow)
    
    
    @tag('query-count')
    def test__query_count(self) -> None:
        """Expect:
            (1) SELECT and LOCK other purchases, and athletes
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
        purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = athlete_alt,
        )
        
        fresh_purchase = (
            models.Purchase.objects
            .select_related('team', 'day', 'crew', 'seat', 'athlete')
            .get(id = purchase.id)
        )
        
        with self.assertNumQueries(3):
            _switch_body(fresh_purchase, self.seat_two, self.athlete)

