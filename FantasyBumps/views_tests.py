from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase, tag
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import models as auth
from django.urls import reverse

from .constants import genders
from . import models
from . import utils
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
        
        cls.crew_mens = models.Crew.objects.filter(gender = genders.MENS).first()
        cls.crew_womens = models.Crew.objects.filter(gender = genders.WOMENS).first()
    
    
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
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.team.entries.create(event = cls.event)
    
    
    def assertStartOrdersEqual(self, received, expected):
        """A helper method to compare if two start orders are equal."""
        
        self.assertEqual(len(received), len(expected))
        
        for index in range(0, len(expected)):
            with self.subTest(division_index = index):
                
                self.assertQuerysetEqual(
                    received[index],
                    expected[index],
                    transform = lambda item: item,
                )
    
    
    def extra_context_without_user(self, context):
        """Extra context tests for without_user base test."""
        
        self.assertEqual(context['gender'], self.gender_info['text'])
        self.assertEqual(context['gender_code'], self.gender_info['code'])
        self.assertStartOrdersEqual(
            context['start_order'],
            self.day.start_order(self.gender_info['code']),
        )
        
        self.assertFalse('crew' in context)
        self.assertFalse('crew_valid' in context)
        self.assertFalse('other_crew_valid' in context)
        
        self.assertFalse(context['show_actions'])
    
    
    def extra_context_with_user(self, context):
        """Extra context tests for with_user base test.
        
        Cannot test show_actions here, since it depends on market status.
        """
        
        self.assertEqual(context['gender'], self.gender_info['text'])
        self.assertEqual(context['gender_code'], self.gender_info['code'])
        self.assertStartOrdersEqual(
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
        self.assertFalse(utils.has_all_seats(crew, models.Seat.objects.all()))
        
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
        self.assertTrue(utils.has_all_seats(crew, models.Seat.objects.all()))
        
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
        self.assertTrue(utils.has_all_seats(other_crew, models.Seat.objects.all()))
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))
    def test__market_open(self, market_closes_mock, markets_mock):
        """'show_actions' reflects market status for logged in users.
        Does not test response or default context.
        """
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertTrue(response.context['show_actions'])
    
    
    @patching.market_is_open(False)
    def test__market_closed(self, markets_mock):
        """'show_actions' reflects market status for logged in users.
        Does not test response or default context.
        """
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        
        self.assertFalse(response.context['show_actions'])



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
        self.assertFalse(utils.has_all_seats(crew, models.Seat.objects.all()))
        
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
        self.assertTrue(utils.has_all_seats(crew, models.Seat.objects.all()))
        
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
        self.assertTrue(utils.has_all_seats(other_crew, models.Seat.objects.all()))
        
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
    
    
    @tag('query-count')
    def test__query_count__without_login(self):
        """ Expect:
            (3) FantasyBumps Overhead - Event (1), Active day (2, but can be 1)
            (1) Get rankings
        """
        
        with self.assertNumQueries(4):
            self.client.get(self.url)
    
    
    @tag('query-count')
    def test__query_count__with_login(self):
        """ Expect:
            (4) Base queries
            (2) Django Auth overheard
            (1) Get user's team
        """
        
        self.client.login(username='DevTeam', password='password')
        
        with self.assertNumQueries(7):
            self.client.get(self.url)



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



