from django.test import TestCase

from external.constants import genders

from . import models


class Test__Day(TestCase):
    fixtures = ['basic_event', 'start_orders']
    
    @classmethod
    def setUpTestData(self):
        
        self.event = models.Event.objects.first()
        self.event.womens_divisions = 3
        self.event.boats_per_division = 2
        self.event.save()
        
        self.day = models.Day.objects.first()
    
    
    def test__start_order__number_of_mens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.MENS)
        self.assertEqual(len(start_order), 2)
    
    
    def test__start_order__number_of_womens_divisions(self):
        """Creates the correct number of divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(len(start_order), 3)
    
    
    def test__start_order__number_of_boats(self):
        """Has the correct number of boats in each divisions."""
        
        start_order = self.day.start_order(genders.WOMENS)
        self.assertEqual(start_order[0].count(), 2)
        self.assertEqual(start_order[1].count(), 2)
        self.assertEqual(start_order[2].count(), 3)  # Extra boat in last division
    
    
    def test__start_order__womens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.WOMENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertTrue(genders.WOMENS in div_genders)
        self.assertFalse(genders.MENS in div_genders)
    
    
    def test__start_order__mens_divisions(self):
        """Only returns crews with the correct gender."""
        
        start_order = self.day.start_order(genders.MENS)
        
        div_genders = start_order[0].values_list('crew__gender', flat = True)
        self.assertFalse(genders.WOMENS in div_genders)
        self.assertTrue(genders.MENS in div_genders)

