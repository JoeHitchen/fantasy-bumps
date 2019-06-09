from datetime import time, timedelta
from unittest.mock import patch, PropertyMock

from django.test import TestCase, tag
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import models as auth

from .constants import genders
from . import models
from . import patching


@tag('events-core')
class Test__Event(TestCase):
    
    @classmethod
    def setUpTestData(self):
        self.event = models.Event(
            name = 'Test Event',
            mens_divisions = 3,
            womens_divisions = 3,
            boats_per_division = 2,
        )
        self.event.save()
        
        # Prepare days
        self.yesterday = models.Day(
            event = self.event,
            name = 'Yesterday',
            date = timezone.now() - timedelta(1),
        )
        self.yesterday.save()
        self.today = models.Day(
            event = self.event,
            name = 'Today',
            date = timezone.now(),
        )
        self.today.save()
        self.tomorrow = models.Day(
            event = self.event,
            name = 'Tomorrow',
            date = timezone.now() + timedelta(1),
        )  # Saved per-test due to isolation conflict
        self.future = models.Day(
            event = self.event,
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
        
        self.assertEqual(str(self.event), 'Test Event')
    
    
    @patching.timezone_now_time(19, 59)
    def test__before_rollover(self, timezone_mock):
        """Returns first day from today onwards before 8pm."""
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )
    
    
    @patching.timezone_now_time(20, 00)
    def test__after_rollover(self, timezone_mock):
        """Returns first day from tomorrow onwards before 8pm."""
        
        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )
    
    
    @patching.timezone_now_time(20, 00)
    def test__after_event(self, timezone_mock):
        """Returns last day of the event, if all have passed."""
        
        self.tomorrow.delete()
        self.future.delete()
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )



@tag('events-core')
class Test__Day__Core(TestCase):
    
    @classmethod
    def setUpTestData(self):
        self.event = models.Event(
            name = 'Markets',
            mens_divisions = 3,
            womens_divisions = 3,
            boats_per_division = 2,
        )
        self.event.save()
    
    
    def test__string(self):
        """Returns a day's name as it's string representation."""
        
        day = models.Day(
            event = self.event,
            name = 'Racing',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        day_str = str(day)
        self.assertEqual(day_str, day.name)
    
    
    def test__next__past(self):
        """Returns None if there are no days in the future."""
        
        models.Day(
            event = self.event,
            name = 'Prev',
            date = timezone.now() - timedelta(1),
            first_race_time = time(hour = 12),
        ).save()
        
        curr = models.Day(
            event = self.event,
            name = 'Next',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        curr.save()
        
        self.assertIsNone(curr.next)
    
    
    def test__next__future(self):
        """Returns the next day in the series if there are days in the future."""
        
        curr = models.Day(
            event = self.event,
            name = 'Next',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        curr.save()
        
        future_1 = models.Day(
            event = self.event,
            name = 'Future 1',
            date = timezone.now() + timedelta(1),
            first_race_time = time(hour = 12),
        )
        future_1.save()
        
        models.Day(
            event = self.event,
            name = 'Future 2',
            date = timezone.now() + timedelta(2),
            first_race_time = time(hour = 12),
        ).save()
        
        self.assertEqual(curr.next, future_1)



@tag('events-core')
class Test__Day__Start_Orders(TestCase):
    fixtures = ['basic_event', 'start_orders']
    
    @classmethod
    def setUpTestData(self):
        
        self.event = models.Event.objects.first()
        self.event.womens_divisions = 3
        self.event.boats_per_division = 2
        self.event.save()
        
        self.day = models.Day.objects.first()
    
    
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
    
    
    @patch.object(
        models.Division,
        'start_order',
        new_callable = PropertyMock,
        side_effect = ['Call 1', 'Call 2', 'Call 3'],
    )
    def test__start_order__behaviour(self, start_order_mock):
        """Iteratively calls `start_order` on each division.
        
        ## Only tests that Division.start_order used three times. ##
        """
        
        # Get start orders
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(
            start_order,
            ['Call 1', 'Call 2', 'Call 3'],
        )



@tag('market-status')
class Test__Day__Market_Status(TestCase):
    
    @classmethod
    def setUpTestData(self):
        self.event = models.Event(
            name = 'Markets',
            mens_divisions = 3,
            womens_divisions = 3,
            boats_per_division = 2,
        )
        self.event.save()
    
    
    def test__market_opens__first_race_day(self):
        """First day markets open more than 24h in advance."""
        
        # Create day
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        day.save()
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-4))
        self.assertEqual(open.time(), time(hour = 20))
    
    
    def test__market_opens__later_race_day(self):
        """Later day markets open after racing the previous day."""
        
        # Create days
        now = timezone.now()
        models.Day(
            event = self.event,
            name = 'Markets',
            date = now - timedelta(1),
            first_race_time = time(hour = 12),
        ).save()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        day.save()
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-1))
        self.assertEqual(open.time(), time(hour = 20))
    
    
    def test__market_opens__non_race_day(self):
        """Returns null if no racing occurs."""
        
        # Create days
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
            first_race_time = None,
        )
        day.save()
        
        # Test property
        open = day.market_opens
        self.assertIsNone(open)
    
    
    def test__market_closes__with_race(self):
        """Markets close half an hour before the first race."""
        
        # Create days
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
            first_race_time = time(hour = 12),
        )
        day.save()
        
        # Test property
        close = day.market_closes
        self.assertEqual(close.date(), now.date())
        self.assertEqual(close.time(), time(hour = 11, minute = 30))
    
    
    def test__market_closes__without_race(self):
        """Returns a null value if no racing occurs."""
        
        # Create days
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
            first_race_time = None,
        )
        day.save()
        
        # Test property
        close = day.market_closes
        self.assertIsNone(close)
    
    
    @patching.market_opens(timezone.now() + timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__before_open(self, closes_mock, opens_mock):
        """Returns False if before opening time."""
        
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__between(self, closes_mock, opens_mock):
        """Returns True if between opening time and closing time."""
        
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertTrue(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() - timedelta(minutes = 5))
    def test__market_is_open__after_close(self, closes_mock, opens_mock):
        """Returns False if after closing time."""
        
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 10))
    @patching.market_closes(timezone.now() + timedelta(minutes = 10))
    def test__market_is_open__without_first_race(self, closes_mock, opens_mock):
        """Returns False if first_race_time is not set."""
        
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = timezone.now(),
            first_race_time = None,
        )
        
        self.assertFalse(day.market_is_open)



