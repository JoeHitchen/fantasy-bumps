from django.test import TestCase, tag
from django.contrib.auth import models as auth

from .constants import genders, money
from . import models
from . import game_tools as tools


@tag('game-core')
class Test__Purchase_Rollover(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
        cls.team = models.Team.objects.first()
        cls.crews = models.Crew.objects.all()
    
    
    def test__without_athlete(self):
        """Copies all purchases to the next day, including null athlete references."""
        
        # Create simple set of purchases
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                seat = seat,
                crew = self.crews[seat.id],
            )
        
        # Test method
        tools.roll_over_purchases(self.day)
        
        self.assertEqual(
            list(self.day.purchases.values('team', 'crew', 'seat', 'athlete')),
            list(self.day.next.purchases.values('team', 'crew', 'seat', 'athlete')),
        )
    
    
    def test__with_athlete(self):
        """Copies all purchases to the next day, including athlete references."""
        
        # Create athlete
        athlete = models.Athlete.objects.create(
            event = self.day.event,
            crew = self.crews[0],
            seat = models.Seat.objects.first(),
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
        tools.roll_over_purchases(self.day)
        
        self.assertEqual(
            list(self.day.purchases.values('team', 'crew', 'seat', 'athlete')),
            list(self.day.next.purchases.values('team', 'crew', 'seat', 'athlete')),
        )
    
    
    @tag('query-count')
    def test__query_count(self):
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
            tools.roll_over_purchases(self.day)



@tag('game-core')
class Test__All_Investments(TestCase):
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
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        
        days = cls.event.days.all()
        cls.day1 = days[0]
        cls.day2 = days[1]
        cls.day3 = days[2]
        
        # Hertford bump both days; Oriel got bumped both days; Wolfson rowed over day 1
        cls.crew_hert = models.Crew.objects.get(club = 'hert', gender = genders.WOMENS)
        cls.crew_orie = models.Crew.objects.get(club = 'orie', gender = genders.WOMENS)
        cls.crew_wolf = models.Crew.objects.get(club = 'wolf', gender = genders.WOMENS)
        
        cls.team = models.Team.objects.first()
        cls.budgets = cls.team.entries.create(event = cls.event)
        
        cls.seat = models.Seat.objects.first()
        cls.all_seats = models.Seat.objects.all()
    
    
    def test__bump_up__partial_crew(self):
        """Increases the budget and balance for the correct gender."""
        
        start_value = self.crew_hert.value(self.day1)
        value_change = self.crew_hert.value(self.day2) - start_value
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + value_change)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bump_up__full_crew(self):
        """Increases the budget and balance for the correct gender."""
        
        start_value = self.crew_hert.value(self.day1)
        value_change = self.crew_hert.value(self.day2) - start_value
        self.assertTrue(value_change > 0)
        
        payout = round( 0.15 * start_value )  # noqa: E201 E202
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change + 9 * payout,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout)
    
    
    def test__row_over__partial_crew(self):
        """No changes to budgets or balance."""
        
        start_value = self.crew_wolf.value(self.day1)
        value_change = self.crew_wolf.value(self.day2) - start_value
        self.assertEqual(value_change, 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_wolf, seat = self.seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__row_over__full_crew(self):
        """Increases the budget and balance for the correct gender."""
        
        start_value = self.crew_wolf.value(self.day1)
        value_change = self.crew_wolf.value(self.day2) - start_value
        self.assertEqual(value_change, 0)
        
        payout = round( 0.05 * start_value )  # noqa: E201 E202
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_wolf, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + 9 * payout)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout)
    
    
    def test__bumped_down(self):
        """Decreases the budget for the correct gender, but not the balance."""
        
        value_change = self.crew_orie.value(self.day2) - self.crew_orie.value(self.day1)
        self.assertTrue(value_change < 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_orie, seat = self.seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + value_change)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__different_day(self):
        """Ignores purchases for other days."""
        
        value_change = self.crew_hert.value(self.day3) - self.crew_hert.value(self.day2)
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day2, crew = self.crew_hert, seat = self.seat)
        
        tools.evaluate_all_investments(self.day1)
        
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
        
        tools.evaluate_all_investments(self.day1)
        
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
            (1) SELECT all seats
            (3) Create payout matrix
            (1) UPDATE entries
            
            Assumes crew value lookups are query-free (e.g. from caching)
        """
        
        value_change = self.crew_hert.value(self.day2) - self.crew_hert.value(self.day1)
        self.assertTrue(value_change > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert, seat = self.seat)
        
        with self.assertNumQueries(8):
            tools.evaluate_all_investments(self.day1)

