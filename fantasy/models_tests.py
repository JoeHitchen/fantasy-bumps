from datetime import datetime, date, time, timedelta
from unittest.mock import patch

from django.test import TestCase, tag
from django.utils import timezone
from django.db import IntegrityError, models as db
from django.contrib.auth import models as auth

from .constants import Genders, GENDERS_OVERALL, timings, money, Clubs
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
            date = timezone.localtime().date() - timedelta(1),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )
        cls.today = cls.event.days.create(
            name = 'Today',
            date = timezone.localtime().date(),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )
        cls.tomorrow = models.Day(
            event = cls.event,
            name = 'Tomorrow',
            date = timezone.localtime().date() + timedelta(1),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )  # Saved per-test due to isolation conflict
        cls.future = models.Day(
            event = cls.event,
            name = 'Future',
            date = timezone.localtime().date() + timedelta(2),
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
    
    
    def test__first_day__standard(self):
        """Returns the first day associated with the event."""
        self.assertEqual(self.event.first_day, self.yesterday)
    
    
    def test__first_day__prefetched(self):
        """Returns the first day associated with the event from a prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(self.event.first_day, self.yesterday)
    
    
    @tag('query-count')
    def test__first_day__query_count(self):
        """Expect:
            (1) SELECT first day
        """
        with self.assertNumQueries(1):
            self.event.first_day
    
    
    @tag('query-count')
    def test__first_day__prefetched_query_count(self):
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            self.event.first_day
    
    
    def test__last_racing_day__standard(self):
        """Returns the last day of racing for the event."""
        self.assertEqual(self.event.last_racing_day, self.tomorrow)  # Future does not have races
    
    
    def test__last_racing_day__prefetched(self):
        """Returns the last day of racing for the event from a prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(self.event.last_racing_day, self.tomorrow)  # Future does not have races
    
    
    @tag('query-count')
    def test__last_racing_day__query_count(self):
        """Expect:
            (1) SELECT last day with a race time
        """
        
        with self.assertNumQueries(1):
            self.event.last_racing_day
    
    
    @tag('query-count')
    def test__last_racing_day__prefetched_query_count(self):
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            self.event.last_racing_day
    
    
    @patching.localtime_time(timings.MARKET_OPENS, timedelta(minutes = -1))
    def test__active_day__before_rollover__standard(self, timezone_mock):
        """Before 8pm, returns first day from today onwards."""
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )
    
    
    @patching.localtime_time(timings.MARKET_OPENS, timedelta(minutes = -1))
    def test__active_day__before_rollover__prefetched(self, timezone_mock):
        """Before 8pm, returns first day from today onwards using as prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(
            self.event.active_day,
            self.today,
        )
    
    
    @tag('query-count')
    @patching.localtime_time(timings.MARKET_OPENS, timedelta(minutes = -1))
    def test__active_day__before_rollover__query_count(self, timezone_mock):
        """Expect:
            (1) SELECT first day today onwards
        """
        
        with self.assertNumQueries(1):
            self.event.active_day
    
    
    @tag('query-count')
    @patching.localtime_time(timings.MARKET_OPENS, timedelta(minutes = -1))
    def test__active_day__before_rollover__prefetched_query_count(self, timezone_mock):
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            self.event.active_day
    
    
    @patching.localtime_time(timings.MARKET_OPENS)
    def test__active_day__after_rollover__standard(self, timezone_mock):
        """After 8pm, returns first day from tomorrow onwards."""
        
        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )
    
    
    @patching.localtime_time(timings.MARKET_OPENS)
    def test__active_day__after_rollover__prefetched(self, timezone_mock):
        """After 8pm, returns first day from tomorrow onwards from a prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )
    
    
    @tag('query-count')
    @patching.localtime_time(timings.MARKET_OPENS)
    def test__active_day__after_rollover__query_count(self, timezone_mock):
        """Expect:
            (1) SELECT first day tomorrow onwards
        """
        
        with self.assertNumQueries(1):
            self.event.active_day
    
    
    @tag('query-count')
    @patching.localtime_time(timings.MARKET_OPENS)
    def test__active_day__after_rollover__prefetched_query_count(self, timezone_mock):
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            self.event.active_day
    
    
    def test__active_day__after_event__standard(self):
        """Returns last day of the event, if all have passed."""
        
        models.Day.objects.update(date = db.F('date') - timedelta(5))
        
        self.assertEqual(
            self.event.active_day,
            self.future,
        )
    
    
    def test__active_day__after_event__prefetched(self):
        """Returns last day of the event from a prefetched set of days, if all have passed."""
        
        models.Day.objects.update(date = db.F('date') - timedelta(5))
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(
            self.event.active_day,
            self.future,
        )
    
    
    @tag('query-count')
    def test__active_day__after_event__query_count(self):
        """Expect:
            (1) SELECT any days after today/tomorrow (depending on time)
            (1) SELECT the last day of the event
        """
        
        models.Day.objects.update(date = db.F('date') - timedelta(5))
        
        with self.assertNumQueries(2):
            self.event.active_day
    
    
    @tag('query-count')
    def test__active_day__after_event__prefetched_query_count(self):
        """Returns last day of the event from a prefetched set of days, if all have passed."""
        
        models.Day.objects.update(date = db.F('date') - timedelta(5))
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            self.event.active_day
    
    
    def test__num_crews__mens(self):
        """Adds up all the men's division sizes."""
        
        self.event.mens_division_sizes = [8, 9, 10, 11, 12, 13, 14]
        
        self.assertEqual(self.event.num_crews(Genders.MEN), 77)
    
    
    def test__num_crews__womens(self):
        """Adds up all the women's division sizes."""
        
        self.event.womens_division_sizes = [9, 10, 11, 12, 13]
        
        self.assertEqual(self.event.num_crews(Genders.WOMEN), 55)
    
    
    @tag('query-count')
    def test__num_crews__query_count(self):
        """NONE EXPECTED (but an important part of the crew valuation chain)"""
        
        with self.assertNumQueries(0):
            self.event.num_crews(Genders.WOMEN)