@tag('events-core')
class Test__Division(TestCase):
    fixtures = ['basic_event', 'start_orders']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
    
    def test__start_order__full(self):
        """Generates a list of crews for the division with bungline numbers."""
        
        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = genders.WOMENS,
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order
        
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
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order
        
        # Check for missing bungline
        self.assertEqual(start_order.count(), 5)
        bunglines = start_order.values_list('bungline', flat = True)
        self.assertNotIn(5, bunglines)



@tag('events-core')
class Test__Crew(TestCase):
    
    def test__string(self):
        """Returns a crew's name as it's string representation."""
        
        crew = models.Crew(
            name = 'New College W1',
            gender = genders.WOMENS,
        )
        crew_str = str(crew)
        self.assertEqual(crew_str, crew.name)



@tag('events-core')
class Test__Position(TestCase):
    fixtures = ['basic_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(name = 'Hertford W1', gender = genders.WOMENS)
        cls.crew.save()
    
    
    def test__unique_pair(self):
        """Raises a DB IntegrityError if a duplicate day/crew pairing created."""
        
        position1 = models.Position(day = self.day, crew = self.crew, rank = 1)
        position2 = models.Position(day = self.day, crew = self.crew, rank = 2)
        
        position1.save()
        self.assertRaises(IntegrityError, position2.save)



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



class Test__Purchase(TestCase):
    fixtures = ['basic_event', 'seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = auth.User.objects.create_user('Team', '', 'pass')
        cls.day = models.Day.objects.first()
        
        cls.crew1 = models.Crew(name = 'Hertford W1', gender = genders.WOMENS)
        cls.crew1.save()
        cls.crew2 = models.Crew(name = 'Hertford W2', gender = genders.WOMENS)
        cls.crew2.save()
        
        cls.seat = models.Seat.objects.first()
    
    
    def test__unique_group(self):
        """Raises a DB IntegrityError if a duplicate team/day/seat group created."""
        
        purchase1 = models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew1,
            seat = self.seat,
        )
        purchase2 = models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew2,
            seat = self.seat,
        )
        
        purchase1.save()
        self.assertRaises(IntegrityError, purchase2.save)

