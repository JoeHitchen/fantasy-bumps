from django.test import TestCase

from . import models


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

