from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from external import models as ext

from .. import models
from .. import patching
from . import fantasy_tags as tags


class Test__Market_Status_Box(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event(
            name = 'Markets',
            mens_divisions = 3,
            womens_divisions = 3,
            boats_per_division = 2,
        )
        cls.event.save()
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 2))
    def test__open_two_days(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} 05/05/2019.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 1))
    def test__open_tomorrow(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
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
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
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
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
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
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
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
    def test__closed(self, closes_mock, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = models.Day(
            event = self.event,
            name = 'Market Status',
            date = timezone.now(),
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
        
        seat = ext.Seat(
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