@tag('events-core')
class Test__Day__Core(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.today = timezone.localtime().date()
    
    
    def test__string(self):
        """Returns a day's name as it's string representation."""
        
        day = self.event.days.create(
            name = 'Racing',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        day_str = str(day)
        self.assertEqual(day_str, day.name)
    
    
    def test__next__past_only__standard(self):
        """Returns None if there are no days in the future."""
        
        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertIsNone(curr.next)
    
    
    def test__next__past_only__prefetched(self):
        """Returns None if there are no days in the future, using a prefetched set of days."""
        
        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertIsNone(curr.next)
    
    
    @tag('query-count')
    def test__next__past_only__query_count(self):
        """Expect:
            (1) SELECT the next day in the event
        """
        
        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        with self.assertNumQueries(1):
            curr.next
    
    
    @tag('query-count')
    def test__next__past_only__prefetched_query_count(self):
        """Expect:
            No queries
        """
        
        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            curr.next
    
    
    def test__next__future__standard(self):
        """Returns the next day in the series if there are days in the future."""
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        future_1 = self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertEqual(curr.next, future_1)
    
    
    def test__next__future__prefetched(self):
        """Returns the next day if there are days in the future, from a prefetched set of days."""
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        future_1 = self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(curr.next, future_1)
    
    
    @tag('query-count')
    def test__next__future__query_count(self):
        """Expect:
            (1) SELECT the next day in the event
        """
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        with self.assertNumQueries(1):
            curr.next
    
    
    @tag('query-count')
    def test__next__future__prefetched_query_count(self):
        """Expect:
            No queries
        """
        
        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            curr.next
    
    
    def test__prev__past__standard(self):
        """Returns the previous day in the series if there are days in the past."""
        
        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        prev_1 = self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertEqual(curr.prev, prev_1)
    
    
    def test__prev__past__prefetched(self):
        """Returns the previous day if there are days in the past from a prefetched set of days."""
        
        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        prev_1 = self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertEqual(curr.prev, prev_1)
    
    
    @tag('query-count')
    def test__prev__past__query_count(self):
        """Expect:
            (1) SELECT the previous day in the event
        """
        
        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        with self.assertNumQueries(1):
            curr.prev
    
    
    @tag('query-count')
    def test__prev__past__prefetched_query_count(self):
        """Expect:
            No queries
        """
        
        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            curr.prev
    
    
    def test__prev__future_only__standard(self):
        """Returns None if there are no days in the past."""
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertIsNone(curr.prev)
    
    
    def test__prev__future_only__prefetched(self):
        """Returns None if there are no days in the past."""
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        self.assertIsNone(curr.prev)
    
    
    @tag('query-count')
    def test__prev__future_only__query_count(self):
        """Expect:
            (1) SELECT the previous day in the event
        """
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        with self.assertNumQueries(1):
            curr.prev
    
    
    @tag('query-count')
    def test__prev__future_only__prefetched_query_count(self):
        """Expect:
            No queries
        """
        
        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))
        
        with self.assertNumQueries(0):
            curr.prev
    
    
    def test__first_race__winter(self):
        """Constructs a datetime object from the date, first race time, and system timezone."""
        
        race_date = date.fromisoformat('2021-01-05')
        race_time = time(11, 30)
        first_race = self.event.days.create(
            date = race_date,
            first_race_time = race_time,
            last_race_time = time(hour = 18, minute = 30),
        ).first_race
        
        self.assertIsInstance(first_race, datetime)
        self.assertEqual(first_race.date(), race_date)
        self.assertEqual(first_race.time(), race_time)
        self.assertEqual(first_race.tzname(), 'GMT')
    
    
    def test__first_race__summer(self):
        """Constructs a datetime object from the date, first race time, and system timezone."""
        
        race_date = date.fromisoformat('2021-07-05')
        race_time = time(11, 30)
        first_race = self.event.days.create(
            date = race_date,
            first_race_time = race_time,
            last_race_time = time(hour = 18, minute = 30),
        ).first_race
        
        self.assertIsInstance(first_race, datetime)
        self.assertEqual(first_race.date(), race_date)
        self.assertEqual(first_race.time(), race_time)
        self.assertEqual(first_race.tzname(), 'BST')
    
    
    def test__last_race__winter(self):
        """Constructs a datetime object from the date, last race time, and system timezone."""
        
        race_date = date.fromisoformat('2021-01-05')
        race_time = time(18, 45)
        last_race = self.event.days.create(
            date = race_date,
            first_race_time = time(hour = 12),
            last_race_time = race_time,
        ).last_race
        
        self.assertIsInstance(last_race, datetime)
        self.assertEqual(last_race.date(), race_date)
        self.assertEqual(last_race.time(), race_time)
        self.assertEqual(last_race.tzname(), 'GMT')
    
    
    def test__last_race__summer(self):
        """Constructs a datetime object from the date, last race time, and system timezone."""
        
        race_date = date.fromisoformat('2021-07-05')
        race_time = time(18, 45)
        last_race = self.event.days.create(
            date = race_date,
            first_race_time = time(hour = 12),
            last_race_time = race_time,
        ).last_race
        
        self.assertIsInstance(last_race, datetime)
        self.assertEqual(last_race.date(), race_date)
        self.assertEqual(last_race.time(), race_time)
        self.assertEqual(last_race.tzname(), 'BST')



