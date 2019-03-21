from django.test import TestCase
from django.contrib.auth import models as usr

from external import models as ext
from external.constants import genders

from . import models
from . import utils


class Test__Get_Crew(TestCase):
    fixtures = ['seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Seats')
        cls.crew = ext.Crew(gender = genders.WOMENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns an empty crew list if no rowers have been added to crew."""
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__other_team(self):
        """Does not include rowers assigned to another team."""
        
        other_team = usr.User.objects.create_user('Other')
        
        models.Rower(
            team = other_team,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__wrong_gender(self):
        """Does not include rowers of the wrong gender."""
        
        models.Rower(
            team = self.team,
            crew = self.crew,  # Is a women's crew
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, genders.MENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__partial_team(self):
        """Returns any rowers it finds."""
        
        models.Rower(
            team = self.team,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertEqual(crew.count(), 1)
    
    
    def test__full_team(self):
        """Returns any rowers it finds."""
        
        for seat in ext.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertEqual(crew.count(), 9)
    
    
    def test__duplicate_seats(self):
        """Returns any rowers it finds, regardless of duplications."""
        
        for seat in ext.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew,
                seat = seat,
            ).save()
        
        models.Rower(
            team = self.team,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertEqual(crew.count(), 10)



class Test__Has_All_Seats(TestCase):
    fixtures = ['seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Seats')
        cls.crew = ext.Crew(gender = genders.MENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns false if there are no seats filled."""
        
        value = utils.has_all_seats(models.Rower.objects.all())
        self.assertFalse(value)
    
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in ext.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew,
                seat = seat,
            ).save()
        
        value = utils.has_all_seats(models.Rower.objects.all())
        self.assertTrue(value)
    
    
    def subtest__missing_seat(self, missing_seat):
        """Returns false if a specific seat is missing."""
        
        for seat in ext.Seat.objects.exclude(name__iexact = missing_seat):
            models.Rower(
                team = self.team,
                crew = self.crew,
                seat = seat,
            ).save()
        
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
            models.Rower(
                team = self.team,
                crew = self.crew,
                seat = seat,
            ).save()
        
        extra_seat = ext.Seat.objects.get(name__iexact = extra_seat)
        models.Rower(
            team = self.team,
            crew = self.crew,
            seat = extra_seat,
        ).save()
        
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

