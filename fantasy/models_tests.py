from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase, tag
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import models as auth

from .constants import genders, timings, money
from . import models
from . import patching
from . import utils


@tag('events-core')
class Test__Event(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        
        # Prepare days
        cls.yesterday = cls.event.days.create(
            name = 'Yesterday',
            date = timezone.now() - timedelta(1),
            first_race_time = time(12, 00),
        )
        cls.today = cls.event.days.create(
            name = 'Today',
            date = timezone.now(),
            first_race_time = time(12, 00),
        )
        cls.tomorrow = models.Day(
            event = cls.event,
            name = 'Tomorrow',
            date = timezone.now() + timedelta(1),
            first_race_time = time(12, 00),
        )  # Saved per-test due to isolation conflict
        cls.future = models.Day(
            event = cls.event,
            name = 'Future',
            date = timezone.now() + timedelta(2),
        )  # Saved per-test due to isolation conflict
    
    
    def setUp(self):
        
        # Save future days for delete-safe test isolation
        self.tomorrow.save()
        self.future.save()
        
        # Clear event cache
        self.event.active_day
        del self.event.active_day
    
    
    def test__string(self):
        """Returns an event's name as its string representation."""
        
        self.assertEqual(str(self.event), 'Demo 2019')
    
    
    def test__first_day(self):
        """Returns the first day associated with the event."""
        self.assertEqual(self.event.first_day, self.yesterday)
    
    
    def test__last_racing_day(self):
        """Returns the last day of racing for the event."""
        self.assertEqual(self.event.last_racing_day, self.tomorrow)  # Future does not have races
    
    
    @patching.timezone_now_time(timings.MARKET_OPENS, timedelta(minutes = -1))
    def test__active_day__before_rollover(self, timezone_mock):
        """Returns first day from today onwards before 8pm."""
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )
    
    
    @patching.timezone_now_time(timings.MARKET_OPENS)
    def test__active_day__after_rollover(self, timezone_mock):
        """Returns first day from tomorrow onwards after 8pm."""
        
        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )
    
    
    @patching.timezone_now_time(timings.MARKET_OPENS)
    def test__active_day__after_event(self, timezone_mock):
        """Returns last day of the event, if all have passed."""
        
        self.tomorrow.delete()
        self.future.delete()
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )
    
    
    def test__num_crews__mens(self):
        """Multiplies the number of divisions and the boats per division, then adds one."""
        
        self.event.mens_divisions = 7
        self.event.boats_per_division = 13
        
        self.assertEqual(self.event.num_crews(genders.MENS), 92)
    
    
    def test__num_crews__womens(self):
        """Multiplies the number of divisions and the boats per division, then adds one."""
        
        self.event.womens_divisions = 5
        self.event.boats_per_division = 12
        
        self.assertEqual(self.event.num_crews(genders.WOMENS), 61)
    
    
    @tag('query-count')
    def test__num_crews__query_count(self):
        """NONE EXPECTED (but an important part of the crew valuation chain)"""
        
        with self.assertNumQueries(0):
            self.event.num_crews(genders.WOMENS)



