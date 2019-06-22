from datetime import time, timedelta

from django.test import TestCase, tag
from django.utils import timezone

from .. import models
from .. import patching
from . import fantasy_tags as tags


@tag('market-status')
class Test__Market_Status_Box(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 2))
    def test__open_two_days(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {0:%H:%M} {0:%d/%m/%Y}.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 1))
    def test__open_tomorrow(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} tomorrow.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() + timedelta(minutes = 5))
    def test__open_later_today(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} today.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(days = 1))
    def test__open_until_tomorrow(self, closes_mock, opens_mock):
        """Returns a dismissable info alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'info')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} tomorrow.'.format(
                closes_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__open_until_later(self, closes_mock, opens_mock):
        """Returns a dismissable info alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'warning')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} today.'.format(
                closes_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() - timedelta(minutes = 2))
    def test__after_close(self, closes_mock, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed.',
        )
    
    
    def test__after_close_with_next(self):
        """Returns a non-dismissable danger alert with the open time for the next day.
        
        WARNING: Contains non-standard mocking. May not fail if other code changes.
        """
        
        # Create first day and fix return values
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        day.market_opens = timezone.now() - timedelta(minutes = 5)  # Non-standard mocking
        day.market_closes = timezone.now() - timedelta(minutes = 2)  # Non-standard mocking
        
        # Create later day
        self.event.days.create(
            name = 'Market Status 2',
            date = timezone.now() + timedelta(2),  # Ensure market never opens today
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at 20:00 tomorrow.',
        )
    
    
    def test__non_racing_day(self):
        """Returns a non-dismissable danger alert.
        
        A special case of test__after_close since markets are always closed for non-racing days,
        but market_opens and market_closes do not return datetime objects."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = None,
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed.',
        )


class Test__Bungline_Avatar(TestCase):
    
    def test__standard_use(self):
        """Returns a span with the 'bungline-avatar' class, and containing the bungline number."""
        
        self.assertHTMLEqual(
            tags.bungline_avatar(7),
            '<span class="bungline-avatar">7</span>',
        )
    
    
    def test__not_seat(self):
        """Replaces seat.short with an error indicator if the object passed is not a Seat."""
        
        self.assertHTMLEqual(
            tags.bungline_avatar(None),
            '<span class="bungline-avatar">E</span>',
        )


class Test__Seat_Avatar(TestCase):
    
    def test__standard_use(self):
        """Returns a span with the 'seat-avatar' class, and containing seat.short."""
        
        seat = models.Seat(
            name = 'Seat',
            cox = False,
        )
        seat.save()
        
        self.assertHTMLEqual(
            tags.seat_avatar(seat),
            '<span class="seat-avatar">S</span>',
        )
    
    
    def test__not_seat(self):
        """Replaces seat.short with an error indicator if the object passed is not a Seat."""
        
        self.assertHTMLEqual(
            tags.seat_avatar(None),
            '<span class="seat-avatar">E</span>',
        )

