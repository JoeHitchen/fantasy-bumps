from django.test import TestCase

from external import models as ext

from . import fantasy_tags as tags


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