@tag('events-core')
class Test__Day__Core(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    def test__string(self):
        """Returns a day's name as it's string representation."""
        
        day = self.event.days.create(
            name = 'Racing',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        day_str = str(day)
        self.assertEqual(day_str, day.name)
    
    
    def test__next__past_only(self):
        """Returns None if there are no days in the future."""
        
        self.event.days.create(
            name = 'Prev',
            date = timezone.now() - timedelta(1),
            first_race_time = time(hour = 12),
        )
        
        curr = self.event.days.create(
            name = 'Next',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertIsNone(curr.next)
    
    
    def test__next__future(self):
        """Returns the next day in the series if there are days in the future."""
        
        curr = self.event.days.create(
            name = 'Next',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        future_1 = self.event.days.create(
            name = 'Future 1',
            date = timezone.now() + timedelta(1),
            first_race_time = time(hour = 12),
        )
        
        self.event.days.create(
            name = 'Future 2',
            date = timezone.now() + timedelta(2),
            first_race_time = time(hour = 12),
        )
        
        self.assertEqual(curr.next, future_1)
    
    
    def test__prev__past(self):
        """Returns the previous day in the series if there are days in the past."""
        
        self.event.days.create(
            name = 'Prev 2',
            date = timezone.now() - timedelta(2),
            first_race_time = time(hour = 12),
        )
        
        prev_1 = self.event.days.create(
            name = 'Prev 1',
            date = timezone.now() - timedelta(1),
            first_race_time = time(hour = 12),
        )
        
        curr = self.event.days.create(
            name = 'Curr',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertEqual(curr.prev, prev_1)
    
    
    def test__prev__future_only(self):
        """Returns None if there are no days in the past."""
        
        curr = self.event.days.create(
            name = 'Curr',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.event.days.create(
            name = 'Next',
            date = timezone.now() + timedelta(1),
            first_race_time = time(hour = 12),
        )
        
        self.assertIsNone(curr.prev)
    
    
    def test__first_race(self):
        """Returns a datetime object for the first race of the day."""
        
        first_race = self.event.days.create(
            date = timezone.now(),
            first_race_time = time(11, 30),
        ).first_race
        
        self.assertIsInstance(first_race, datetime)
        self.assertEqual(first_race.date(), timezone.now().date())
        self.assertEqual(first_race.time(), time(11, 30))
        self.assertEqual(first_race.tzinfo, timezone.now().tzinfo)



@tag('events-core')
class Test__Day__Start_Orders(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1']
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.event.womens_divisions = 3
        cls.event.boats_per_division = 2
        cls.event.save()
        
        cls.day = cls.event.days.first()
    
    
    def test__divisions__mens(self):
        """Has the division structure as described by the event."""
        
        # Get divisions
        divisions = self.day.divisions(genders.MENS)
        
        # Test division structure
        self.assertEqual(len(divisions), 2)
        
        div1 = divisions[0]
        self.assertEqual(div1.top_bungline, 1)
        self.assertEqual(div1.bottom_bungline, 2)
        
        div2 = divisions[1]
        self.assertEqual(div2.top_bungline, 3)
        self.assertEqual(div2.bottom_bungline, 5)
    
    
    def test__divisions__womens(self):
        """Has the division structure as described by the event."""
        
        # Get divisions
        divisions = self.day.divisions(genders.WOMENS)
        
        # Test division structure
        self.assertEqual(len(divisions), 3)
        
        div1 = divisions[0]
        self.assertEqual(div1.top_bungline, 1)
        self.assertEqual(div1.bottom_bungline, 2)
        
        div2 = divisions[1]
        self.assertEqual(div2.top_bungline, 3)
        self.assertEqual(div2.bottom_bungline, 4)
        
        div3 = divisions[2]
        self.assertEqual(div3.top_bungline, 5)
        self.assertEqual(div3.bottom_bungline, 7)
    
    
    @patch.object(models.Day, 'divisions', autospec = True)
    def test__start_order__mens(self, day_divisions_mock):
        """Passes the gender argument onto the divisions method."""
        
        # Get start orders
        self.day.start_order(genders.MENS)
        self.day.divisions.assert_called_once_with(genders.MENS)
    
    
    @patch.object(models.Day, 'divisions', autospec = True)
    def test__start_order__womens(self, day_divisions_mock):
        """Passes the gender argument onto the divisions method."""
        
        # Get start orders
        self.day.start_order(genders.WOMENS)
        self.day.divisions.assert_called_once_with(genders.WOMENS)
    
    
    @patch(
        'fantasy.models.Division.start_order',
        autospec = True,
        side_effect = lambda self: self,
    )
    def test__start_order__behaviour(self, start_order_mock):
        """Iteratively calls `start_order` on each division.
        
        A mocked Division.start_order returns the division instance it is called on.
        """
        
        # Get start orders
        day_divisions = self.day.divisions(genders.WOMENS)
        day_start_order = self.day.start_order(genders.WOMENS)
        
        self.assertEqual(start_order_mock.call_count, 3)
        for index, call in enumerate(start_order_mock.call_args_list):
            with self.subTest(call_index = index):
                self.assertEqual(call, ((day_divisions[index],),))
        
        self.assertEqual(day_start_order, day_divisions)
    
    
    @patch(
        'fantasy.models.Division.start_order',
        autospec = True,
        side_effect = lambda self: (self.day.id, self.gender, self.number),
    )
    def test__start_order__extend(self, start_order_mock):
        """Calls optional extend on each division start order.
        
        Tests indirectly by mocking the return value of Division.start_order and extend.
        """
        
        start_order = self.day.start_order(genders.WOMENS, extend = lambda so: (so, so))
        
        self.assertEqual(start_order_mock.call_count, 3)
        for index, div_start_order in enumerate(start_order):
            with self.subTest(div = index + 1):
                div_spec = (self.day.id, genders.WOMENS, index + 1)
                self.assertEqual(div_start_order, (div_spec, div_spec))



@tag('market-status')
class Test__Day__Market_Status(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    def test__market_opens__first_race_day(self):
        """First day markets open more than 24h in advance."""
        
        # Create day
        now = timezone.now()
        day = self.event.days.create(
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-4))
        self.assertEqual(open.time(), timings.MARKET_OPENS)
    
    
    def test__market_opens__later_race_day(self):
        """Later day markets open after racing the previous day."""
        
        # Create days
        now = timezone.now()
        self.event.days.create(
            name = 'Markets',
            date = now - timedelta(1),
            first_race_time = time(hour = 12),
        )
        day = self.event.days.create(
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-1))
        self.assertEqual(open.time(), timings.MARKET_OPENS)
    
    
    def test__market_opens__non_race_day(self):
        """Returns null if no racing occurs."""
        
        # Create days
        now = timezone.now()
        day = self.event.days.create(
            name = 'Markets',
            date = now,
            first_race_time = None,
        )
        
        # Test property
        open = day.market_opens
        self.assertIsNone(open)
    
    
    def test__market_closes__with_race(self):
        """Markets close half an hour before the first race."""
        
        # Create days
        now = timezone.now()
        day = self.event.days.create(
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        
        # Test property
        close = day.market_closes
        self.assertEqual(close.date(), now.date())
        self.assertEqual(close.time(), time(hour = 11, minute = 30))
    
    
    def test__market_closes__without_race(self):
        """Returns a null value if no racing occurs."""
        
        # Create days
        now = timezone.now()
        day = self.event.days.create(
            name = 'Markets',
            date = now,
            first_race_time = None,
        )
        
        # Test property
        close = day.market_closes
        self.assertIsNone(close)
    
    
    @patching.market_opens(timezone.now() + timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__before_open(self, closes_mock, opens_mock):
        """Returns False if before opening time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__between(self, closes_mock, opens_mock):
        """Returns True if between opening time and closing time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertTrue(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() - timedelta(minutes = 5))
    def test__market_is_open__after_close(self, closes_mock, opens_mock):
        """Returns False if after closing time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__without_first_race(self, closes_mock, opens_mock):
        """Returns False if first_race_time is not set."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.now(),
            first_race_time = None,
        )
        
        self.assertFalse(day.market_is_open)



@tag('events-core')
class Test__Division(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
    
    def test__start_order__full(self):
        """Generates a list of crews for the division with bungline numbers."""
        
        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = genders.WOMENS,
            number = 2,
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order()
        
        self.assertEqual(start_order.count(), 6)
        
        # Iterate over start order objects
        for idx, position in enumerate(start_order):
            with self.subTest(idx = idx):
                
                # Test individual bungline
                self.assertEqual(position.bungline, idx + 1)
                self.assertEqual(position.crew.gender, genders.WOMENS)
                self.assertTrue(position.rank >= 3)
                self.assertTrue(position.rank <= 8)
    
    
    def test__start_order__partial(self):
        """Safely excludes missing bunglines from the returned data."""
        
        # Leave position 7 (Bungline 5) empty
        models.Position.objects.filter(crew__gender = genders.WOMENS, rank = 7).delete()
        
        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = genders.WOMENS,
            number = 2,
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order()
        
        # Check for missing bungline
        self.assertEqual(start_order.count(), 5)
        bunglines = start_order.values_list('bungline', flat = True)
        self.assertNotIn(5, bunglines)



@tag('events-core')
class Test__Crew(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews']
    
    @classmethod
    def setUpTestData(cls):
        event = models.Event.objects.first()
        event.womens_divisions = 1
        event.boats_per_division = 2  # Extra crew added in "last" division
        
        days = event.days.all()
        cls.day1 = days[0]
        
        crews = models.Crew.objects.filter(gender = genders.WOMENS)
        
        cls.crew_top = crews[0]
        cls.crew_top.positions.create(day = cls.day1, rank = 1)
        
        cls.crew_middle = crews[1]
        cls.crew_middle.positions.create(day = cls.day1, rank = 2)
        
        cls.crew_bottom = crews[2]
        cls.crew_bottom.positions.create(day = cls.day1, rank = 3)
        
        cls.crew_unranked = crews[3]
        
        crew_mens = models.Crew.objects.filter(gender = genders.MENS).first()
        crew_mens.positions.create(day = cls.day1, rank = 4)  # Added to ensure gender isolation
    
    
    def test__string__womens_first(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = 'newc',
            gender = genders.WOMENS,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College W1')
    
    
    def test__string__mens_first(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = 'newc',
            gender = genders.MENS,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College M1')
    
    
    def test__string__lower_boat(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = 'newc',
            gender = genders.WOMENS,
            rank = 2,
        )
        self.assertEqual(str(crew), 'New College W2')
    
    
    def test__value__no_ranking(self):
        """Returns zero if the crew has no position for that day."""
        self.assertEqual(self.crew_unranked.value(self.day1), 0)
    
    
    def test__value__top_crew(self):
        """Returns the maximum price."""
        self.assertEqual(self.crew_top.value(self.day1), money.PRICE_MAX)
    
    
    def test__value__bottom_crew(self):
        """Returns the minimum price."""
        self.assertEqual(self.crew_bottom.value(self.day1), money.PRICE_MIN)
    
    
    def test__value__middle_crew(self):
        """Returns the price from the pricing algorithm."""
        self.assertEqual(self.crew_middle.value(self.day1), utils.pricing(2, 3))
    
    
    @tag('query-count')
    def test__value__query_count(self):
        """Expect:
            (1) SELECT crew's position
        """
        
        with self.assertNumQueries(1):
            self.crew_top.value(self.day1)



@tag('events-core')
class Test__Position(TestCase):
    fixtures = ['dev_event', 'dev_days']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(club = 'hert', gender = genders.WOMENS, rank = 1)
        cls.crew.save()
    
    
    def test__unique_pair(self):
        """Raises a DB IntegrityError if a duplicate day/crew pairing created."""
        
        self.day.ranking.create(crew = self.crew, rank = 1)
        
        with self.assertRaises(IntegrityError):
            self.day.ranking.create(crew = self.crew, rank = 2)



class Test__Seat(TestCase):
    
    def test__short__empty(self):
        """Raises expected error when Seat.name empty."""
        
        seat = models.Seat(name = '')
        
        with self.assertRaises(IndexError):
            seat.short
    
    
    def test__short__one_char(self):
        """Gives first character of Seat.name."""
        
        seat = models.Seat(name = 'S')
        self.assertEqual(seat.short, 'S')
    
    
    def test__short__multi_char(self):
        """Gives first character of Seat.name."""
        
        seat = models.Seat(name = 'Seat')
        self.assertEqual(seat.short, 'S')
    
    
    def test__string(self):
        """Returns a seat's name as it's string representation."""
        
        seat = models.Seat(name = 'Name')
        self.assertEqual(str(seat), 'Name')



class Test__Athlete(TestCase):
    fixtures = ['dev_event', 'dev_crews', 'seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.crew = models.Crew.objects.first()
        cls.seat = models.Seat.objects.first()
    
    
    def test__string(self):
        """Returns a athlete's name as their string representation."""
        
        athlete = models.Athlete(name = 'Test Athlete')
        athlete_str = str(athlete)
        self.assertEqual(athlete_str, athlete.name)
    
    
    def test__unique_pair(self):
        """Raises a DB IntegrityError if a duplicate event/crew/seat pairing created."""
        
        self.event.crew_lists.create(crew = self.crew, seat = self.seat, name = 'Test Athlete')
        
        with self.assertRaises(IntegrityError):
            self.event.crew_lists.create(
                crew = self.crew,
                seat = self.seat,
                name = 'Test Athlete',
            )



@tag('game-core')
class Test__Team(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        
        cls.crew = models.Crew.objects.create(club = 'newc', gender = genders.WOMENS, rank = 1)
        cls.bow = models.Seat.objects.get(name = 'Bow')
        
    
    def test__auto_create(self):
        """Is auto created every time a User instance is created."""
        
        user = auth.User.objects.create_user('A User', '', '')
        self.assertTrue(hasattr(user, 'team'))
    
    
    def test__string(self):
        """Returns the related username as it's string representation."""
        
        user = auth.User.objects.create_user('A User', '', '')
        team = user.team
        
        self.assertEqual(str(team), 'A User')
    
    
    def test__get_crew__empty_crew(self):
        """Returns an empty crew list if no rowers have been purchased."""
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__other_team(self):
        """Does not include rowers purchased by another team."""
        
        other_team = auth.User.objects.create_user('Other').team
        
        other_team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__other_day(self):
        """Does not include rowers purchased on another day."""
        
        other_day = models.Day.objects.last()
        self.assertNotEqual(other_day, self.day)
        
        self.team.purchases.create(
            day = other_day,
            crew = self.crew,
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__wrong_gender(self):
        """Does not include purchases of the wrong gender."""
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,  # Is a women's crew
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, genders.MENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__partial_team(self):
        """Returns any purchases matching the criteria."""
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 1)
    
    
    def test__get_crew__full_team(self):
        """Returns any purchases matching the criteria."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                crew = self.crew,
                seat = seat,
            )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 9)



@tag('game-core')
class Test__GameEntry(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        
        cls.team_1 = auth.User.objects.create_user('One', '', '').team
        cls.team_2 = auth.User.objects.create_user('Two', '', '').team
        cls.team_3 = auth.User.objects.create_user('Three', '', '').team
        
        cls.game_entry_1 = cls.event.fantasies.create(
            team = cls.team_1,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 110,
            womens_balance = 103,
        )
        cls.game_entry_2 = cls.event.fantasies.create(
            team = cls.team_2,
            mens_budget = 754,
            womens_budget = 456,
            mens_balance = 120,
            womens_balance = 105,
        )
        cls.game_entry_3 = cls.event.fantasies.create(
            team = cls.team_3,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 117,
            womens_balance = 112,
        )
    
    
    def test__unique_group(self):
        """Raises a DB IntegrityError if a duplicate team/event group created."""
        
        with self.assertRaises(IntegrityError):
            self.event.fantasies.create(team = self.team_1)  # Already exists
    
    
    def test__query__extend_financials__total_budget(self):
        """Totals the gendered budgets."""
        
        entry = models.GameEntry.objects.extend_financials().first()
        self.assertEqual(entry.total_budget, 701 + 713)
    
    
    def test__query__extend_financials__mens_crew(self):
        """Calculates the value of men's crews."""
        
        entry = models.GameEntry.objects.extend_financials().first()
        self.assertEqual(entry.mens_crew_value, 701 - 110)
    
    
    def test__query__extend_financials__womens_crew(self):
        """Calculates the value of women's crews."""
        
        entry = models.GameEntry.objects.extend_financials().first()
        self.assertEqual(entry.womens_crew_value, 713 - 103)
    
    
    def test__query__extend_financials__total_crew(self):
        """Calculates the value of both crews."""
        
        entry = models.GameEntry.objects.extend_financials().first()
        self.assertEqual(entry.total_crew_value, 701 + 713 - 103 - 110)
    
    
    def test__query__rank_by__total(self):
        """Ranks teams by the total budget."""
        
        self.assertEqual(
            list(self.event.fantasies.extend_financials().rank_by(genders.TOTALS)),
            [self.game_entry_1, self.game_entry_3, self.game_entry_2],
        )
    
    
    def test__query__rank_by__mens(self):
        """Ranks teams by the men's budget."""
        
        self.assertEqual(
            list(self.event.fantasies.extend_financials().rank_by(genders.MENS)),
            [self.game_entry_2, self.game_entry_1, self.game_entry_3],
        )
    
    
    def test__query__rank_by__womens(self):
        """Ranks teams by the women's budget."""
        
        self.assertEqual(
            list(self.event.fantasies.extend_financials().rank_by(genders.WOMENS)),
            [self.game_entry_1, self.game_entry_3, self.game_entry_2],
        )