class Test__Team(TestCase):
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_team',
    ]

    # Test settings
    url_name = 'fantasybumps:team'
    
    
    @classmethod
    def setUpTestData(cls):
        
        cls.event = models.Event.objects.first()
        cls.user_team = models.Team.objects.select_related().first()
        cls.day = cls.event.active_day
        
        cls.view_team = auth.User.objects.create_user('Target', '', '').team
        cls.budgets = cls.view_team.entries.create(event = cls.event)
        
        cls.url = reverse(
            cls.url_name,
            kwargs = {'event_tag': cls.event.tag, 'team_name': cls.view_team},
        )
    
    
    def test__unknown_event(self):
        """Returns a 404 response if the event tag is not recognised."""
        
        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': 'Unknown', 'team_name': self.view_team},
        ))
        self.assertEqual(response.status_code, 404)
    
    
    def test__unknown_team(self):
        """Returns a 404 response if the team not recognised."""
        
        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': self.event.tag, 'team_name': 'Unknown'},
        ))
        self.assertEqual(response.status_code, 404)
    
    
    def test__not_entered(self):
        """Returns a 404 response if the team has no entry for the event."""
        
        self.budgets.delete()
        
        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': self.event.tag, 'team_name': self.view_team},
        ))
        self.assertEqual(response.status_code, 404)
    
    
    @patching.team_get_crew
    def test__without_login(self, get_crew_mock):
        """Generates a context containing the selected team, their financials, and their crews."""
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['team'], self.view_team)
        self.assertEqual(response.context['finances'], self.budgets)
        
        self.assertEqual(
            response.context['mens_crew'],
            (self.view_team, self.day, genders.MENS),
        )
        self.assertEqual(
            response.context['womens_crew'],
            (self.view_team, self.day, genders.WOMENS),
        )
    
    
    @patching.team_get_crew
    def test__with_login(self, get_crew_mock):
        """Does not replace the requested team with the viewer's own team."""
        
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['team'], self.view_team)
        self.assertEqual(response.context['finances'], self.budgets)
        
        self.assertEqual(
            response.context['mens_crew'],
            (self.view_team, self.day, genders.MENS),
        )
        self.assertEqual(
            response.context['womens_crew'],
            (self.view_team, self.day, genders.WOMENS),
        )
    
    
    @tag('query-count')
    def test__query_count(self):
        """ Expect:
            (3) SELECT event and active day
            (1) SELECT team to view
            (2) SELECT all seats (twice, once for each crew list)
            (2) SELECT purchases for crew lists (one for each crew lists)
        """
        
        with self.assertNumQueries(8):
            response = self.client.get(self.url)
            
            # Needed to force crew list queries
            list(response.context['mens_crew'])
            list(response.context['womens_crew'])



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



