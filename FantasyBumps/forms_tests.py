from django.test import TestCase
from django.contrib.auth import models as usr

from external import models as ext_models

from . import models
from . import forms
from . import patching


class Test__Buy(TestCase):
    fixtures = ['seats', 'basic_event', 'start_orders']
    
    def setUp(self):
        self.team = usr.User.objects.create_user('Buy')
        self.day = models.Day.objects.first()
        self.crew = ext_models.Crew.objects.first().id
        self.seat = ext_models.Seat.objects.first().id
    
    
    def test__init__kwargs_stored(self):
        """Stores the 'team' and 'day' keyword arguments."""
        
        form = forms.Buy(team = self.team, day = self.day)
        self.assertEqual(form.team, self.team)
        self.assertEqual(form.day, self.day)
    
    
    @patching.markets_open(True)
    def test__valid__markets_open(self, markets_mock):
        """Purchases allowed when markets are open."""
        
        form = forms.Buy(
            {'crew': self.crew, 'seat': self.seat},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
    
    
    @patching.markets_open(False)
    def test__valid__markets_closed(self, markets_mock):
        """Purchases allowed when markets are open."""
        
        form = forms.Buy(
            {'crew': self.crew, 'seat': self.seat},
            team = self.team,
            day = self.day,
        )
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors, {
            '__all__': ['Markets are not currently open.'],
        })
    
    
    @patching.markets_open(True)
    def test__save(self, markets_mock):
        """Uses an extra argument to complete the object."""
        
        form = forms.Buy(
            {'crew': self.crew, 'seat': self.seat},
            team = self.team,
            day = self.day,
        )
        purchase = form.save()
        self.assertEqual(purchase.team, self.team)
        self.assertEqual(purchase.day, self.day)



class Test__Sell(TestCase):
    fixtures = ['seats', 'basic_event', 'start_orders']
    
    def setUp(self):
        self.team = usr.User.objects.create_user('Buy')
        self.day = models.Day.objects.first()
        self.crew = ext_models.Crew.objects.filter(gender = 'W').first()
        self.seat = ext_models.Seat.objects.first()
    
    
    def test__init__kwargs_stored(self):
        """Stores the 'team' and 'day' keyword arguments."""
        
        form = forms.Sell(team = self.team, day = self.day)
        self.assertEqual(form.team, self.team)
        self.assertEqual(form.day, self.day)
    
    
    @patching.markets_open(True)
    def test__valid__markets_open(self, markets_mock):
        """Sales allowed when markets are open."""
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
    
    
    @patching.markets_open(False)
    def test__valid__markets_closed(self, markets_mock):
        """Sales allowed when markets are open."""
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors, {
            '__all__': ['Markets are not currently open.'],
        })
    
    
    @patching.markets_open(True)
    def test__save__deletes_purchases(self, markets_mock):
        """Removes any and all purchases for that team, seat, and gender. Returns gender."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
        
        out = form.save()
        self.assertEqual(models.Purchase.objects.count(), 0)
        self.assertEqual(out, 'W')
    
    
    @patching.markets_open(True)
    def test__save__ignores_other_teams(self, markets_mock):
        """Does not delete purchases from other teams."""
        
        other_team = usr.User.objects.create_user('other', '', '')
        models.Purchase(
            team = other_team,
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)
    
    
    @patching.markets_open(True)
    def test__save__ignores_other_days(self, markets_mock):
        """Does not delete purchases for other days."""
        
        other_day = models.Day.objects.last()
        self.assertNotEqual(other_day, self.day)
        models.Purchase(
            team = self.team,
            day = other_day,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)
    
    
    @patching.markets_open(True)
    def test__save__ignores_other_seats(self, markets_mock):
        """Does not delete purchases in other seats."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            seat = ext_models.Seat.objects.last(),
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)
    
    
    @patching.markets_open(True)
    def test__save__ignores_other_gender(self, markets_mock):
        """Does not delete purchases of the other gender."""
        
        other_crew = ext_models.Crew.objects.exclude(gender = self.crew.gender).first()
        
        models.Purchase(
            team = self.team,
            day = self.day,
            seat = self.seat,
            crew = other_crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        form = forms.Sell(
            {'seat': self.seat.id, 'gender': 'W'},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
        
        form.save()
        self.assertEqual(models.Purchase.objects.count(), 1)

