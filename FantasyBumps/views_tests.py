from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import models as usr
from django.contrib import messages
from django.urls import reverse, resolve

from .constants import genders
from . import models
from . import utils
from . import views
from . import patching


class Test__Simple(TestCase):
    """Tests simple views that do not justify separate test classes."""
    fixtures = ['basic_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    def test__index(self):
        """Renders the index page."""
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')
    
    
    def test__event__unknown_event(self):
        """Returns 404 for unknown events."""
        
        url = reverse('fantasybumps:event', kwargs = {'event_tag': 'unknown'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    
    def test__event__known_event(self):
        """Returns 200 for known events, with the event in the context."""
        
        url = reverse('fantasybumps:event', kwargs = {'event_tag': self.event.tag})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/event.html')
        self.assertEqual(response.context['event'], self.event)
    
    
    def test__leaderboard__unknown_event(self):
        """Returns 404 for unknown events."""
        
        url = reverse('fantasybumps:leaderboard', kwargs = {'event_tag': 'unknown'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    
    def test__leaderboard__known_event(self):
        """Returns 200 for known events, with the event in the context."""
        
        url = reverse('fantasybumps:leaderboard', kwargs = {'event_tag': self.event.tag})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/leaderboard.html')
        self.assertEqual(response.context['event'], self.event)



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
    fixtures = ['seats', 'basic_event', 'start_orders']
    url_name = 'fantasybumps:men'
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.url = reverse(cls.url_name, kwargs = {'event_tag': cls.event.tag})
        
        cls.team = usr.User.objects.create_user('Market', '', 'secret')
        cls.day = cls.event.active_day
        
        cls.crew_mens = models.Crew(gender = genders.MENS)
        cls.crew_mens.save()
        
        cls.crew_womens = models.Crew(gender = genders.WOMENS)
        cls.crew_womens.save()
    
    
    def test__without_user(self):
        """Renders the market page for the men's competition."""
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Men')
        self.assertStartOrderEqual(
            response.context['start_order'],
            self.day.start_order(genders.MENS),
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
            self.day.start_order(genders.MENS),
        )
        
        self.assertTrue('crew' in response.context)
        self.assertTrue('crew_valid' in response.context)
        self.assertTrue('other_crew_valid' in response.context)
    
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew_mens,
            seat = models.Seat.objects.first(),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.MENS)
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
        
        for seat in models.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew_mens,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.MENS)
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
        
        for seat in models.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew_womens,
                seat = seat,
            ).save()
        
        other_crew = utils.get_crew(self.team, self.day, genders.WOMENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])



class Test__Market_Women(TestCase, StartOrdersMixin):
    fixtures = ['seats', 'basic_event', 'start_orders']
    url_name = 'fantasybumps:women'
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.url = reverse(cls.url_name, kwargs = {'event_tag': cls.event.tag})
        
        cls.team = usr.User.objects.create_user('Market', '', 'secret')
        cls.day = cls.event.active_day
        
        cls.crew_mens = models.Crew(gender = genders.MENS)
        cls.crew_mens.save()
        
        cls.crew_womens = models.Crew(gender = genders.WOMENS)
        cls.crew_womens.save()
    
    
    def test__without_user(self):
        """Renders the market page for the women's competition."""
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        
        self.assertEqual(response.context['gender'], 'Women')
        self.assertStartOrderEqual(
            response.context['start_order'],
            self.day.start_order(genders.WOMENS),
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
            self.day.start_order(genders.WOMENS),
        )
        
        self.assertTrue('crew' in response.context)
        self.assertTrue('crew_valid' in response.context)
        self.assertTrue('other_crew_valid' in response.context)
    
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        models.Purchase(
            team = self.team,
            day = self.day,
            crew = self.crew_womens,
            seat = models.Seat.objects.first(),
        ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
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
        
        for seat in models.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew_womens,
                seat = seat,
            ).save()
        
        crew = utils.get_crew(self.team, self.day, genders.WOMENS)
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
        
        for seat in models.Seat.objects.all():
            models.Purchase(
                team = self.team,
                day = self.day,
                crew = self.crew_mens,
                seat = seat,
            ).save()
        
        other_crew = utils.get_crew(self.team, self.day, genders.MENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='Market', password='secret')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])



class MessagesMixin:
    
    def check_messages(self, msgs, expected):
        """Tests that the expected messages are sent to the client."""
        
        def convert_level(level):
            return messages.__dict__.get(level.upper())
        
        self.assertEqual(len(msgs), len(expected))
        
        for i, msg in enumerate(msgs):
            with self.subTest(index = i):
                
                self.assertEqual(
                    msg.level,
                    convert_level(expected[i]['level']),
                )
                self.assertEqual(
                    msg.message,
                    expected[i]['message'],
                )



