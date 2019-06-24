from django.test import TestCase
from django.contrib.auth import models as auth

from .constants import genders
from . import models
from . import utils


class Test__Get_Crew(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(gender = genders.WOMENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns an empty crew list if no rowers have been purchased."""
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__other_team(self):
        """Does not include rowers purchased by another team."""
        
        other_team = auth.User.objects.create_user('Other').team
        
        models.Purchase(
            team = other_team,
            day = self.day,
            crew = self.crew,
            seat = models.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__other_day(self):
        """Does not include rowers purchased on another day."""
        
        other_day = models.Day.objects.last()
        self.assertNotEqual(other_day, self.day)
        
        models.Purchase(
            team = self.team,
            day = other_day,
            crew = self.crew,
            seat = models.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__wrong_gender(self):
        """Does not include purchases of the wrong gender."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,  # Is a women's crew
            seat = models.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = self.team.get_crew(self.day, genders.MENS)
        self.assertEqual(crew.count(), 0)
    
    
    def test__partial_team(self):
        """Returns any purchases matching the criteria."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew,
            seat = models.Seat.objects.get(name = 'Bow'),
        ).save()
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 1)
    
    
    def test__full_team(self):
        """Returns any purchases matching the criteria."""
        
        for seat in models.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew,
                seat = seat,
            ).save()
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertEqual(crew.count(), 9)



class Test__Has_All_Seats(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew(gender = genders.MENS)
        cls.crew.save()
    
    
    def test__empty_crew(self):
        """Returns false if there are no seats filled."""
        
        value = utils.has_all_seats(models.Purchase.objects.all())
        self.assertFalse(value)
    
    
    def test__all_seats(self):
        """Returns true if all seats are present exactly once."""
        
        for seat in models.Seat.objects.all():
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
        
        for seat in models.Seat.objects.exclude(name__iexact = missing_seat):
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



class Test__Reverse_Gender(TestCase):
    
    def test__men_to_women(self):
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(genders.MENS), genders.WOMENS)
    
    def test__women_to_men(self):
        """Returns opposite gender."""
        self.assertEqual(utils.reverse_gender(genders.WOMENS), genders.MENS)

