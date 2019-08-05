from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase, tag
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import models as auth
from django.urls import reverse, resolve

from .constants import genders
from . import models
from . import utils
from . import views
from . import transactions
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
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        cls.team_1 = auth.User.objects.create_user('One', '', '').team
        cls.team_2 = auth.User.objects.create_user('Two', '', '').team
        cls.team_3 = auth.User.objects.create_user('Three', '', '').team
        
        cls.game_entry_1 = cls.event.fantasies.create(
            team = cls.team_1,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 110,
            womens_balance = 103,
        )
        cls.game_entry_2 = cls.event.fantasies.create(
            team = cls.team_2,
            mens_budget = 754,
            womens_budget = 456,
            mens_balance = 120,
            womens_balance = 105,
        )
        cls.game_entry_3 = cls.event.fantasies.create(
            team = cls.team_3,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 117,
            womens_balance = 112,
        )
    
    def extra_context_without_user(self, context):
        """Extra context tests for without_user base test."""
        
        self.assertEqual(context['genders'], genders)
        self.assertEqual(context['ranking'], self.ranking)
        self.assertEqual(list(context['fantasies']), self.get_ranked_fantasies())
    
    
    def extra_context_with_user(self, context):
        """Extra context tests for with_user base test."""
        
        self.assertEqual(context['genders'], genders)
        self.assertEqual(context['ranking'], self.ranking)
        self.assertEqual(list(context['fantasies']), self.get_ranked_fantasies())



class Test__Leaderboard_Main(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard'
    ranking = genders.TOTALS
    
    def get_ranked_fantasies(self):
        return [self.game_entry_1, self.game_entry_3, self.game_entry_2]



class Test__Leaderboard_Men(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard_men'
    ranking = genders.MENS
    
    def get_ranked_fantasies(self):
        return [self.game_entry_2, self.game_entry_1, self.game_entry_3]



class Test__Leaderboard_Women(LeaderboardPageBase, TestCase):
    
    # Test settings
    url_name = 'fantasybumps:leaderboard_women'
    ranking = genders.WOMENS
    
    def get_ranked_fantasies(self):
        return [self.game_entry_1, self.game_entry_3, self.game_entry_2]



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
    url = reverse('fantasybumps:oldbuy')
    
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
        
        view = views.OldBuyView()
        view.form_save_out = models.Purchase(crew = mens_crew)
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'men')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
    def test__get_success_url__women(self):
        """Returns a redirect to the relevant market place."""
        
        view = views.OldBuyView()
        view.form_save_out = models.Purchase(crew = self.crew)
        view.event = models.Event(tag = self.event_tag)
        url = view.get_success_url()
        
        resolved = resolve(url)
        self.assertEqual(resolved.namespaces, ['fantasybumps'])
        self.assertEqual(resolved.url_name, 'women')
        self.assertEqual(resolved.kwargs['event_tag'], self.event_tag)
    
    
    def test__get_success_message__rower(self):
        """Generates a success message including the team and seat."""
        
        msg = views.OldBuyView().get_success_message({
            'crew': self.crew,
            'seat': self.stroke,
        })
        self.assertEqual(msg, 'Successfully added Hertford W1 to your crew at stroke.')
    
    
    def test__get_success_message__cox(self):
        """Presents a slightly different seat description for coxes."""
        
        msg = views.OldBuyView().get_success_message({
            'crew': self.crew,
            'seat': self.cox,
        })
        self.assertNotIn('at cox.', msg)
        self.assertIn('as the cox.', msg)



class Test__Sell(TestCase, MessagesMixin):
    """Testing of transaction behaviour (including side effects) is delegated to the relevant
    subroutine."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    url = reverse('fantasybumps:sell')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.first()
        cls.seat = models.Seat.objects.first()
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
        
        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )
        cls.crew.positions.create(day = cls.day, rank = 1)
    
    
    def test__deny_get(self):
        """Rejects non-POST requests."""
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
    
    
    def test__no_login(self):
        """Redirects non-logged in users."""
        
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__no_data(self):
        """Denies request if no purchase number is supplied.
        
        Redirects to fantasy root and raises error to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'error', 'message': 'You are not authorised to conduct this sale.'}],
        )
    
    
    def test__unknown_purchase(self):
        """Denies request if the purchase does not exist.
        
        Redirects to fantasy root and raises error to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url, {'purchase': 100000})
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'error', 'message': 'You are not authorised to conduct this sale.'}],
        )
    
    
    def test__other_team(self):
        """Denies request if the purchase does not belong to the user.
        
        Redirects to fantasy root and raises error to user.
        """
        
        auth.User.objects.create_user('Other', '', 'pw')
        self.client.login(username = 'Other', password = 'pw')
        
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'error', 'message': 'You are not authorised to conduct this sale.'}],
        )
    
    
    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock):
        """Denies request if market not open for purchase's day.
        
        Redirects to relevant market page and raises warning to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        
        self.assertRedirects(
            response,
            reverse(
                'fantasybumps:women',
                kwargs = {'event_tag': self.day.event.tag},
            ),
        )
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Markets are not open for this sale.'}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    @patch.object(transactions, 'sell')
    def test__transaction_error(self, transaction_mock, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Redirects to relevant market page and raises error to user.
        """
        
        transaction_mock.side_effect = AssertionError()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        
        self.assertRedirects(
            response,
            reverse(
                'fantasybumps:women',
                kwargs = {'event_tag': self.day.event.tag},
            ),
        )
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'error', 'message': 'An unknown error occurred processing this sale.'}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_womens(self, market_closes_mock, markets_mock):
        """Completes the sale.
        
        Redirects to relevant market page and raises success to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        
        self.assertRedirects(
            response,
            reverse(
                'fantasybumps:women',
                kwargs = {'event_tag': self.day.event.tag},
            ),
        )
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'success', 'message': "Successfully sold your women's bow seat."}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_mens(self, market_closes_mock, markets_mock):
        """Completes the sale.
        
        Redirects to relevant market page and raises success to user.
        """
        self.skipTest('See issue #4.')
        
        mens_crew = models.Crew.objects.filter(gender = genders.MENS).first()
        purchase_men = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = mens_crew,
        )
        mens_crew.positions.create(day = self.day, rank = 1)
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': purchase_men.id})
        
        self.assertRedirects(
            response,
            reverse(
                'fantasybumps:men',
                kwargs = {'event_tag': self.day.event.tag},
            ),
        )
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'success', 'message': "Successfully sold your men's bow seat."}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_cox(self, market_closes_mock, markets_mock):
        """Completes the sale.
        
        Redirects to relevant market page and raises success to user.
        """
        
        coxing_purchase = self.team.purchases.create(
            day = self.day,
            seat = models.Seat.objects.get(cox = True),
            crew = self.crew,
        )
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': coxing_purchase.id})
        
        self.assertRedirects(
            response,
            reverse(
                'fantasybumps:women',
                kwargs = {'event_tag': self.day.event.tag},
            ),
        )
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'success', 'message': "Successfully sold your women's cox."}],
        )
    
    
    @tag('query-count')
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__query_count(self, market_closes_mock, markets_mock):
        """ Expect:
            (2) Django internals
            (1) SELECT user's team
            (1) SELECT purchase, crew, team, user, day, event
            (1) SELECT crew's position that day
            (2) Transaction overhead
            (1) Sell action queries
        """
        
        models.Crew.value.cache_clear()
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        with self.assertNumQueries(9):
            self.client.post(self.url, {'purchase': self.purchase.id})