class Test__Buy__Integration(TestCase, MessagesMixin):
    fixtures = ['seats', 'basic_event', 'start_orders']
    url = reverse('fantasybumps:buy')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Buy', '', 'secret')
        
        cls.crew = models.Crew(name = 'A', gender = genders.MENS)
        cls.crew.save()
        
        cls.seat = models.Seat.objects.get(name = 'Stroke')
    
    
    def test__no_login(self):
        """Requires a log in."""
        
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__get(self):
        """Renders the form page for GET requests."""
        
        self.client.login(username='Buy', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    def test__invalid_post(self):
        """Renders the form page for invalid POST requests."""
        
        self.client.login(username='Buy', password='secret')
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__valid_post(self, market_closes_mock, markets_mock):
        """Creates the object and redirects to the relevant market page."""
        
        self.assertEqual(models.Purchase.objects.count(), 0)
        
        self.client.login(username='Buy', password='secret')
        response = self.client.post(
            self.url,
            {'crew': str(self.crew.id), 'seat': str(self.seat.id)},
            follow = True,
        )
        
        self.assertRedirects(response, reverse('fantasybumps:men'))
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        self.check_messages(
            response.context['messages'],
            [{'level': 'success', 'message': 'Successfully added A to your crew at stroke.'}],
        )


        
class Test__Buy__Unit(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """N.B. Saving objects not necessary since no database lookups performed."""
        cls.crew = models.Crew(name = 'Hertford W1', gender = genders.WOMENS)
        
        cls.stroke = models.Seat(name = 'Stroke', cox = False)
        cls.cox = models.Seat(name = 'Cox', cox = True)
    
    
    def test__get_success_url__men(self):
        """Returns a redirect to the relevant market place."""
        
        mens_crew = models.Crew(name = 'Hertford M1', gender = genders.MENS)
        
        view = views.BuyView()
        view.form_save_out = models.Purchase(crew = mens_crew)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'men')
    
    
    def test__get_success_url__women(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.BuyView()
        view.form_save_out = models.Purchase(crew = self.crew)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'women')
    
    
    def test__get_success_message__rower(self):
        """Generates a success message including the team and seat."""
        
        msg = views.BuyView().get_success_message({
            'crew': self.crew,
            'seat': self.stroke,
        })
        self.assertEqual(msg, 'Successfully added Hertford W1 to your crew at stroke.')
    
    
    def test__get_success_message__cox(self):
        """Presents a slightly different seat description for coxes."""
        
        msg = views.BuyView().get_success_message({
            'crew': self.crew,
            'seat': self.cox,
        })
        self.assertNotIn('at cox.', msg)
        self.assertIn('as the cox.', msg)



class Test__Sell__Integration(TestCase, MessagesMixin):
    fixtures = ['seats', 'basic_event', 'start_orders']
    url = reverse('fantasybumps:sell')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = usr.User.objects.create_user('Sell', '', 'secret')
        cls.day = models.Day.objects.first()
        
        cls.crew = models.Crew(name = 'A', gender = genders.MENS)
        cls.crew.save()
        
        cls.seat = models.Seat.objects.get(name = 'Stroke')
    
    
    def test__no_login(self):
        """Requires a log in."""
        
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__get(self):
        """Renders the form page for GET requests."""
        
        self.client.login(username='Sell', password='secret')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    def test__invalid_post(self):
        """Renders the form page for invalid POST requests."""
        
        self.client.login(username='Sell', password='secret')
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__valid_post(self, market_closes_mock, markets_mock):
        """Deletes the object and redirects to the relevant market page."""
        
        models.Purchase(
            team = self.team,
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        ).save()
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        self.client.login(username='Sell', password='secret')
        response = self.client.post(
            self.url,
            {'seat': str(self.seat.id), 'gender': 'M'},
            follow = True,
        )
        
        self.assertRedirects(response, reverse('fantasybumps:men'))
        self.assertEqual(models.Purchase.objects.count(), 0)
        
        self.check_messages(
            response.context['messages'],
            [{'level': 'success', 'message': 'Successfully sold your stroke seat.'}],
        )



class Test__Sell__Unit(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """N.B. Saving objects not necessary since no database lookups performed."""
        
        cls.stroke = models.Seat(name = 'Stroke', cox = False)
        cls.cox = models.Seat(name = 'Cox', cox = True)
    
    
    def test__get_success_url__men(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.SellView()
        view.form_save_out = genders.MENS
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'men')
    
    
    def test__get_success_url__women(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.SellView()
        view.form_save_out = genders.WOMENS
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'women')
    
    
    def test__get_success_message__rower(self):
        """Generates a success message including the team and seat."""
        
        msg = views.SellView().get_success_message({'seat': self.stroke})
        self.assertEqual(msg, 'Successfully sold your stroke seat.')
    
    
    def test__get_success_message__cox(self):
        """Presents a slightly different seat description for coxes."""
        
        msg = views.SellView().get_success_message({'seat': self.cox})
        self.assertNotIn('your cox seat.', msg)
        self.assertIn('your cox.', msg)