class Test__Buy(TestCase, MessagesMixin):
    """Testing of transaction behaviour (including side effects) is delegated to the relevant
    subroutine."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    url = reverse('fantasybumps:buy')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.crew = models.Crew.objects.first()
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
        
        cls.womens_url = reverse('fantasybumps:women', kwargs = {'event_tag': cls.day.event.tag})
    
    
    def setUp(self):
        models.Crew.value.cache_clear()
        self.budgets.refresh_from_db()
    
    
    def test__deny_get(self):
        """Rejects non-POST requests."""
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
    
    
    def test__no_login(self):
        """Redirects non-logged in users."""
        
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))
    
    
    def test__missing_day(self):
        """Denies request - Redirects to fantasy root and raises error to user."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'crew': self.crew.id})
        
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'error',
                'message': 'An error occurred processing the request data.',
            }],
        )

    
    def test__unknown_day(self):
        """Denies request - Redirects to fantasy root and raises error to user."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': 10000, 'crew': self.crew.id})
        
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'error',
                'message': 'An error occurred processing the request data.',
            }],
        )
    
    
    def test__missing_crew(self):
        """Denies request - Redirects to fantasy root and raises error to user."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id})
        
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'error',
                'message': 'An error occurred processing the request data.',
            }],
        )

    
    def test__unknown_crew(self):
        """Denies request - Redirects to fantasy root and raises error to user."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': 10000})
        
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'error',
                'message': 'An error occurred processing the request data.',
            }],
        )
    
    
    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock):
        """Denies request if market not open for intended day.
        
        Redirects to relevant market page and raises warning to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Markets are not open for this sale.'}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__not_racing(self, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Redirects to relevant market page and raises warning to user.
        """
        
        self.crew.positions.filter(day = self.day).delete()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'warning',
                'message': 'Cannot buy a crew on a day they are not racing.',
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__insufficient_funds(self, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Redirects to relevant market page and raises warning to user.
        """
        
        self.budgets.womens_balance = 0
        self.budgets.save()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'warning',
                'message': 'You do not have sufficient funds to make this purchase.',
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_womens(self, market_closes_mock, markets_mock):
        """Completes the purchase.
        
        Redirects to relevant market page and raises success to user.
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'success',
                'message': "Successfully bought Oriel W1 as your women's bow seat.",
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_mens(self, market_closes_mock, markets_mock):
        """Completes the purchase.
        
        Redirects to relevant market page and raises success to user.
        """
        
        mens_crew = models.Crew.objects.filter(gender = genders.MENS).first()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': mens_crew.id})
        
        mens_url = reverse('fantasybumps:men', kwargs = {'event_tag': self.day.event.tag})
        self.assertRedirects(response, mens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'success',
                'message': "Successfully bought Oriel M1 as your men's bow seat.",
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__valid_cox(self, market_closes_mock, markets_mock):
        """Completes the purchase.
        
        Redirects to relevant market page and raises success to user.
        """
        
        for seat in models.Seat.objects.exclude(cox = True):
            self.team.purchases.create(day = self.day, seat = seat, crew = self.crew)
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'success',
                'message': "Successfully bought Oriel W1 as your women's cox.",
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__all_seats_filled(self, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Redirects to relevant market page and raises warning to user.
        """
        
        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, seat = seat, crew = self.crew)
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'warning',
                'message': "You have already filled your women's crew.",
            }],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__budgets_missing(self, market_closes_mock, markets_mock):
        """Completes the purchase as normal, creating the missing budgets."""
        
        self.budgets.delete()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{
                'level': 'success',
                'message': "Successfully bought Oriel W1 as your women's bow seat.",
            }],
        )
    
    
    @tag('query-count')
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__query_count__standard(self, market_closes_mock, markets_mock):
        """ Expect:
            (2) Django internals
            (1) SELECT day, event
            (1) SELECT crew
            (1) SELECT user's team
            (1) SELECT seat - 'filled_seats' not evaluated separately
            (1) SELECT athlete
            (2) Transaction overhead
            (2) Buy action - Get crew's value (Affected by caching)
            (5) Buy action - Other queries
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        with self.assertNumQueries(16):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
    
    
    @tag('query-count')
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__query_count__without_budgets(self, market_closes_mock, markets_mock):
        """ Expect:
            (16) Queried as standard
            (3) Extra action queries
        """
        
        self.budgets.delete()
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        with self.assertNumQueries(19):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
    
    
    @tag('query-count')
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__query_count__with_athlete(self, market_closes_mock, markets_mock):
        """ Expect:
            (16) Queried as standard
        """
        
        for seat in models.Seat.objects.all():
            self.crew.crew_lists.create(event = self.day.event, seat = seat, name = 'Test Athlete')
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        with self.assertNumQueries(16):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})



class Test__Sell(TestCase, MessagesMixin):
    """Testing of transaction behaviour (including side effects) is delegated to the relevant
    subroutine."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    url = reverse('fantasybumps:sell')
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.crew = models.Crew.objects.first()
        cls.seat = models.Seat.objects.first()
        
        cls.budgets = cls.team.entries.create(event = cls.day.event)
        
        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )
        
        cls.womens_url = reverse('fantasybumps:women', kwargs = {'event_tag': cls.day.event.tag})
    
    
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
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Markets are not open for this sale.'}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    @patch.object(transactions, 'sell')
    def test__race_condition(self, transaction_mock, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Occurs when another thread deletes the purchase after it has been retrieved.
        Redirects to relevant market page and raises error to user.
        """
        
        transaction_mock.side_effect = models.Purchase.DoesNotExist()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'This sale has already been completed.'}],
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__missing_budgets(self, market_closes_mock, markets_mock):
        """Does not complete the sale.
        
        Redirects to relevant market page and raises error to user.
        """
        
        self.budgets.delete()
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)
        
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
        self.assertRedirects(response, self.womens_url)
        
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
        
        mens_crew = models.Crew.objects.filter(gender = genders.MENS).first()
        purchase_men = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = mens_crew,
        )
        
        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': purchase_men.id})
        
        mens_url = reverse('fantasybumps:men', kwargs = {'event_tag': self.day.event.tag})
        self.assertRedirects(response, mens_url)
        
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
        self.assertRedirects(response, self.womens_url)
        
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
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT purchase, crew, team, user, day, event
            (2) Transaction overhead
            (4) Sell action queries (2 with caching)
        """
        
        models.Crew.value.cache_clear()
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        with self.assertNumQueries(10):
            self.client.post(self.url, {'purchase': self.purchase.id})



class Test__Switch(TestCase, MessagesMixin):
    """."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    url_name = 'fantasybumps:switch'
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.select_related().first()
        cls.event = cls.day.event
        cls.crew = models.Crew.objects.first()
        
        cls.seat_bow = models.Seat.objects.get(name = 'Bow')
        cls.seat_two = models.Seat.objects.get(name = '2')
        cls.seat_thr = models.Seat.objects.get(name = '3')
        cls.seat_cox = models.Seat.objects.get(name = 'Cox')
        
        cls.ath_bow = cls.crew.crew_lists.create(
            event = cls.event,
            seat = cls.seat_bow,
            name = 'Athlete 1',
        )
        cls.ath_two = cls.crew.crew_lists.create(
            event = cls.event,
            seat = cls.seat_two,
            name = 'Athlete 2',
        )
        cls.ath_thr = cls.crew.crew_lists.create(
            event = cls.event,
            seat = cls.seat_thr,
            name = 'Athlete 3',
        )
        cls.ath_cox = cls.crew.crew_lists.create(
            event = cls.event,
            seat = cls.seat_cox,
            name = 'Cox',
        )
        
        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat_bow,
            crew = cls.crew,
            athlete = cls.ath_bow,
        )
        
        cls.url = reverse(cls.url_name, kwargs = {'purchase_id': cls.purchase.id})
        cls.market_page = reverse(
            'fantasybumps:women',
            kwargs = {'event_tag': cls.event.tag},
        )
    
    
    def setUp(self):
        self.general_methods = [('GET', self.client.get), ('POST', self.client.post)]
        self.purchase.refresh_from_db()
    
    
    def test__general__no_login(self):
        """Redirects non-logged in users."""
        
        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):
                
                response = call(self.url)
                self.assertRedirects(response, reverse('login'))
    
    
    def test__general__unknown_purchases(self):
        """Raises a 404 if the purchase is not recognised."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        url = reverse(self.url_name, kwargs = {'purchase_id': 1000})
        
        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):
                
                response = call(url)
                self.assertEqual(response.status_code, 404)
    
    
    def test__general__purchases_for_other_team(self):
        """Raises a 404 if the purchase does not belong to the user's team."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        other_team = auth.User.objects.create_user('Other User', '', 'other').team
        self.purchase.team = other_team
        self.purchase.save()
        
        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):
                
                response = call(self.url)
                self.assertEqual(response.status_code, 404)
    
    
    @patching.market_is_open(False)
    def test__general__market_closed(self, markets_mock):
        """Switching a cox purchase is not allowed, and redirects to the market page."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.purchase.seat = models.Seat.objects.get(cox = True)
        self.purchase.save()
        
        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):
                
                response = call(self.url)
                self.assertRedirects(response, self.market_page)
                
                self.check_messages(
                    messages.get_messages(response.wsgi_request),
                    [{
                        'level': 'warning',
                        'message': 'Markets are not open to alter this purchase.',
                    }],
                )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__general__switching_coxes(self, market_closes_mock, markets_mock):
        """Switching a cox purchase is not allowed, and redirects to the market page."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.purchase.seat = models.Seat.objects.get(cox = True)
        self.purchase.save()
        
        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):
                
                response = call(self.url)
                self.assertRedirects(response, self.market_page)
                
                self.check_messages(
                    messages.get_messages(response.wsgi_request),
                    [{'level': 'warning', 'message': 'Coxes must stay in their place.'}],
                )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__get(self, market_closes_mock, markets_mock):
        """Provides the frontend with:
            * The main purchase
            * A list of rowers in the target crew (excluding the cox)
            * A list of athletes which have been purchased (excluding the main purchase)
            * A list of seats
        """
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = self.ath_two,
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['purchase'], self.purchase)
        self.assertQuerysetEqual(
            response.context['rowers'],
            [self.ath_bow, self.ath_two, self.ath_thr],  # Does not include ath_cox
            transform = lambda item: item,
        )
        
        self.assertQuerysetEqual(
            response.context['other_purchased_athletes'],
            [self.ath_two],
            transform = lambda item: item,
        )
        
        self.assertQuerysetEqual(
            response.context['seats'],
            models.Seat.objects.all(),
            transform = lambda item: item,
            ordered = False,
        )
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__no_data(self, market_closes_mock, markets_mock):
        """Does not change the athlete on the purchase."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url)
        self.assertRedirects(response, self.market_page)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__not_in_crew(self, market_closes_mock, markets_mock):
        """Cannot switch to an athlete not in the crew."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        second_crew = models.Crew.objects.last()
        self.assertNotEqual(second_crew, self.crew)
        ath_other = second_crew.crew_lists.create(
            event = self.event,
            seat = self.seat_bow,
            name = 'Other',
        )
        
        response = self.client.post(self.url, {'athlete': ath_other.id})
        self.assertRedirects(response, self.market_page)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Must pick a rower from the purchased crew.'}],
        )
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__cox(self, market_closes_mock, markets_mock):
        """Cannot switch to the cox."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url, {'athlete': self.ath_cox.id})
        self.assertRedirects(response, self.market_page)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Must pick a rower from the purchased crew.'}],
        )
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__set(self, market_closes_mock, markets_mock):
        """Adds an athlete to the purchase."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.purchase.athlete = None
        self.purchase.save()
        
        response = self.client.post(self.url, {'athlete': self.ath_bow.id})
        self.assertRedirects(response, self.market_page)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__unset(self, market_closes_mock, markets_mock):
        """Removes the athlete from the purchase."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url, {'athlete': '0'})
        self.assertRedirects(response, self.market_page)
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__switch(self, market_closes_mock, markets_mock):
        """Switches the athlete on the purchase."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        response = self.client.post(self.url, {'athlete': self.ath_two.id})
        self.assertRedirects(response, self.market_page)
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_two)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__already_purchased(self, market_closes_mock, markets_mock):
        """Cannot switch to a named athlete already purchased."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = self.ath_two,
        )
        
        response = self.client.post(self.url, {'athlete': self.ath_two.id})
        self.assertRedirects(response, self.market_page)
        
        self.check_messages(
            messages.get_messages(response.wsgi_request),
            [{'level': 'warning', 'message': 'Cannot pick the same rower twice.'}],
        )
        
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
    
    
    @patching.market_is_open(True)
    @patching.market_closes(timezone.now() + timedelta(1))  # Required for redirect page
    def test__athlete__allow_double_unnamed(self, market_closes_mock, markets_mock):
        """Can have multiple unnamed athletes."""
        
        self.client.login(username = 'DevTeam', password = 'password')
        
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
        )
        
        response = self.client.post(self.url, {'athlete': '0'})
        self.assertRedirects(response, self.market_page)
        
        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)

