from django.test import TestCase
from django.contrib.auth import models as usr

from external import models as ext
from external.constants import genders

from . import models
from . import utils


class Test__Get_Crew(TestCase):
    fixtures = ['seats', 'basic_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Seats')
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(gender = genders.WOMENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns an empty crew list if no rowers have been purchased."""
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__other_team(self):
        """Does not include rowers purchased by another team."""
        
        other_team = usr.User.objects.create_user('Other')
        
        models.Purchase(
            team = other_team,
            day = self.day,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__other_day(self):
        """Does not include rowers purchased on another day."""
        
        other_day = models.Day.objects.last()
        self.assertNotEqual(other_day, self.day)
        
        models.Purchase(
            team = self.team,
            day = other_day,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__wrong_gender(self):
        """Does not include purchases of the wrong gender."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,  # Is a women's crew
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.MENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__partial_team(self):
        """Returns any purchases matching the criteria."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 1)
    
    
    def test__full_team(self):
        """Returns any purchases matching the criteria."""
        
        for seat in ext.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 9)
    
    
    def test__duplicate_seats(self):
        """Returns any purchases matching the criteria, regardless of duplication."""
        
        for seat in ext.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,
            seat = ext.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 10)



class Test__Has_All_Seats(TestCase):
    fixtures = ['seats', 'basic_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Seats')
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(gender = genders.MENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns false if there are no seats filled."""
        
        value = utils.has_all_seats(models.Purchase.objects.all())
        self.assertFalse(value)
    
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in ext.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        value = utils.has_all_seats(models.Purchase.objects.all())
        self.assertTrue(value)
    
    
    def subtest__missing_seat(self, missing_seat):
        """Returns false if a specific seat is missing."""
        
        for seat in ext.Seat.objects.exclude(name__iexact = missing_seat):
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        value = utils.has_all_seats(models.Purchase.objects.all())
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
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        extra_seat = ext.Seat.objects.get(name__iexact = extra_seat)
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,
            seat = extra_seat,
        ).save()
        
        with self.assertRaises(ValueError):
            utils.has_all_seats(models.Purchase.objects.all())
    
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