@tag('events-core')
class Test__Day__Start_Orders(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1']
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.event.mens_division_sizes = [2, 3]
        cls.event.womens_division_sizes = [2, 2, 3]
        cls.event.save()
        
        cls.day = cls.event.days.first()
    
    
    def test__divisions__mens(self):
        """Has the division structure as described by the event."""
        
        # Get divisions
        divisions = self.day.divisions(Genders.MEN)
        
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
        divisions = self.day.divisions(Genders.WOMEN)
        
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
        self.day.start_order(Genders.MEN)
        self.day.divisions.assert_called_once_with(Genders.MEN)
    
    
    @patch.object(models.Day, 'divisions', autospec = True)
    def test__start_order__womens(self, day_divisions_mock):
        """Passes the gender argument onto the divisions method."""
        
        # Get start orders
        self.day.start_order(Genders.WOMEN)
        self.day.divisions.assert_called_once_with(Genders.WOMEN)
    
    
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
        day_divisions = self.day.divisions(Genders.WOMEN)
        day_start_order = self.day.start_order(Genders.WOMEN)
        
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
        
        start_order = self.day.start_order(Genders.WOMEN, extend = lambda so: (so, so))
        
        self.assertEqual(start_order_mock.call_count, 3)
        for index, div_start_order in enumerate(start_order):
            with self.subTest(div = index + 1):
                div_spec = (self.day.id, Genders.WOMEN, index + 1)
                self.assertEqual(div_start_order, (div_spec, div_spec))



@tag('market-status')
class Test__Day__Market_Status(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    def test__market_opens__non_race_day(self):
        """Market opening time is undefined if no racing is scheduled."""
        
        race_date = date.fromisoformat('2021-07-05')
        day = self.event.days.create(
            name = 'Main',
            date = race_date,
            first_race_time = None,
            last_race_time = None,
        )
        
        self.assertIsNone(day.market_opens)
    
    
    def test__market_opens__first_race_day__winter(self):
        """The first day's markets opening is three days prior."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        
        self.assertEqual(day.market_opens.date(), day.date - timedelta(3))
        self.assertEqual(day.market_opens.time(), timings.MARKET_OPENS)
        self.assertEqual(day.market_opens.tzname(), 'GMT')
    
    
    def test__market_opens__first_race_day__summer(self):
        """The first day's markets opening is three days prior."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        
        self.assertEqual(day.market_opens.date(), day.date - timedelta(3))
        self.assertEqual(day.market_opens.time(), timings.MARKET_OPENS)
        self.assertEqual(day.market_opens.tzname(), 'BST')
    
    
    def test__market_opens__later_race_day__winter(self):
        """Later day markets open after racing the previous day."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        prev = self.event.days.create(
            name = 'Prior',
            date = day.date - timedelta(2),  # Demonstrates linked to previous day, not yesterday
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('17:45:00'),
        )
        
        self.assertEqual(day.market_opens.date(), prev.date)
        self.assertEqual(day.market_opens.time(), timings.MARKET_OPENS)
        self.assertEqual(day.market_opens.tzname(), 'GMT')
    
    
    def test__market_opens__later_race_day__summer(self):
        """Later day markets open after racing the previous day."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        prev = self.event.days.create(
            name = 'Prior',
            date = day.date - timedelta(2),  # Demonstrates linked to previous day, not yesterday
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('17:45:00'),
        )
        
        self.assertEqual(day.market_opens.date(), prev.date)
        self.assertEqual(day.market_opens.time(), timings.MARKET_OPENS)
        self.assertEqual(day.market_opens.tzname(), 'BST')
    
    
    def test__market_closes__without_race(self):
        """Market closing time is undefined if no racing is scheduled."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = None,
            last_race_time = None,
        )
        
        self.assertIsNone(day.market_closes)
    
    
    def test__market_closes__with_winter_race(self):
        """Markets close half an hour before the first race."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        
        self.assertEqual(day.market_closes.date(), day.date)
        self.assertEqual(day.market_closes.time().isoformat(), '11:30:00')
        self.assertEqual(day.market_closes.tzname(), 'GMT')
    
    
    def test__market_closes__with_summer_race(self):
        """Markets close half an hour before the first race."""
        
        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        
        self.assertEqual(day.market_closes.date(), day.date)
        self.assertEqual(day.market_closes.time().isoformat(), '11:30:00')
        self.assertEqual(day.market_closes.tzname(), 'BST')
    
    
    @patching.market_opens(timezone.localtime() + timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__before_open(self, closes_mock, opens_mock):
        """Returns False if before opening time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__between(self, closes_mock, opens_mock):
        """Returns True if between opening time and closing time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertTrue(day.market_is_open)
    
    
    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() - timedelta(minutes = 5))
    def test__market_is_open__after_close(self, closes_mock, opens_mock):
        """Returns False if after closing time."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__non_racing_day(self, closes_mock, opens_mock):
        """Returns False if it is not a racing day."""
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = None,
            last_race_time = None,
        )
        
        self.assertFalse(day.market_is_open)
    
    
    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__held_closed(self, closes_mock, opens_mock):
        """Returns False if the event has markets held closed."""
        
        self.event.market_held_closed = True
        self.event.save()
        
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
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
            gender = Genders.WOMEN,
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
                self.assertEqual(position.crew.gender, Genders.WOMEN)
                self.assertTrue(position.rank >= 3)
                self.assertTrue(position.rank <= 8)
    
    
    def test__start_order__partial(self):
        """Safely excludes missing bunglines from the returned data."""
        
        # Leave position 7 (Bungline 5) empty
        models.Position.objects.filter(crew__gender = Genders.WOMEN, rank = 7).delete()
        
        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = Genders.WOMEN,
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
        event.womens_division_sizes = [3]
        
        days = event.days.all()
        cls.day1 = days[0]
        
        crews = models.Crew.objects.filter(gender = Genders.WOMEN)
        
        cls.crew_top = crews[0]
        cls.crew_top.positions.create(day = cls.day1, rank = 1)
        
        cls.crew_middle = crews[1]
        cls.crew_middle.positions.create(day = cls.day1, rank = 2)
        
        cls.crew_bottom = crews[2]
        cls.crew_bottom.positions.create(day = cls.day1, rank = 3)
        
        cls.crew_unranked = crews[3]
        
        crew_mens = models.Crew.objects.filter(gender = Genders.MEN).first()
        crew_mens.positions.create(day = cls.day1, rank = 4)  # Added to ensure gender isolation
    
    
    def test__string__womens_first(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College W1')
    
    
    def test__string__mens_first(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.MEN,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College M1')
    
    
    def test__string__lower_boat(self):
        """Displays a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 2,
        )
        self.assertEqual(str(crew), 'New College W2')
    
    
    def test__tuple__womens_first(self):
        """Contains a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 1,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.WOMEN, 1))
    
    
    def test__tuple__mens_first(self):
        """Contains a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.MEN,
            rank = 1,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.MEN, 1))
    
    
    def test__tuple__lower_boat(self):
        """Contains a crew's club, gender, and rank."""
        
        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 2,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.WOMEN, 2))
    
    
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
        cls.crew = models.Crew(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)
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
        
        cls.crew = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.WOMEN, rank = 1)
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
        
        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__other_team(self):
        """Does not include rowers purchased by another team."""
        
        other_team = auth.User.objects.create_user('Other').team
        
        other_team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, Genders.WOMEN)
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
        
        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__wrong_gender(self):
        """Does not include purchases of the wrong gender."""
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,  # Is a women's crew
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, Genders.MEN)
        self.assertEqual(crew.count(), 0)
    
    
    def test__get_crew__partial_team(self):
        """Returns any purchases matching the criteria."""
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )
        
        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 1)
    
    
    def test__get_crew__full_team(self):
        """Returns any purchases matching the criteria."""
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                crew = self.crew,
                seat = seat,
            )
        
        crew = self.team.get_crew(self.day, Genders.WOMEN)
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
        cls.team_4 = auth.User.objects.create_user('Four', '', '').team
        
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
        cls.game_entry_4 = cls.event.fantasies.create(
            team = cls.team_4,  # Alphabetically before but otherwise identical to 'Three'
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
            list(self.event.fantasies.extend_financials().rank_by(GENDERS_OVERALL)),
            [self.game_entry_1, self.game_entry_4, self.game_entry_3, self.game_entry_2],
        )
    
    
    def test__query__rank_by__mens(self):
        """Ranks teams by the men's budget."""
        
        self.assertEqual(
            list(self.event.fantasies.extend_financials().rank_by(Genders.MEN)),
            [self.game_entry_2, self.game_entry_1, self.game_entry_4, self.game_entry_3],
        )
    
    
    def test__query__rank_by__womens(self):
        """Ranks teams by the women's budget."""
        
        self.assertEqual(
            list(self.event.fantasies.extend_financials().rank_by(Genders.WOMEN)),
            [self.game_entry_1, self.game_entry_4, self.game_entry_3, self.game_entry_2],
        )



@tag('game-core')
class Test__Purchase(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    def test__athlete_delete(self):
        """Athlete references should be nulled if the athlete is deleted.
        
        This is important for not dropping purchases when honouring an athlete deletion request.
        """
        
        # Create athlete
        day = models.Day.objects.select_related('event').first()
        crew = models.Crew.objects.first()
        seat = models.Seat.objects.first()
        athlete = crew.crew_lists.create(event = day.event, seat = seat, name = 'Deletion')
        
        # Create purchase
        team = models.Team.objects.first()
        purchase = team.purchases.create(day = day, crew = crew, seat = seat, athlete = athlete)
        
        # Delete athlete
        athlete.delete()
        with self.assertRaises(models.Athlete.DoesNotExist):
            athlete.refresh_from_db()  # Verify deletion completed
        purchase.refresh_from_db()
        self.assertIsNone(purchase.athlete)

