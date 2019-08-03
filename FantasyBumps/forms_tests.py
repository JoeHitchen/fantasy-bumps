from django.test import TestCase

from . import models
from . import forms
from . import patching


class Test__Buy(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    
    def setUp(self):
        self.team = models.Team.objects.first()
        self.day = models.Day.objects.first()
        self.crew = models.Crew.objects.first().id
        self.seat = models.Seat.objects.first().id
    
    
    def test__init__kwargs_stored(self):
        """Stores the 'team' and 'day' keyword arguments."""
        
        form = forms.Buy(team = self.team, day = self.day)
        self.assertEqual(form.team, self.team)
        self.assertEqual(form.day, self.day)
    
    
    @patching.market_is_open(True)
    def test__valid__markets_open(self, markets_mock):
        """Purchases allowed when markets are open."""
        
        form = forms.Buy(
            {'crew': self.crew, 'seat': self.seat},
            team = self.team,
            day = self.day,
        )
        self.assertTrue(form.is_valid())
    
    
    @patching.market_is_open(False)
    def test__valid__markets_closed(self, markets_mock):
        """Purchases allowed when markets are open."""
        
        day = models.Day.objects.first()
        
        form = forms.Buy(
            {'crew': self.crew, 'seat': self.seat},
            team = self.team,
            day = day,
        )
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors, {
            '__all__': ['Markets are not currently open.'],
        })
    
    
    @patching.market_is_open(True)
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

