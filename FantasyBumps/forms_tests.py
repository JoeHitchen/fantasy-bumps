from django.test import TestCase
from django.contrib.auth import models as usr

from external import models as ext_models

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
        rower = form.save(self.team)
        self.assertEqual(rower.team, self.team)

