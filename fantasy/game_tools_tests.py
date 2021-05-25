from django.test import TestCase, tag
from django.contrib.auth import models as auth

from .constants import Genders, money, Clubs
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
        
        # Wadham bumped day 1; Oriel got bumped both days; Wolfson rowed over day 1
        cls.crew_wadh_w = models.Crew.objects.get(club = Clubs.WADH, gender = Genders.WOMEN)
        cls.crew_orie_w = models.Crew.objects.get(club = Clubs.ORIE, gender = Genders.WOMEN)
        cls.crew_wolf_w = models.Crew.objects.get(club = Clubs.WOLF, gender = Genders.WOMEN)
        
        # Balliol bumped day 1; Hertford got bumped day 1; Pembroke rowed over both days
        cls.crew_ball_m = models.Crew.objects.get(club = Clubs.BALL, gender = Genders.MEN)
        cls.crew_hert_m = models.Crew.objects.get(club = Clubs.HERT, gender = Genders.MEN)
        cls.crew_pemb_m = models.Crew.objects.get(club = Clubs.PEMB, gender = Genders.MEN)
        cls.crew_catz_m = models.Crew.objects.get(club = Clubs.SCAT, gender = Genders.MEN)
        # ^ Catz bumped day 2
        
        cls.team = models.Team.objects.first()
        cls.budgets = cls.team.entries.create(event = cls.event)
        
        cls.seat = models.Seat.objects.first()
        cls.all_seats = models.Seat.objects.all()
    
    
    def test__bump_down__men_complete(self):
        """Crews lose value and no bonuses are awarded, regardless of completeness."""
        
        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)
        
        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 1 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bump_down__women_complete(self):
        """Crews lose value and no bonuses are awarded, regardless of completeness."""
        
        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)
        
        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 1 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bump_down__both_complete(self):
        """Crews lose value and no bonuses are awarded, regardless of completeness."""
        
        value_change_men = self.crew_hert_m.value(self.day2) - self.crew_hert_m.value(self.day1)
        self.assertTrue(value_change_men < 0)
        
        value_change_women = self.crew_orie_w.value(self.day2) - self.crew_orie_w.value(self.day1)
        self.assertTrue(value_change_women < 0)
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_hert_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_orie_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__row_over__men_complete(self):
        """No value changes, but bonuses are awarded if both crews complete."""
        
        value_change_men = self.crew_pemb_m.value(self.day2) - self.crew_pemb_m.value(self.day1)
        self.assertEqual(value_change_men, 0)
        
        value_change_women = self.crew_wolf_w.value(self.day2) - self.crew_wolf_w.value(self.day1)
        self.assertEqual(value_change_women, 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__row_over__women_complete(self):
        """No value changes, but bonuses are awarded if both crews complete."""
        
        value_change_men = self.crew_pemb_m.value(self.day2) - self.crew_pemb_m.value(self.day1)
        self.assertEqual(value_change_men, 0)
        
        value_change_women = self.crew_wolf_w.value(self.day2) - self.crew_wolf_w.value(self.day1)
        self.assertEqual(value_change_women, 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__row_over__both_complete(self):
        """No value changes, but bonuses are awarded if both crews complete."""
        
        start_value_men = self.crew_pemb_m.value(self.day1)
        payout_men = round(0.07 * start_value_men)
        value_change_men = self.crew_pemb_m.value(self.day2) - start_value_men
        self.assertEqual(value_change_men, 0)
        
        start_value_women = self.crew_wolf_w.value(self.day1)
        payout_women = round(0.07 * start_value_women)
        value_change_women = self.crew_wolf_w.value(self.day2) - start_value_women
        self.assertEqual(value_change_women, 0)
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_pemb_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wolf_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE + 9 * payout_women)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout_women)
    
    
    def test__bump_up__men_complete(self):
        """Values increase regardless of completeness, bonuses awarded only if both complete."""
        
        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)
        
        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 1 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bump_up__women_complete(self):
        """Values increase regardless of completeness, bonuses awarded only if both complete."""
        
        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)
        
        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)
        
        self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = self.seat)
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 1 * value_change_men,
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * value_change_women,
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__bump_up__both_complete(self):
        """Values increase regardless of completeness, bonuses awarded only if both complete."""
        
        start_value_men = self.crew_ball_m.value(self.day1)
        payout_men = round(0.21 * start_value_men)
        value_change_men = self.crew_ball_m.value(self.day2) - start_value_men
        self.assertTrue(value_change_men > 0)
        
        start_value_women = self.crew_wadh_w.value(self.day1)
        payout_women = round(0.21 * start_value_women)
        value_change_women = self.crew_wadh_w.value(self.day2) - start_value_women
        self.assertTrue(value_change_women > 0)
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(
            self.budgets.mens_budget,
            money.INITIAL_BALANCE + 9 * (value_change_men + payout_men),
        )
        self.assertEqual(
            self.budgets.womens_budget,
            money.INITIAL_BALANCE + 9 * (value_change_women + payout_women),
        )
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE + 9 * payout_men)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE + 9 * payout_women)
    
    
    def test__different_day(self):
        """Ignores purchases for other days."""
        
        value_change_men = self.crew_catz_m.value(self.day3) - self.crew_catz_m.value(self.day2)
        self.assertTrue(value_change_men > 0)
        
        value_change_women = self.crew_wolf_w.value(self.day3) - self.crew_wolf_w.value(self.day2)
        self.assertTrue(value_change_women > 0)
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day2, crew = self.crew_catz_m, seat = seat)
            self.team.purchases.create(day = self.day2, crew = self.crew_wolf_w, seat = seat)
        
        tools.evaluate_all_investments(self.day1)
        
        self.budgets.refresh_from_db()
        self.assertEqual(self.budgets.mens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_budget, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.mens_balance, money.INITIAL_BALANCE)
        self.assertEqual(self.budgets.womens_balance, money.INITIAL_BALANCE)
    
    
    def test__different_team(self):
        """Ignores purchases for other teams."""
        
        other_team = auth.User.objects.create_user('Other').team
        
        value_change_men = self.crew_catz_m.value(self.day3) - self.crew_catz_m.value(self.day2)
        self.assertTrue(value_change_men > 0)
        
        value_change_women = self.crew_wolf_w.value(self.day3) - self.crew_wolf_w.value(self.day2)
        self.assertTrue(value_change_women > 0)
        
        for seat in self.all_seats:
            other_team.purchases.create(day = self.day2, crew = self.crew_catz_m, seat = seat)
            other_team.purchases.create(day = self.day2, crew = self.crew_wolf_w, seat = seat)
        
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
            (4) Create payout matrix  (3 if day.next is cached)
            (1) UPDATE entries
        """
        
        value_change_men = self.crew_ball_m.value(self.day2) - self.crew_ball_m.value(self.day1)
        self.assertTrue(value_change_men > 0)
        
        value_change_women = self.crew_wadh_w.value(self.day2) - self.crew_wadh_w.value(self.day1)
        self.assertTrue(value_change_women > 0)
        
        for seat in self.all_seats:
            self.team.purchases.create(day = self.day1, crew = self.crew_ball_m, seat = seat)
            self.team.purchases.create(day = self.day1, crew = self.crew_wadh_w, seat = seat)
        
        fresh_day = models.Day.objects.select_related().get(pk = self.day1.pk)
        
        with self.assertNumQueries(9):
            tools.evaluate_all_investments(fresh_day)

