from django.test import TestCase
from django.contrib.auth import models as usr

from external import models as ext_models

from . import models
from . import forms


class Test__Buy(TestCase):
    fixtures = ['seats', 'start_orders']
    
    def setUp(self):
        self.team = usr.User.objects.create_user('Buy')
        self.crew = ext_models.Crew.objects.first().id
        self.seat = ext_models.Seat.objects.first().id
    
    
    def test__save(self):
        """Uses an extra argument to complete the object."""
        
        form = forms.Buy({
            'crew': self.crew,
            'seat': self.seat,
        })
        purchase = form.save(self.team)
        self.assertEqual(purchase.team, self.team)



class Test__Sell(TestCase):
    fixtures = ['seats', 'start_orders']
    
    def setUp(self):
        self.team = usr.User.objects.create_user('Buy')
        self.crew = ext_models.Crew.objects.filter(gender = 'W').first()
        self.seat = ext_models.Seat.objects.first()
    
    
    def test__init__team_missing(self):
        """The 'team' kwarg is required."""
        
        with self.assertRaises(TypeError):
            forms.Sell()
    
    
    def test__init__team_stored(self):
        """The 'team' kwarg is stored for future use."""
        
        form = forms.Sell(team = self.team)
        self.assertEqual(form.team, self.team)
    
    
    def test__save__deletes_purchases(self):
        """Removes any and all purchases for that team, seat, and gender. Returns gender."""
        
        models.Purchase(
            team = self.team,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
        )
        self.assertTrue(form.is_valid())
        
        out = form.save()
        self.assertEqual(models.Purchase.objects.count(), 0)
        self.assertEqual(out, 'W')
    
    
    def test__save__ignores_other_teams(self):
        """Does not delete purchases from other teams."""
        
        other_team = usr.User.objects.create_user('other', '', '')
        models.Purchase(
            team = other_team,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)
    
    
    def test__save__ignores_other_seats(self):
        """Does not delete purchases in other seats."""
        
        models.Purchase(
            team = self.team,
            seat = ext_models.Seat.objects.last(),
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)
    
    
    def test__save__ignores_other_gender(self):
        """Does not delete purchases of the other gender."""
        
        other_crew = ext_models.Crew.objects.exclude(gender = self.crew.gender).first()
        
        models.Purchase(
            team = self.team,
            seat = self.seat,
            crew = other_crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)

