from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse, resolve

from .constants import genders
from . import models
from . import utils
from . import views
from . import patching


class Test__Index(TestCase):
    """Tests simple views that do not justify separate test classes."""
    fixtures = ['dev_event', 'dev_team']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.team = models.Team.objects.first()
    
    
    def test__index(self):
        """Renders the index page."""
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')
        self.assertEqual(
            list(response.context['events']),
            list(models.Event.objects.all()),
        )



class GamePageBase():
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'dev_start_day3',
        'seats',
        'dev_team',
    ]
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.team = models.Team.objects.first()
        cls.day = cls.event.active_day
        
        cls.url = reverse(cls.url_name, kwargs = {'event_tag': cls.event.tag})
        
        cls.crew_mens = models.Crew.objects.create(gender = genders.MENS)
        cls.crew_womens = models.Crew.objects.create(gender = genders.WOMENS)
    
    
    def test__generic__unknown_event(self):
        """Returns a 404 response if the event tag is not recognised."""
        
        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': 'unknown'},
        ))
        self.assertEqual(response.status_code, 404)
    
    
    def test__generic__without_user(self):
        """Returns a 200 success, with the event and day in the context but no team."""
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)
        
        self.assertEqual(response.context['event'], self.event)
        self.assertEqual(response.context['day'], self.day)
        self.assertFalse('team' in response.context)
        
        self.extra_context_without_user(response.context)
    
    def extra_context_without_user(self, context):
        """Extra context tests for without_user base test."""
        pass
    
    
    def test__generic__with_user(self):
        """Returns a 200 success, with the event, day, and team in the context."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)
        
        self.assertEqual(response.context['event'], self.event)
        self.assertEqual(response.context['day'], self.day)
        self.assertEqual(response.context['team'], self.team)
        
        self.extra_context_with_user(response.context)
    
    def extra_context_with_user(self, context):
        """Extra context tests for with_user base test."""
        pass



class Test__Event(GamePageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:event'
    template = 'fantasybumps/event.html'



class MarketPageBase(GamePageBase):
    
    # Test group settings
    template = 'fantasybumps/market.html'
    
    def extra_context_without_user(self, context):
        """Extra context tests for without_user base test."""
        
        self.assertEqual(context['gender'], self.gender_info['text'])
        self.assertEqual(
            context['start_order'],
            self.day.start_order(self.gender_info['code']),
        )
        
        self.assertFalse('crew' in context)
        self.assertFalse('crew_valid' in context)
        self.assertFalse('other_crew_valid' in context)
    
    
    def extra_context_with_user(self, context):
        """Extra context tests for with_user base test."""
        
        self.assertEqual(context['gender'], self.gender_info['text'])
        self.assertEqual(
            context['start_order'],
            self.day.start_order(self.gender_info['code']),
        )
        
        self.assertTrue('crew' in context)
        self.assertTrue('crew_valid' in context)
        self.assertTrue('other_crew_valid' in context)



class Test__Market_Men(MarketPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:men'
    gender_info = {
        'text': 'Men',
        'code': genders.MENS,
    }
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew_mens,
            seat = models.Seat.objects.first(),
        )
        
        crew = self.team.get_crew(self.day, genders.MENS)
        self.assertFalse(utils.has_all_seats(crew))
        
        self.client.login(username='DevTeam', password='password')
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
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_mens,
                seat = seat,
            )
        
        crew = self.team.get_crew(self.day, genders.MENS)
        self.assertTrue(utils.has_all_seats(crew))
        
        self.client.login(username='DevTeam', password='password')
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
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_womens,
                seat = seat,
            )
        
        other_crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])



class Test__Market_Women(MarketPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:women'
    gender_info = {
        'text': 'Women',
        'code': genders.WOMENS,
    }
    
    def test__partial_crew(self):
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """
        
        self.team.purchases.create(
            day = self.day,
            crew = self.crew_womens,
            seat = models.Seat.objects.first(),
        )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertFalse(utils.has_all_seats(crew))
        
        self.client.login(username='DevTeam', password='password')
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
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_womens,
                seat = seat,
            )
        
        crew = self.team.get_crew(self.day, genders.WOMENS)
        self.assertTrue(utils.has_all_seats(crew))
        
        self.client.login(username='DevTeam', password='password')
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
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_mens,
                seat = seat,
            )
        
        other_crew = self.team.get_crew(self.day, genders.MENS)
        self.assertTrue(utils.has_all_seats(other_crew))
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])



