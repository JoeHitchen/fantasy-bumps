from datetime import time, timedelta

from django.test import TestCase, tag
from django.utils import timezone

from .constants import genders
from . import models
from . import patching


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
    
    
    def test__number_of_mens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.MENS)
        self.assertEqual(len(start_order), 2)
    
    
    def test__number_of_womens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(len(start_order), 3)
    
    
    def test__number_of_boats(self):
        """Has the correct number of boats in each divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(start_order[0].count(), 2)
        self.assertEqual(start_order[1].count(), 2)
        self.assertEqual(start_order[2].count(), 3)  # Extra boat in last division
    
    
    def test__womens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.WOMENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertTrue(genders.WOMENS in div_genders)
        self.assertFalse(genders.MENS in div_genders)
    
    
    def test__mens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.MENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertFalse(genders.WOMENS in div_genders)
        self.assertTrue(genders.MENS in div_genders)



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
class Test__Crew(TestCase):
    
    def test__string(self):
        """Returns a crew's name as it's string representation."""
        
        crew = models.Crew(
            name = 'New College W1',
            gender = genders.WOMENS,
        )
        crew_str = str(crew)
        self.assertEqual(crew_str, crew.name)



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

