from django.test import TestCase

from . import models
from . import utils
from external import models as ext


class Test__Has_All_Seats(TestCase):
    fixtures = ['seats']
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in ext.Seat.objects.all():
            models.Rower(seat = seat).save()
        
        value = utils.has_all_seats(models.Rower.objects.all())
        self.assertTrue(value)
    
    
    def subtest__missing_seat(self, missing_seat):
        """Returns false if a specific seat is missing."""
        
        for seat in ext.Seat.objects.exclude(name__iexact = missing_seat):
            models.Rower(seat = seat).save()
        
        value = utils.has_all_seats(models.Rower.objects.all())
        self.assertFalse(value)
    
    def test__missing_seat__bow(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('bow')
    
    def test__missing_seat__2(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('2')
    
    def test__missing_seat__3(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('3')
    
    def test__missing_seat__4(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('4')
    
    def test__missing_seat__5(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('5')
    
    def test__missing_seat__6(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('6')
    
    def test__missing_seat__7(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('7')
    
    def test__missing_seat__stroke(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('stroke')
    
    def test__missing_seat__cox(self):
        """Returns false if a specific seat is missing."""
        self.subtest__missing_seat('cox')
    
    
    def subtest__extra_seat(self, extra_seat):
        """Raises ValueError if any seat present twice."""
        
        for seat in ext.Seat.objects.all():
            models.Rower(seat = seat).save()
        extra_seat = ext.Seat.objects.get(name__iexact = extra_seat)
        models.Rower(seat = extra_seat).save()
        
        with self.assertRaises(ValueError):
            utils.has_all_seats(models.Rower.objects.all())
    
    def test__extra_seat__bow(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('bow')
    
    def test__extra_seat__2(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('2')
    
    def test__extra_seat__3(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('3')
    
    def test__extra_seat__4(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('4')
    
    def test__extra_seat__5(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('5')
    
    def test__extra_seat__6(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('6')
    
    def test__extra_seat__7(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('7')
    
    def test__extra_seat__stroke(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('stroke')
    
    def test__extra_seat__cox(self):
        """Raises ValueError if any seat present twice."""
        self.subtest__extra_seat('cox')