class LeaderboardPageBase(GamePageBase):
    
    # Test group settings
    template = 'fantasybumps/leaderboard.html'
    
    def extra_context_without_user(self, context):
        """Extra context tests for without_user base test."""
        
        self.assertEqual(context['ranking'], self.view_info['ranking'])
    
    
    def extra_context_with_user(self, context):
        """Extra context tests for with_user base test."""
        
        self.assertEqual(context['ranking'], self.view_info['ranking'])



class Test__Leaderboard_Main(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard'
    view_info = {
        'ranking': 'T',
    }



class Test__Leaderboard_Men(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard_men'
    view_info = {
        'ranking': genders.MENS,
    }



class Test__Leaderboard_Women(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard_women'
    view_info = {
        'ranking': genders.WOMENS,
    }



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
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'dev_start_day3',
        'seats',
        'dev_team',
    ]
    url = reverse('fantasybumps:buy')
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.day = cls.event.active_day
        
        cls.team = models.Team.objects.first()
        
        cls.crew = models.Crew(name = 'A', gender = genders.MENS)
        cls.crew.save()
        
        cls.seat = models.Seat.objects.get(name = 'Stroke')
    
    
    def test__no_login(self):
        """Requires a log in."""
        
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__get(self):
        """Renders the form page for GET requests."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    def test__invalid_post(self):
        """Renders the form page for invalid POST requests."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__valid_post(self, market_closes_mock, markets_mock):
        """Creates the object and redirects to the relevant market page."""
        
        self.assertEqual(models.Purchase.objects.count(), 0)
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.post(
            self.url,
            {'crew': str(self.crew.id), 'seat': str(self.seat.id)},
            follow = True,
        )
        
        self.assertRedirects(
            response,
            reverse('fantasybumps:men', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        self.check_messages(
            response.context['messages'],
            [{'level': 'success', 'message': 'Successfully added A to your crew at stroke.'}],
        )


        
class Test__Buy__Unit(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """N.B. Saving objects not necessary since no database lookups performed."""
        cls.event_tag = 'testevent'
        cls.crew = models.Crew(name = 'Hertford W1', gender = genders.WOMENS)
        
        cls.stroke = models.Seat(name = 'Stroke', cox = False)
        cls.cox = models.Seat(name = 'Cox', cox = True)
    
    
    def test__get_success_url__men(self):
        """Returns a redirect to the relevant market place."""
        
        mens_crew = models.Crew(name = 'Hertford M1', gender = genders.MENS)
        
        view = views.BuyView()
        view.form_save_out = models.Purchase(crew = mens_crew)
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'men')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
    def test__get_success_url__women(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.BuyView()
        view.form_save_out = models.Purchase(crew = self.crew)
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'women')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
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
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'dev_start_day3',
        'seats',
        'dev_team',
    ]
    url = reverse('fantasybumps:sell')
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.day = cls.event.active_day
        
        cls.team = models.Team.objects.first()
        
        cls.crew = models.Crew(name = 'A', gender = genders.MENS)
        cls.crew.save()
        
        cls.seat = models.Seat.objects.get(name = 'Stroke')
    
    
    def test__no_login(self):
        """Requires a log in."""
        
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__get(self):
        """Renders the form page for GET requests."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    def test__invalid_post(self):
        """Renders the form page for invalid POST requests."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/form.html')
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__valid_post(self, market_closes_mock, markets_mock):
        """Deletes the object and redirects to the relevant market page."""
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        )
        self.assertEqual(models.Purchase.objects.count(), 1)
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.post(
            self.url,
            {'seat': str(self.seat.id), 'gender': 'M'},
            follow = True,
        )
        
        self.assertRedirects(
            response,
            reverse('fantasybumps:men', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertEqual(models.Purchase.objects.count(), 0)
        
        self.check_messages(
            response.context['messages'],
            [{'level': 'success', 'message': 'Successfully sold your stroke seat.'}],
        )



class Test__Sell__Unit(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """N.B. Saving objects not necessary since no database lookups performed."""
        cls.event_tag = 'testevent'
        
        cls.stroke = models.Seat(name = 'Stroke', cox = False)
        cls.cox = models.Seat(name = 'Cox', cox = True)
    
    
    def test__get_success_url__men(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.SellView()
        view.form_save_out = genders.MENS
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'men')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
    def test__get_success_url__women(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.SellView()
        view.form_save_out = genders.WOMENS
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'women')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
    def test__get_success_message__rower(self):
        """Generates a success message including the team and seat."""
        
        msg = views.SellView().get_success_message({'seat': self.stroke})
        self.assertEqual(msg, 'Successfully sold your stroke seat.')
    
    
    def test__get_success_message__cox(self):
        """Presents a slightly different seat description for coxes."""
        
        msg = views.SellView().get_success_message({'seat': self.cox})
        self.assertNotIn('your cox seat.', msg)
        self.assertIn('your cox.', msg)

