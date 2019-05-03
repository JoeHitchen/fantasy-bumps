from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone

from external.constants import genders

from . import models
from . import patching


class Test__Day(TestCase):
    fixtures = ['basic_event', 'start_orders']
    
    @classmethod
    def setUpTestData(self):
        
        self.event = models.Event.objects.first()
        self.event.womens_divisions = 3
        self.event.boats_per_division = 2
        self.event.save()
        
        self.day = models.Day.objects.first()
    
    
    def test__start_order__number_of_mens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.MENS)
        self.assertEqual(len(start_order), 2)
    
    
    def test__start_order__number_of_womens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(len(start_order), 3)
    
    
    def test__start_order__number_of_boats(self):
        """Has the correct number of boats in each divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(start_order[0].count(), 2)
        self.assertEqual(start_order[1].count(), 2)
        self.assertEqual(start_order[2].count(), 3)  # Extra boat in last division
    
    
    def test__start_order__womens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.WOMENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertTrue(genders.WOMENS in div_genders)
        self.assertFalse(genders.MENS in div_genders)
    
    
    def test__start_order__mens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.MENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertFalse(genders.WOMENS in div_genders)
        self.assertTrue(genders.MENS in div_genders)



class Test__Day__Markets(TestCase):
    
    @classmethod
    def setUpTestData(self):
        self.event = models.Event(
            name = 'Markets',
            mens_divisions = 3,
            womens_divisions = 3,
            boats_per_division = 2,
        )
        self.event.save()
    
    
    def test__market_opens__first_day(self):
        """First day markets open more than 24h in advance."""
        
        # Create day
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
        )
        day.save()
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-4))
        self.assertEqual(open.time(), time(hour = 20))
    
    
    def test__market_opens__later_day(self):
        """Later day markets open after racing the previous day."""
        
        # Create days
        now = timezone.now()
        models.Day(
            event = self.event,
            name = 'Markets',
            date = now - timedelta(1),
        ).save()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
        )
        day.save()
        
        # Test property
        open = day.market_opens
        self.assertEqual(open.date() - now.date(), timedelta(-1))
        self.assertEqual(open.time(), time(hour = 20))
    
    
    def test__market_closes(self):
        """Markets close at 11:30AM on the day of racing."""
        
        # Create days
        now = timezone.now()
        day = models.Day(
            event = self.event,
            name = 'Markets',
            date = now,
        )
        day.save()
        
        # Test property
        close = day.market_closes
        self.assertEqual(close.date(), now.date())
        self.assertEqual(close.time(), time(hour = 11, minute = 30))
    
    
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

