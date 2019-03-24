from django.test import TestCase
from django.contrib.auth import models as usr
from django.urls import reverse

from external import models as ext_models
from external import utils as ext_utils
from external.constants import genders

from . import models
from . import utils


class Test__Index(TestCase):
    
    def test__index(self):
        """Renders the index page."""
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')



class StartOrdersMixin:
    
    def assertStartOrderEqual(self, received, expected):
        """Checks that two start orders are the same."""
        
        self.assertEqual(len(received), len(expected))
        for i, division in enumerate(expected):
            with self.subTest(index = i):
                self.assertEqual(
                    list(received[i]),
                    list(division),
                )



class Test__Market_Men(TestCase, StartOrdersMixin):
    fixtures = ['seats', 'start_orders']
    url = reverse('fantasybumps:men')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Market', '', 'secret')
        
        cls.crew_mens = ext_models.Crew(gender = genders.MENS)
        cls.crew_mens.save()
        
        cls.crew_womens = ext_models.Crew(gender = genders.WOMENS)
        cls.crew_womens.save()
    
    
    def test__without_user(self):
        """Renders the market page for the men's competition."""
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Men')
        self.assertStartOrderEqual(
            response.context['start_order'],
            ext_utils.get_start_order(genders.MENS),
        )
        
        self.assertFalse('crew' in response.context)
        self.assertFalse('crew_valid' in response.context)
        self.assertFalse('other_crew_valid' in response.context)
    
    
    def test__with_user(self):
        """Renders the market page with details of the user's team."""
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Men')
        self.assertStartOrderEqual(
            response.context['start_order'],
            ext_utils.get_start_order(genders.MENS),
        )
        
        self.assertTrue('crew' in response.context)
        self.assertTrue('crew_valid' in response.context)
        self.assertTrue('other_crew_valid' in response.context)
    
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        models.Rower(
            team = self.team,
            crew = self.crew_mens,
            seat = ext_models.Seat.objects.first(),
        ).save()
        
        crew = utils.get_crew(self.team, genders.MENS)
        self.assertFalse(utils.has_all_seats(crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertFalse(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])
    
    
    def test__crew_valid(self):
        """
        Sets a flag if the user's team is valid.
        Does not test response or default context.
        """
        
        for seat in ext_models.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew_mens,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, genders.MENS)
        self.assertTrue(utils.has_all_seats(crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertTrue(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])
    
    
    def test__other_crew_valid(self):
        """
        Sets a flag if the user's other-gendered team is valid.
        Does not test response or default context.
        """
        
        for seat in ext_models.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew_womens,
                seat = seat,
            ).save()
        
        other_crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])



class Test__Market_Women(TestCase, StartOrdersMixin):
    fixtures = ['seats', 'start_orders']
    url = reverse('fantasybumps:women')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Market', '', 'secret')
        
        cls.crew_mens = ext_models.Crew(gender = genders.MENS)
        cls.crew_mens.save()
        
        cls.crew_womens = ext_models.Crew(gender = genders.WOMENS)
        cls.crew_womens.save()
    
    
    def test__without_user(self):
        """Renders the market page for the women's competition."""
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        
        self.assertEqual(response.context['gender'], 'Women')
        self.assertStartOrderEqual(
            response.context['start_order'],
            ext_utils.get_start_order(genders.WOMENS),
        )
        
        self.assertFalse('crew' in response.context)
        self.assertFalse('crew_valid' in response.context)
        self.assertFalse('other_crew_valid' in response.context)
    
    
    def test__with_user(self):
        """Adds additional context about logged-in user's crews."""
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Women')
        self.assertStartOrderEqual(
            response.context['start_order'],
            ext_utils.get_start_order(genders.WOMENS),
        )
        
        self.assertTrue('crew' in response.context)
        self.assertTrue('crew_valid' in response.context)
        self.assertTrue('other_crew_valid' in response.context)
    
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        models.Rower(
            team = self.team,
            crew = self.crew_womens,
            seat = ext_models.Seat.objects.first(),
        ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertFalse(utils.has_all_seats(crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertFalse(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])
    
    
    def test__crew_valid(self):
        """
        Sets a flag if the user's team is valid.
        Does not test response or default context.
        """
        
        for seat in ext_models.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew_womens,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, genders.WOMENS)
        self.assertTrue(utils.has_all_seats(crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertTrue(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])
    
    
    def test__other_crew_valid(self):
        """
        Sets a flag if the user's other-gendered team is valid.
        Does not test response or default context.
        """
        
        for seat in ext_models.Seat.objects.all():
            models.Rower(
                team = self.team,
                crew = self.crew_mens,
                seat = seat,
            ).save()
        
        other_crew = utils.get_crew(self.team, genders.MENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])

