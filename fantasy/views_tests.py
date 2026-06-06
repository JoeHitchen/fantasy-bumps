from unittest.mock import patch, Mock
from datetime import date, timedelta
from typing import Callable, Any, TYPE_CHECKING

from django.test import TestCase, Client
from django.db import models as db
from django.utils import timezone
from django.contrib.auth import models as auth
from django.urls import reverse

from core.tests import MessagesTestMixin, exists

from .constants import Series, Genders, GENDERS_OVERALL, money, CoachingCompetitions
from . import models
from . import utils
from . import transactions
from . import patching


if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse
    from django.test.utils import ContextList

    Context = dict[str, Any] | ContextList
    StartOrder = list[db.QuerySet[models.StartOrderPosition]]


class AbstractTestCase:

    subTest: Callable  # type: ignore
    assertEqual: Callable  # type: ignore
    assertTrue: Callable  # type: ignore
    assertFalse: Callable  # type: ignore
    assertQuerySetEqual: Callable  # type: ignore
    assertTemplateUsed: Callable  # type: ignore
    assertNumQueries: Callable  # type: ignore


def prepare_event(user: auth.User, year: int, date_shift: int = 0) -> models.Event:
    """An internal method for creating multiple events."""

    event = models.Event.objects.create(
        series = Series.EIGHTS,
        year = year,
        tag = 'eights{}'.format(year),
        mens_division_sizes = [13, 13, 13, 13, 13, 13, 14],
        womens_division_sizes = [13, 13, 13, 13, 13, 14],
        initial_market_open = '2019-02-24T20:00:00Z',
    )

    models.Day.objects.bulk_create([models.Day(
        event = event,
        name = index,
        date = timezone.localtime().date() + timedelta(days = index - date_shift),
        first_race_time = '12:30' if index != 4 else None,
        last_race_time = '18:45' if index != 4 else None,
    ) for index in range(0, 5)])

    event.fantasies.create(
        team = user.team,
        mens_budget = 967,
        mens_balance = 126,
        womens_budget = 1209,
        womens_balance = 103,
    )

    return event


class Test__Index(TestCase):
    fixtures = ['dev_team', 'seats']

    url = reverse('fantasy:index')

    def setUp(self) -> None:

        self.user = auth.User.objects.get(username = 'DevTeam')

        self.recent_events = [
            prepare_event(self.user, 2021, -2),
            prepare_event(self.user, 2020, 0),
            prepare_event(self.user, 2019, 2),
        ]
        prepare_event(self.user, 2018, 4)
        prepare_event(self.user, 2017, 6)


    def check_event_augmentation(self, event: models.Event, with_user: bool) -> None:
        self.assertEqual(hasattr(event, 'user_fantasy'), with_user)
        self.assertEqual(hasattr(event, 'mens_crew_ready'), with_user)
        self.assertEqual(hasattr(event, 'womens_crew_ready'), with_user)


    def test__without_login(self) -> None:
        """Returns a 200 success with augmented recent and past events."""

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasy/index.html')

        self.assertQuerySetEqual(response.context['recent_events'], self.recent_events)

        for event in response.context['recent_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = False)


    def test__with_login(self) -> None:
        """Returns a 200 success with augmented recent and past events."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasy/index.html')

        self.assertQuerySetEqual(response.context['recent_events'], self.recent_events)

        for event in response.context['recent_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = True)


    def test__query_count__without_login(self) -> None:
        """Expect:
            (1) SELECT recent events
            (1) SELECT event days prefetch

        * Seats query defined but not executed since it is not used
        """

        with self.assertNumQueries(2):
            self.client.get(self.url)


    def test__query_count__with_login(self) -> None:
        """Expect:
            (1) SELECT recent events
            (3) SELECT session, user & team
            (1) SELECT financial information prefetch
            (2) SELECT user crew prefetches
            (1) SELECT all seats
            (1) SELECT event days prefetch
        """
        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(9):
            self.client.get(self.url)



class Test__GuideRules(TestCase):
    fixtures = ['dev_team']

    user: auth.User
    recent_events: list[models.Event]
    past_events: list[models.Event]


    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = auth.User.objects.get(username = 'DevTeam')

        cls.recent_events = [
            prepare_event(cls.user, 2021, -2),
            prepare_event(cls.user, 2020, 0),
            prepare_event(cls.user, 2019, 2),
        ]
        prepare_event(cls.user, 2018, 4)
        prepare_event(cls.user, 2017, 6)


    def test__render(self) -> None:
        """Renders the guide & rules page."""

        response = self.client.get(reverse('fantasy:rules'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasy/rules.html')
        self.assertQuerySetEqual(response.context['recent_events'], self.recent_events)
        self.assertEqual(response.context['money'], money)


    def test__query_count(self) -> None:
        """Expect:
            (1) SELECT recent events
        """

        with self.assertNumQueries(1):
            self.client.get(reverse('fantasy:rules'))



class Test__EventsList(TestCase):
    fixtures = ['dev_team', 'seats']

    url = reverse('fantasy:events')

    user: auth.User
    recent_events: list[models.Event]
    past_events: list[models.Event]


    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = auth.User.objects.get(username = 'DevTeam')

        cls.recent_events = [
            prepare_event(cls.user, 2021, -2),
            prepare_event(cls.user, 2020, 0),
            prepare_event(cls.user, 2019, 2),
        ]
        cls.past_events = [
            prepare_event(cls.user, 2018, 4),
            prepare_event(cls.user, 2017, 6),
        ]


    def check_event_augmentation(self, event: models.Event, with_user: bool) -> None:
        self.assertEqual(hasattr(event, 'user_fantasy'), with_user)
        self.assertEqual(hasattr(event, 'mens_crew_ready'), with_user)
        self.assertEqual(hasattr(event, 'mens_crew_ready'), with_user)


    def test__without_login(self) -> None:
        """Returns a 200 success with augmented recent and past events."""

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasy/events.html')

        self.assertEqual(response.context['recent_events'], self.recent_events)
        self.assertEqual(response.context['past_events'], self.past_events)

        for event in response.context['recent_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = False)

        for event in response.context['past_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = False)


    def test__with_login(self) -> None:
        """Returns a 200 success with augmented recent and past events."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasy/events.html')

        self.assertEqual(response.context['recent_events'], self.recent_events)
        self.assertEqual(response.context['past_events'], self.past_events)

        for event in response.context['recent_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = True)

        for event in response.context['past_events']:
            with self.subTest(year = event.year):
                self.check_event_augmentation(event, with_user = True)


    def test__query_count__without_login(self) -> None:
        """Expect:
            (1) SELECT recent events
            (1) SELECT historical events
            (1) SELECT event days prefetch

        * Seats query defined but not executed since it is not used
        """

        with self.assertNumQueries(3):
            self.client.get(self.url)


    def test__query_count__with_login(self) -> None:
        """Expect:
            (1) SELECT recent events
            (3) SELECT session, user & team
            (1) SELECT historical events
            (1) SELECT financial information prefetch
            (2) SELECT user crew prefetches
            (1) SELECT all seats
            (1) SELECT event days prefetch
        """
        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(10):
            self.client.get(self.url)



class GamePageBase(AbstractTestCase):
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

    url: str
    url_name: str
    template: str

    event: models.Event
    day: models.Day
    prev_day: models.Day
    recent_events: list[models.Event]

    user: auth.User
    team: models.Team

    crew_mens: models.Crew
    crew_womens: models.Crew

    client: Client


    @classmethod
    def setUpTestData(cls) -> None:

        cls.event = exists(models.Event.objects.first())
        cls.team = exists(models.Team.objects.first())
        cls.user = exists(auth.User.objects.first())
        cls.day = exists(cls.event.active_day)
        cls.prev_day = exists(cls.day.prev)

        cls.url = reverse(cls.url_name, kwargs = {'event_tag': cls.event.tag})

        cls.crew_mens = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        cls.crew_womens = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())

        day_shift = (date.today() - cls.day.date).days
        cls.recent_events = [
            prepare_event(cls.user, 2021, 0),
            prepare_event(cls.user, 2020, day_shift + 10),
            prepare_event(cls.user, 2019, day_shift + 12),
        ]
        prepare_event(cls.user, 2018, day_shift + 14)
        prepare_event(cls.user, 2017, day_shift + 16)


    def test__generic__unknown_event(self) -> None:
        """Returns a 404 response if the event tag is not recognised."""

        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': 'unknown'},
        ))
        self.assertEqual(response.status_code, 404)


    def test__generic__without_user(self) -> None:
        """Returns a 200 success, with the event and day in the context but no team."""

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)

        self.assertEqual(response.context['event'], self.event)
        self.assertEqual(response.context['day'], self.day)
        self.assertFalse('team' in response.context)
        self.assertQuerySetEqual(response.context['recent_events'], self.recent_events)

        self.extra_context_without_user(exists(response.context_data))

    def extra_context_without_user(self, context: 'Context') -> None:
        """Extra context tests for without_user base test."""
        pass


    def test__generic__with_user(self) -> None:
        """Returns a 200 success, with the event, day, and team in the context."""

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)

        self.assertEqual(response.context['event'], self.event)
        self.assertEqual(response.context['day'], self.day)
        self.assertEqual(response.context['team'], self.team)
        self.assertQuerySetEqual(response.context['recent_events'], self.recent_events)

        self.extra_context_with_user(response.context)

    def extra_context_with_user(self, context: 'Context') -> None:
        """Extra context tests for with_user base test."""
        pass



class Test__Event(GamePageBase, TestCase):

    # Test settings
    url_name = 'fantasy:event'
    template = 'fantasy/event.html'

    team: models.Team
    team2: models.Team
    seat_bow: models.Seat
    seat_two: models.Seat
    seat_thr: models.Seat
    seat_cox: models.Seat


    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.team.entries.create(event = cls.event)
        cls.team2 = auth.User.objects.create_user('Team 2').team
        cls.team2.entries.create(event = cls.event)

        cls.seat_bow = models.Seat.objects.get(name = 'Bow')
        cls.seat_two = models.Seat.objects.get(name = '2')
        cls.seat_thr = models.Seat.objects.get(name = '3')
        cls.seat_cox = models.Seat.objects.get(name = 'Cox')


    def get_crew(self, gender: Genders, position: int) -> models.Crew:
        """Helper function for retrieving crew by gender and position."""
        return models.Crew.objects.get(
            gender = gender,
            positions__day = self.day,
            positions__rank = position,
        )


    def test__leaderboard(self) -> None:
        """Lists the best fantasies, by total score, if there is one or fewer trophy winners."""

        # Create teams
        fantasies = []
        for index in range(1, 16):
            team = auth.User.objects.create_user('T-{}'.format(index)).team
            fantasy = team.entries.create(
                event = self.event,
                mens_budget = money.INITIAL_BALANCE + 10 * index,
                womens_budget = money.INITIAL_BALANCE + 100 * index,
            )
            if index == 1:
                team.trophies.create(event = self.event, type = models.Trophy.Types.JESTER_SWAN)
            fantasies.append(fantasy)

        response = self.client.get(self.url)
        self.assertContains(response, 'Leaderboard')
        self.assertNotContains(response, 'Trophy Winners')
        self.assertEqual(list(response.context['fantasies']), fantasies[::-1][:5])


    def test__trophies(self) -> None:
        """Lists the trophy winners, if more than one has been awarded."""

        trophies = list(models.Trophy.Types)

        # Create teams
        fantasies = []
        for index in range(1, 16):
            team = auth.User.objects.create_user('T-{}'.format(index)).team
            fantasy = team.entries.create(
                event = self.event,
                mens_budget = money.INITIAL_BALANCE + 10 * index,
                womens_budget = money.INITIAL_BALANCE + 100 * index,
            )
            if index - 1 < len(trophies):
                team.trophies.create(event = self.event, type = trophies[index - 1])
            fantasies.append(fantasy)

        response = self.client.get(self.url)
        # Navigation link prevents checking for "Leaderboard" text exclusion
        self.assertContains(response, 'Trophy Winners')
        self.assertEqual(list(response.context['fantasies']), fantasies[::-1][:5])


    def test__popularity__men(self) -> None:
        """Orders crews according to number of purchases and position on the river."""

        # Get crews
        crew_bl1 = self.get_crew(Genders.MEN, 1)
        crew_bl2 = self.get_crew(Genders.MEN, 2)
        crew_bl3 = self.get_crew(Genders.MEN, 3)
        crew_bl4 = self.get_crew(Genders.MEN, 4)
        crew_bl5 = self.get_crew(Genders.MEN, 5)

        # Create purchases
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_bow)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_two)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_thr)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_cox)
        self.team2.purchases.create(day = self.day, crew = crew_bl4, seat = self.seat_bow)
        self.team2.purchases.create(day = self.day, crew = crew_bl2, seat = self.seat_two)
        self.team2.purchases.create(day = self.day, crew = crew_bl2, seat = self.seat_thr)
        self.team2.purchases.create(day = self.day, crew = crew_bl4, seat = self.seat_cox)

        # Create distraction purchases
        self.team2.purchases.create(day = self.day, crew = self.crew_womens, seat = self.seat_bow)
        self.team2.purchases.create(day = self.prev_day, crew = crew_bl5, seat = self.seat_bow)

        # Create expectation
        expected = [
            (crew_bl3, 4, 2.0),
            (crew_bl2, 2, 1.0),
            (crew_bl4, 2, 1.0),
            (crew_bl1, 0, 0.0),
            (crew_bl5, 0, 0.0),
        ]

        # Run test
        response = self.client.get(self.url)

        for index, crew in enumerate(response.context['popular_crews_men']):
            with self.subTest(order = index + 1):
                self.assertEqual(crew, expected[index][0])
                self.assertEqual(crew.purchase_count, expected[index][1])
                self.assertEqual(crew.popularity, expected[index][2])


    def test__popularity__women(self) -> None:
        """Orders crews according to number of purchases and position on the river."""

        # Get crews
        crew_bl1 = self.get_crew(Genders.WOMEN, 1)
        crew_bl2 = self.get_crew(Genders.WOMEN, 2)
        crew_bl3 = self.get_crew(Genders.WOMEN, 3)
        crew_bl4 = self.get_crew(Genders.WOMEN, 4)
        crew_bl5 = self.get_crew(Genders.WOMEN, 5)

        # Create purchases
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_bow)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_two)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_thr)
        self.team.purchases.create(day = self.day, crew = crew_bl3, seat = self.seat_cox)
        self.team2.purchases.create(day = self.day, crew = crew_bl4, seat = self.seat_bow)
        self.team2.purchases.create(day = self.day, crew = crew_bl2, seat = self.seat_two)
        self.team2.purchases.create(day = self.day, crew = crew_bl2, seat = self.seat_thr)
        self.team2.purchases.create(day = self.day, crew = crew_bl4, seat = self.seat_cox)

        # Create distraction purchases
        self.team2.purchases.create(day = self.day, crew = self.crew_mens, seat = self.seat_bow)
        self.team2.purchases.create(day = self.prev_day, crew = crew_bl5, seat = self.seat_bow)

        # Create expectation
        expected = [
            (crew_bl3, 4, 2.0),
            (crew_bl2, 2, 1.0),
            (crew_bl4, 2, 1.0),
            (crew_bl1, 0, 0.0),
            (crew_bl5, 0, 0.0),
        ]

        # Run test
        response = self.client.get(self.url)

        for index, crew in enumerate(response.context['popular_crews_women']):
            with self.subTest(order = index + 1):
                self.assertEqual(crew, expected[index][0])
                self.assertEqual(crew.purchase_count, expected[index][1])
                self.assertEqual(crew.popularity, expected[index][2])


    def test__query_count__no_trophies(self) -> None:
        """Expect:
            (3) FantasyBumps Overhead - Event (1), Active day (2, but can be 1)
            (1) SELECT Total entry count (for popularity)
            (1) FantasyBumps Overhead - Recent events
            (2) SELECT First and last racing days
            (1) SELECT Trophy winners
            (1) SELECT Top ranked teams
            (2) SELECT Most popular crews of each gender
        """

        for index in range(1, 6):
            team = auth.User.objects.create(username = f'team-{index}').team
            team.entries.create(event = self.event)

        with self.assertNumQueries(11):
            self.client.get(self.url)


    def test__query_count__trophies(self) -> None:
        """Expect:
            (3) FantasyBumps Overhead - Event (1), Active day (2, but can be 1)
            (1) SELECT Total entry count (for popularity)
            (1) FantasyBumps Overhead - Recent events
            (2) SELECT First and last racing days
            (1) SELECT Trophy winners
            (1) SELECT Trophy winner game entries
            (2) SELECT Most popular crews of each gender
        """

        for trophy in models.Trophy.Types:
            team = auth.User.objects.create(
                username = trophy.label,
            ).team
            team.entries.create(event = self.event)
            team.trophies.create(event = self.event, type = trophy)

        with self.assertNumQueries(11):
            self.client.get(self.url)



class Test__EventRules(GamePageBase, TestCase):

    # Test settings
    url_name = 'fantasy:rules'
    template = 'fantasy/rules.html'

    def extra_context_without_user(self, context: 'Context') -> None:
        """Extra context tests for without_user base test."""
        self.assertEqual(context['money'], money)


    def extra_context_with_user(self, context: 'Context') -> None:
        """Extra context tests for with_user base test."""
        self.assertEqual(context['money'], money)



class MarketPageBase(GamePageBase):

    # Test group settings
    gender: Genders
    template = 'fantasy/market.html'

    entry: models.GameEntry


    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.entry = cls.team.entries.create(event = cls.event)

        cls.event.coaching_competition = CoachingCompetitions.BLADES
        cls.event.save()


    def assertStartOrdersEqual(self, received: 'StartOrder', expected: 'StartOrder') -> None:
        """A helper method to compare if two start orders are equal."""

        self.assertEqual(len(received), len(expected))

        for index in range(0, len(expected)):
            with self.subTest(division_index = index):
                self.assertQuerySetEqual(received[index], expected[index])


    def extra_context_without_user(self, context: 'Context') -> None:
        """Extra context tests for without_user base test."""

        self.assertEqual(context['gender'], self.gender)
        self.assertStartOrdersEqual(
            context['start_order'],
            self.day.start_order(self.gender),
        )

        self.assertFalse('crew' in context)
        self.assertFalse('crew_valid' in context)
        self.assertFalse('other_crew_valid' in context)

        self.assertFalse(context['show_crew_actions'])
        self.assertFalse(context['show_coach_fire'])


    def extra_context_with_user(self, context: 'Context') -> None:
        """Extra context tests for with_user base test.

        Cannot test show_crew_actions here, since it depends on market status.
        """

        self.assertEqual(context['gender'], self.gender)
        self.assertStartOrdersEqual(
            context['start_order'],
            self.day.start_order(self.gender),
        )

        self.assertTrue('crew' in context)
        self.assertTrue('crew_valid' in context)
        self.assertTrue('other_crew_valid' in context)


    @patching.market_is_open(False)
    def test__market_closed(self, markets_mock: Mock) -> None:
        """Tests the availability of actions:

        * Crew action availability reflects market status for logged in users.
        * Coach action availability also requires the current day to be the first day.
        * Coach display requires the current day to be the first day or there to be a coach set.

        Does not test response or default context.
        """

        day_shift = timezone.now().date() - self.event.first_day.date + timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertFalse(response.context['show_crew_actions'])
        self.assertTrue(response.context['show_coach_row'])
        self.assertFalse(response.context['show_coach_fire'])
        self.assertFalse(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__market_open(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Tests the availability of actions:

        * Crew action availability reflects market status for logged in users.
        * Coach action availability also requires the current day to be the first day.
        * Coach display requires the current day to be the first day or there to be a coach set.

        Does not test response or default context.
        """

        day_shift = timezone.now().date() - self.event.first_day.date + timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertTrue(response.context['show_coach_row'])
        self.assertTrue(response.context['show_coach_fire'])
        self.assertTrue(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__no_coaching_competition(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Tests the availability of actions:

        * Crew action availability reflects market status for logged in users.
        * Coach actions/displays also require there to be a coaching competition.

        Does not test response or default context.
        """

        day_shift = timezone.now().date() - self.event.first_day.date + timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)
        self.event.coaching_competition = None
        self.event.save()

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertFalse(response.context['show_coach_row'])
        self.assertTrue(response.context['show_coach_fire'])
        self.assertTrue(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__coaches__day_two_with_coach(
        self,
        market_closes_mock:
        Mock, markets_mock: Mock,
    ) -> None:
        """Tests the availability of actions:

        * Crew action availability reflects market status for logged in users.
        * Coach action availability also requires the current day to be the first day.
        * Coach display requires the current day to be the first day or there to be a coach set.

        Does not test response or default context.
        """

        day_shift = timezone.now().date() - self.event.first_day.date - timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertFalse(response.context['show_coach_row'])
        self.assertFalse(response.context['show_coach_fire'])
        self.assertFalse(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__coaches__day_two_without_coach(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """Tests the availability of actions:

        * Crew action availability reflects market status for logged in users.
        * Coach action availability also requires the current day to be the first day.
        * Coach display requires the current day to be the first day or there to be a coach set.

        Does not test response or default context.
        """

        day_shift = timezone.now().date() - self.event.first_day.date - timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertFalse(response.context['show_coach_row'])
        self.assertFalse(response.context['show_coach_fire'])
        self.assertFalse(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__coaches__crew_incomplete(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Coach hiring is not possible if the crew is incomplete.
        """

        for seat in models.Seat.objects.filter(cox = False):
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )

        day_shift = timezone.now().date() - self.event.first_day.date + timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertTrue(response.context['show_coach_row'])
        self.assertTrue(response.context['show_coach_fire'])
        self.assertFalse(response.context['show_coach_hire'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))
    def test__coaches__already_hired(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Coach hiring is not shown if a coach has already been hired.
        """

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = exists(self.event.days.first()),
                crew = {Genders.MEN: self.crew_mens, Genders.WOMEN: self.crew_womens}[self.gender],
                seat = seat,
            )
        self.entry.mens_coach = self.crew_mens
        self.entry.womens_coach = self.crew_womens
        self.entry.save()

        day_shift = timezone.now().date() - self.event.first_day.date + timedelta(1)
        self.event.days.update(date = db.F('date') + day_shift)

        # Test view
        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertTrue(response.context['show_crew_actions'])
        self.assertTrue(response.context['show_coach_row'])
        self.assertTrue(response.context['show_coach_fire'])
        self.assertFalse(response.context['show_coach_hire'])



class Test__Market_Men(MarketPageBase, TestCase):

    # Test settings
    url_name = 'fantasy:men'
    gender = Genders.MEN


    def test__partial_crew(self) -> None:
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """

        self.team.purchases.create(
            day = self.day,
            crew = self.crew_mens,
            seat = exists(models.Seat.objects.first()),
        )

        crew = self.team.get_crew(self.day, Genders.MEN)
        self.assertFalse(utils.has_all_seats(crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertFalse(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])


    def test__crew_valid(self) -> None:
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

        crew = self.team.get_crew(self.day, Genders.MEN)
        self.assertTrue(utils.has_all_seats(crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertTrue(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])


    def test__other_crew_valid(self) -> None:
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

        other_crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertTrue(utils.has_all_seats(other_crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])


    def test__popularity(self) -> None:
        """`purchase_count` and `popularity` are added to start order query sets.
        Popularity is the average number of seats purchased per team, and both are per-day.

        *** Due to limitations, SQLite is unable to test non-integer popularity results. ***
        """

        # Create additional teams
        team2 = auth.User.objects.create_user('Team2').team
        team3 = auth.User.objects.create_user('Team3').team
        team2.entries.create(event = self.event)
        team3.entries.create(event = self.event)

        seat_bow = models.Seat.objects.get(name = 'Bow')
        seat_two = models.Seat.objects.get(name = '2')
        seat_cox = models.Seat.objects.get(name = 'Cox')

        # Create purchases
        team2.purchases.create(day = self.day, crew = self.crew_mens, seat = seat_bow)
        team2.purchases.create(day = self.day, crew = self.crew_mens, seat = seat_two)
        team3.purchases.create(day = self.day, crew = self.crew_mens, seat = seat_cox)

        self.team.purchases.create(day = self.prev_day, crew = self.crew_mens, seat = seat_bow)
        # ^ Distraction, wrong day


        # Generate and test expectations
        expect = {self.crew_mens: {'count': 3, 'popularity': 1.0}}

        response = self.client.get(self.url)
        for division in response.context['start_order']:
            for position in division:
                with self.subTest(crew = position.crew):
                    expect_crew = expect.get(position.crew, {'count': 0, 'popularity': 0})
                    self.assertEqual(position.purchase_count, expect_crew['count'])
                    self.assertEqual(position.popularity, expect_crew['popularity'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Expect:
            (4) FantasyBumps Overhead - Event (1), Active day (2, but can be 1), Recent events (1)
            (2) Django Auth overheard - Session (1), User (1)
            (1) User's team
            (1) All game entries for event (for popularity count)
            (1) User's crew for this gender
            (1) Prefetch purchase positions (for pricing)
            (1) Select all seats
            (1) Select coach
            (1) User's crew of other gender
            (1) User's game entry & financials
            (1) Event's first day
            (2 <-> Divisions) Select start order for each division

            Could be reduced further by fetching the information for every division's start order
            in a single query and filtering in the code. See #88.
        """

        for seat in models.Seat.objects.all():
            athlete = self.crew_mens.crew_lists.create(
                event = self.day.event,
                seat = seat,
                name = str(seat),
            )
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_mens,
                seat = seat,
                athlete = athlete,
            )

        self.client.login(username='DevTeam', password='password')
        with self.assertNumQueries(17):
            self.client.get(self.url)



class Test__Market_Women(MarketPageBase, TestCase):

    # Test settings
    url_name = 'fantasy:women'
    gender = Genders.WOMEN


    def test__partial_crew(self) -> None:
        """
        Returns the user's team, complete or otherwise.
        Does not test response or default context.
        """

        self.team.purchases.create(
            day = self.day,
            crew = self.crew_womens,
            seat = exists(models.Seat.objects.first()),
        )

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertFalse(utils.has_all_seats(crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertFalse(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])


    def test__crew_valid(self) -> None:
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

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertTrue(utils.has_all_seats(crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertEqual(list(response.context['crew']), list(crew))
        self.assertTrue(response.context['crew_valid'])
        self.assertFalse(response.context['other_crew_valid'])


    def test__other_crew_valid(self) -> None:
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

        other_crew = self.team.get_crew(self.day, Genders.MEN)
        self.assertTrue(utils.has_all_seats(other_crew, models.Seat.objects.all()))

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)

        self.assertFalse(response.context['crew'])
        self.assertFalse(response.context['crew_valid'])
        self.assertTrue(response.context['other_crew_valid'])


    def test__popularity(self) -> None:
        """`purchase_count` and `popularity` are added to start order query sets.
        Popularity is the average number of seats purchased per team, and both are per-day.

        *** Due to limitations, SQLite is unable to test non-integer popularity results. ***
        """

        # Create additional teams
        team2 = auth.User.objects.create_user('Team2').team
        team3 = auth.User.objects.create_user('Team3').team
        team2.entries.create(event = self.event)
        team3.entries.create(event = self.event)

        seat_bow = models.Seat.objects.get(name = 'Bow')
        seat_two = models.Seat.objects.get(name = '2')
        seat_cox = models.Seat.objects.get(name = 'Cox')

        # Create purchases
        team2.purchases.create(day = self.day, crew = self.crew_womens, seat = seat_bow)
        team2.purchases.create(day = self.day, crew = self.crew_womens, seat = seat_two)
        team3.purchases.create(day = self.day, crew = self.crew_womens, seat = seat_cox)

        self.team.purchases.create(day = self.prev_day, crew = self.crew_womens, seat = seat_bow)
        # ^ Distraction, wrong day


        # Generate and test expectations
        expect = {self.crew_womens: {'count': 3, 'popularity': 1.0}}

        response = self.client.get(self.url)
        for division in response.context['start_order']:
            for position in division:
                with self.subTest(crew = position.crew):
                    expect_crew = expect.get(position.crew, {'count': 0, 'popularity': 0})
                    self.assertEqual(position.purchase_count, expect_crew['count'])
                    self.assertEqual(position.popularity, expect_crew['popularity'])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Expect:
            (4) FantasyBumps Overhead - Event (1), Active day (2, but can be 1), Recent events (1)
            (2) Django Auth overheard - Session (1), User (1)
            (1) User's team
            (1) All game entries for event (for popularity count)
            (1) User's crew for this gender
            (1) Prefetch purchase positions (for pricing)
            (1) Select all seats
            (1) User's crew of other gender
            (1) User's game entry & financials
            (1) Event's first day
            (2 <-> Divisions) Select start order for each division

            Could be reduced further by fetching the information for every division's start order
            in a single query and filtering in the code. See #88.
        """

        for seat in models.Seat.objects.all():
            athlete = self.crew_womens.crew_lists.create(
                event = self.day.event,
                seat = seat,
                name = str(seat),
            )
            self.team.purchases.create(
                day = self.day,
                crew = self.crew_womens,
                seat = seat,
                athlete = athlete,
            )

        self.client.login(username='DevTeam', password='password')
        with self.assertNumQueries(17):
            self.client.get(self.url)



class LeaderboardPageBase(GamePageBase):

    # Test group settings
    template = 'fantasy/leaderboard.html'

    team_1: models.Team
    team_2: models.Team
    team_3: models.Team
    game_entry_1: models.GameEntry
    game_entry_2: models.GameEntry
    game_entry_3: models.GameEntry

    ranking: Genders | str
    get_ranked_fantasies: Callable[[], list[models.GameEntry]]


    @classmethod
    def setUpTestData(cls) -> None:
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

    def extra_context_without_user(self, context: 'Context') -> None:
        """Extra context tests for without_user base test."""

        self.assertEqual(context['genders'], Genders)
        self.assertEqual(context['GENDERS_OVERALL'], GENDERS_OVERALL)
        self.assertEqual(context['ranking'], self.ranking)
        self.assertEqual(list(context['fantasies']), self.get_ranked_fantasies())


    def extra_context_with_user(self, context: 'Context') -> None:
        """Extra context tests for with_user base test."""

        self.assertEqual(context['genders'], Genders)
        self.assertEqual(context['GENDERS_OVERALL'], GENDERS_OVERALL)
        self.assertEqual(context['ranking'], self.ranking)
        self.assertEqual(list(context['fantasies']), self.get_ranked_fantasies())


    def test__query_count__without_login(self) -> None:
        """ Expect:
            (3) FantasyBumps Overhead - Event (1), Active day (2, but can be 1)
            (1) SELECT recent events
            (1) Get rankings
            (1) Prefetch trophies
        """

        with self.assertNumQueries(6):
            self.client.get(self.url)


    def test__query_count__with_login(self) -> None:
        """ Expect:
            (4) Base queries
            (2) Django Auth overheard
            (1) SELECT recent events
            (1) Get user's team
            (1) Prefetch trophies
        """

        self.client.login(username='DevTeam', password='password')

        with self.assertNumQueries(9):
            self.client.get(self.url)



class Test__Leaderboard_Main(LeaderboardPageBase, TestCase):

    # Test settings
    url_name = 'fantasy:leaderboard'
    ranking = GENDERS_OVERALL

    def get_ranked_fantasies(self) -> list[models.GameEntry]:
        return [self.game_entry_1, self.game_entry_3, self.game_entry_2]



class Test__Leaderboard_Men(LeaderboardPageBase, TestCase):

    # Test settings
    url_name = 'fantasy:leaderboard_men'
    ranking = Genders.MEN

    def get_ranked_fantasies(self) -> list[models.GameEntry]:
        return [self.game_entry_2, self.game_entry_1, self.game_entry_3]



class Test__Leaderboard_Women(LeaderboardPageBase, TestCase):

    # Test settings
    url_name = 'fantasy:leaderboard_women'
    ranking = Genders.WOMEN

    def get_ranked_fantasies(self) -> list[models.GameEntry]:
        return [self.game_entry_1, self.game_entry_3, self.game_entry_2]



class Test__Team(TestCase):
    fixtures = [
        'dev_event',
        'dev_days',
        'dev_team',
    ]

    # Test settings
    url_name = 'fantasy:team'
    template = 'fantasy/team.html'

    url: str
    event: models.Event
    day: models.Day

    user_team: models.Team
    view_team: models.Team
    budgets: models.GameEntry


    @classmethod
    def setUpTestData(cls) -> None:

        cls.event = exists(models.Event.objects.first())
        cls.user_team = exists(models.Team.objects.select_related().first())
        cls.day = cls.event.active_day

        cls.view_team = auth.User.objects.create_user('Target', '', '').team
        cls.budgets = cls.view_team.entries.create(event = cls.event)

        cls.url = reverse(
            cls.url_name,
            kwargs = {'event_tag': cls.event.tag, 'team_name': cls.view_team},
        )


    def setUp(self) -> None:
        self.budgets = self.view_team.entries.get(event = self.event)


    def test__unknown_event(self) -> None:
        """Returns a 404 response if the event tag is not recognised."""

        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': 'Unknown', 'team_name': self.view_team},
        ))
        self.assertEqual(response.status_code, 404)


    def test__unknown_team(self) -> None:
        """Returns a 404 response if the team not recognised."""

        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': self.event.tag, 'team_name': 'Unknown'},
        ))
        self.assertEqual(response.status_code, 404)


    def test__not_entered(self) -> None:
        """Returns a 404 response if the team has no entry for the event."""

        self.budgets.delete()

        response = self.client.get(reverse(
            self.url_name,
            kwargs = {'event_tag': self.event.tag, 'team_name': self.view_team},
        ))
        self.assertEqual(response.status_code, 404)


    @patching.team_get_crew
    def test__without_login(self, get_crew_mock: Mock) -> None:
        """Generates a context containing the selected team, their financials, and their crews."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)

        self.assertEqual(response.context['team'], self.view_team)
        self.assertEqual(response.context['finances'], self.budgets)

        self.assertEqual(
            response.context['mens_crew'],
            (self.view_team, self.day, Genders.MEN),
        )
        self.assertEqual(
            response.context['womens_crew'],
            (self.view_team, self.day, Genders.WOMEN),
        )


    @patching.team_get_crew
    def test__with_login(self, get_crew_mock: Mock) -> None:
        """Does not replace the requested team with the viewer's own team."""

        self.client.login(username='DevTeam', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template)

        self.assertEqual(response.context['team'], self.view_team)
        self.assertEqual(response.context['finances'], self.budgets)

        self.assertEqual(
            response.context['mens_crew'],
            (self.view_team, self.day, Genders.MEN),
        )
        self.assertEqual(
            response.context['womens_crew'],
            (self.view_team, self.day, Genders.WOMEN),
        )


    def test__query_count(self) -> None:
        """ Expect:
            (3) SELECT event and active day
            (1) SELECT team to view
            (1) SELECT recent events
            (1) SELECT all seats
            (2) SELECT purchases for crew lists (one for each crew lists)
            (2) SELECT coaches (one for each crew list)
        """

        with self.assertNumQueries(10):
            response = self.client.get(self.url)

            # Needed to force crew list queries
            list(response.context['mens_crew'])
            list(response.context['womens_crew'])



class Test__Buy(TestCase, MessagesTestMixin):
    """Testing of transaction behaviour (including side effects) is delegated to the relevant
    subroutine."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    url = reverse('fantasy:buy')

    womens_url: str

    day: models.Day
    crew: models.Crew
    team: models.Team
    budgets: models.GameEntry


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.select_related().first())
        cls.crew = exists(models.Crew.objects.first())

        cls.budgets = cls.team.entries.create(event = cls.day.event)

        cls.womens_url = reverse('fantasy:women', kwargs = {'event_tag': cls.day.event.tag})


    def setUp(self) -> None:
        self.budgets = self.team.entries.get(event = self.day.event)


    def test__deny_get(self) -> None:
        """Rejects non-POST requests."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


    def test__no_login(self) -> None:
        """Redirects non-logged in users."""

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))


    def test__missing_day(self) -> None:
        """Denies request - Redirects to fantasy root and raises error to user."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'crew': self.crew.id})

        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [
            ('error', 'An error occurred processing the request data.'),
        ])


    def test__unknown_day(self) -> None:
        """Denies request - Redirects to fantasy root and raises error to user."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': 10000, 'crew': self.crew.id})

        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [
            ('error', 'An error occurred processing the request data.'),
        ])


    def test__missing_crew(self) -> None:
        """Denies request - Redirects to fantasy root and raises error to user."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id})

        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [
            ('error', 'An error occurred processing the request data.'),
        ])


    def test__unknown_crew(self) -> None:
        """Denies request - Redirects to fantasy root and raises error to user."""

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': 10000})

        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [
            ('error', 'An error occurred processing the request data.'),
        ])


    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock: Mock) -> None:
        """Denies request if market not open for intended day.

        Redirects to relevant market page and raises warning to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', 'Markets are not open for this sale.')])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__not_racing(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Does not complete the sale.

        Redirects to relevant market page and raises warning to user.
        """

        self.crew.positions.filter(day = self.day).delete()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [
            ('warning', 'Cannot buy a crew on a day they are not racing.'),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__insufficient_funds(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Does not complete the sale.

        Redirects to relevant market page and raises warning to user.
        """

        self.budgets.womens_balance = 0
        self.budgets.save()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [
            ('warning', 'You do not have sufficient funds to make this purchase.'),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_womens(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the purchase.

        Redirects to relevant market page and raises success to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Bought Oriel W1 as your women's bow seat.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_mens(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the purchase.

        Redirects to relevant market page and raises success to user.
        """

        mens_crew = exists(models.Crew.objects.filter(gender = Genders.MEN).first())

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': mens_crew.id})

        mens_url = reverse('fantasy:men', kwargs = {'event_tag': self.day.event.tag})
        self.assertRedirects(response, mens_url)

        self.assertMessages(response, [('success', "Bought Oriel M1 as your men's bow seat.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_cox(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the purchase.

        Redirects to relevant market page and raises success to user.
        """

        for seat in models.Seat.objects.exclude(cox = True):
            self.team.purchases.create(day = self.day, seat = seat, crew = self.crew)

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Bought Oriel W1 as your women's cox.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__with_athlete(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the purchase.

        Redirects to relevant market page and raises success to user.
        """

        self.crew.crew_lists.create(
            event = self.day.event,
            seat = exists(models.Seat.objects.first()),
            name = 'Test Athlete',
        )

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [
            ('success', "Bought Test Athlete (Oriel W1) as your women's bow seat."),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__all_seats_filled(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Does not complete the sale.

        Redirects to relevant market page and raises warning to user.
        """

        for seat in models.Seat.objects.all():
            self.team.purchases.create(day = self.day, seat = seat, crew = self.crew)

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', "You have already filled your women's crew.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__budgets_missing(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the purchase as normal, creating the missing budgets."""

        self.budgets.delete()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Bought Oriel W1 as your women's bow seat.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count__standard(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT day, event
            (1) SELECT crew
            (1) SELECT user's team
            (1) SELECT seat - 'filled_seats' not evaluated separately
            (1) SELECT athlete
            (2) Transaction overhead
            (5) Buy action queries
        """

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(14):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count__without_budgets(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """ Expect:
            (14) Queried as standard
            (3) Extra action queries
        """

        self.budgets.delete()

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(17):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count__with_athlete(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """ Expect:
            (14) Queried as standard
        """

        for seat in models.Seat.objects.all():
            self.crew.crew_lists.create(event = self.day.event, seat = seat, name = 'Test Athlete')

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(14):
            self.client.post(self.url, {'day': self.day.id, 'crew': self.crew.id})



class Test__Sell(TestCase, MessagesTestMixin):
    """Testing of transaction behaviour (including side effects) is delegated to the relevant
    subroutine."""
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats', 'dev_team']
    url = reverse('fantasy:sell')

    womens_url: str

    day: models.Day
    crew: models.Crew
    seat: models.Seat

    team: models.Team
    budgets: models.GameEntry
    purchase: models.Purchase


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.select_related().first())
        cls.crew = exists(models.Crew.objects.first())
        cls.seat = exists(models.Seat.objects.first())

        cls.budgets = cls.team.entries.create(
            event = cls.day.event,
            mens_balance = 650,
            womens_balance = 650,
        )

        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )

        cls.womens_url = reverse('fantasy:women', kwargs = {'event_tag': cls.day.event.tag})


    def test__deny_get(self) -> None:
        """Rejects non-POST requests."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


    def test__no_login(self) -> None:
        """Redirects non-logged in users."""

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))


    def test__no_data(self) -> None:
        """Denies request if no purchase number is supplied.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'You are not authorised to conduct this sale.')])


    def test__unknown_purchase(self) -> None:
        """Denies request if the purchase does not exist.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'purchase': 100000})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'You are not authorised to conduct this sale.')])


    def test__other_team(self) -> None:
        """Denies request if the purchase does not belong to the user.

        Redirects to fantasy root and raises error to user.
        """

        auth.User.objects.create_user('Other', '', 'pw')
        self.client.login(username = 'Other', password = 'pw')

        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'You are not authorised to conduct this sale.')])


    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock: Mock) -> None:
        """Denies request if market not open for purchase's day.

        Redirects to relevant market page and raises warning to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', 'Markets are not open for this sale.')])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    @patch.object(transactions, 'sell')
    def test__race_condition(
        self,
        transaction_mock: Mock,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """Does not complete the sale.

        Occurs when another thread deletes the purchase after it has been retrieved.
        Redirects to relevant market page and raises error to user.
        """

        transaction_mock.side_effect = models.Purchase.DoesNotExist()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', 'This sale has already been completed.')])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__missing_budgets(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Does not complete the sale.

        Redirects to relevant market page and raises error to user.
        """

        self.budgets.delete()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [
            ('error', 'An unknown error occurred processing this sale.'),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_womens(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the sale.

        Redirects to relevant market page and raises success to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Sold Oriel W1 from your women's bow seat.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_mens(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the sale.

        Redirects to relevant market page and raises success to user.
        """

        mens_crew = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        purchase_men = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = mens_crew,
        )

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': purchase_men.id})

        mens_url = reverse('fantasy:men', kwargs = {'event_tag': self.day.event.tag})
        self.assertRedirects(response, mens_url)

        self.assertMessages(response, [('success', "Sold Oriel M1 from your men's bow seat.")])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__valid_cox(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
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

        self.assertMessages(response, [
            ('success', "Sold Oriel W1 from your women's coxing seat."),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__with_athlete(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Completes the sale.

        Redirects to relevant market page and raises success to user.
        """

        athlete = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat,
            name = 'Sale',
        )
        self.purchase.athlete = athlete
        self.purchase.save()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'purchase': self.purchase.id})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [
            ('success', "Sold Sale (Oriel W1) from your women's bow seat."),
        ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT purchase, crew, team, user, day, event
            (2) Transaction overhead
            (3) Sell action queries
        """

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(9):
            self.client.post(self.url, {'purchase': self.purchase.id})



class Test__Hire(TestCase, MessagesTestMixin):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_team']
    url = reverse('fantasy:hire')

    team: models.Team
    event: models.Event
    mens_crew: models.Crew
    womens_crew: models.Crew

    entry: models.GameEntry

    womens_url: str


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.event = exists(models.Event.objects.first())
        cls.mens_crew = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        cls.womens_crew = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())

        cls.entry = cls.team.entries.create(event = cls.event)

        cls.womens_url = reverse('fantasy:women', kwargs = {'event_tag': cls.event.tag})


    def test__deny_get(self) -> None:
        """Rejects non-POST requests."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    def test__no_login(self) -> None:
        """Redirects non-logged in users."""

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    def test__no_data(self) -> None:
        """Denies request if no data is supplied.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to find a matching competition entry.')])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    def test__unknown_event(self) -> None:
        """Denies request if the event does not exist or there is no corresponding game entry.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {
            'event': 'citybumps2026',
            'crew': self.womens_crew.id,
        })
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to find a matching competition entry.')])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    def test__unknown_crew(self) -> None:
        """Denies request if there is no crew specified.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': self.event.tag, 'crew': 1000})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to find the coach being hired.')])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock: Mock) -> None:
        """Denies request if market not open for the event's first day.

        Redirects to relevant market page and raises warning to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {
            'event': self.event.tag,
            'crew': self.womens_crew.id,
        })
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', 'Markets are not open for this hiring.')])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertIsNone(self.entry.womens_coach)


    @patching.market_is_open(True)
    def test__valid_womens(self, markets_mock: Mock) -> None:
        """Completes the hiring.

        Redirects to relevant market page and raises success to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {
            'event': self.event.tag,
            'crew': self.womens_crew.id,
        })
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Hired Oriel W1 as your women's coach.")])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    @patching.market_is_open(True)
    def test__valid_mens(self, markets_mock: Mock) -> None:
        """Completes the hiring.

        Redirects to relevant market page and raises success to user.
        """

        mens_url = reverse('fantasy:men', kwargs = {'event_tag': self.event.tag})
        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {
            'event': self.event.tag,
            'crew': self.mens_crew.id,
        })
        self.assertRedirects(response, mens_url)

        self.assertMessages(response, [('success', "Hired Oriel M1 as your men's coach.")])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertIsNone(self.entry.womens_coach)


    @patching.market_is_open(True)
    def test__query_count(self, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT game entry and event
            (1) SELECT target crew
            (1) SELECT event's first day
            (1) UPDATE coach
        """

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(7):
            self.client.post(self.url, {'event': self.event.tag, 'crew': self.womens_crew.id})



class Test__Fire(TestCase, MessagesTestMixin):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_team']
    url = reverse('fantasy:fire')

    womens_url: str

    event: models.Event
    mens_crew: models.Crew
    womens_crew: models.Crew

    team: models.Team
    entry: models.GameEntry


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.event = exists(models.Event.objects.first())
        cls.mens_crew = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        cls.womens_crew = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())

        cls.entry = cls.team.entries.create(
            event = cls.event,
            mens_coach = cls.mens_crew,
            womens_coach = cls.womens_crew,
        )

        cls.womens_url = reverse('fantasy:women', kwargs = {'event_tag': cls.event.tag})


    def test__deny_get(self) -> None:
        """Rejects non-POST requests."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    def test__no_login(self) -> None:
        """Redirects non-logged in users."""

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    def test__no_data(self) -> None:
        """Denies request if no data is supplied.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to identify the coach to be fire.')])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    def test__unknown_event(self) -> None:
        """Denies request if the event does not exist or there is no corresponding game entry.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': 'citybumps2026', 'gender': 'X'})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to identify the coach to be fire.')])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    def test__unknown_gender(self) -> None:
        """Denies request if the gender provided is not recognised.

        Redirects to fantasy root and raises error to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': self.event.tag, 'gender': 'X'})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.assertMessages(response, [('error', 'Unable to identify the coach to be fire.')])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    @patching.market_is_open(False)
    def test__markets_not_open(self, markets_mock: Mock) -> None:
        """Denies request if market not open for the event's first day.

        Redirects to relevant market page and raises warning to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'event': self.event.tag, 'gender': Genders.WOMEN})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('warning', 'Markets are not open for this firing.')])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    @patching.market_is_open(True)
    def test__no_coach(self, markets_mock: Mock) -> None:
        """Handles the case where there is no coach to be fired gracefully.

        Redirects to relevant market page and raises success to user.
        """

        self.entry.womens_coach = None
        self.entry.save()

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'event': self.event.tag, 'gender': Genders.WOMEN})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Your women's coaching slot is now empty.")])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertIsNone(self.entry.womens_coach)


    @patching.market_is_open(True)
    def test__valid_mens(self, markets_mock: Mock) -> None:
        """Completes the firing.

        Redirects to relevant market page and raises success to user.
        """

        mens_url = reverse('fantasy:men', kwargs = {'event_tag': self.event.tag})

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'event': self.event.tag, 'gender': Genders.MEN})
        self.assertRedirects(response, mens_url)

        self.assertMessages(response, [('success', "Fired Oriel M1 as your men's coach.")])

        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.mens_coach)
        self.assertEqual(self.entry.womens_coach, self.womens_crew)


    @patching.market_is_open(True)
    def test__valid_womens(self, markets_mock: Mock) -> None:
        """Completes the firing.

        Redirects to relevant market page and raises success to user.
        """

        self.client.login(username = 'DevTeam', password = 'password')
        response = self.client.post(self.url, {'event': self.event.tag, 'gender': Genders.WOMEN})
        self.assertRedirects(response, self.womens_url)

        self.assertMessages(response, [('success', "Fired Oriel W1 as your women's coach.")])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.mens_coach, self.mens_crew)
        self.assertIsNone(self.entry.womens_coach)


    @patching.market_is_open(True)
    def test__query_count(self, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT game entry, event, and coach-crews
            (1) SELECT event's first day
            (1) UPDATE coach
        """

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(6):
            self.client.post(self.url, {'event': self.event.tag, 'gender': Genders.WOMEN})



class Test__Switch(TestCase, MessagesTestMixin):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']
    url_name = 'fantasy:switch'
    template = 'fantasy/switch.html'

    url: str
    market_page: str

    event: models.Event
    day: models.Day
    crew: models.Crew

    seat_bow: models.Seat
    seat_two: models.Seat
    seat_thr: models.Seat
    seat_cox: models.Seat

    ath_bow: models.Athlete
    ath_two: models.Athlete
    ath_thr: models.Athlete
    ath_cox: models.Athlete

    team: models.Team
    purchase: models.Purchase


    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.select_related().first())
        cls.event = exists(cls.day.event)
        cls.crew = exists(models.Crew.objects.first())

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
            'fantasy:women',
            kwargs = {'event_tag': cls.event.tag},
        )


    def setUp(self) -> None:
        self.general_methods: list[tuple[str, Callable[[str], 'TestHttpResponse']]] = [
            ('GET', self.client.get),
            ('POST', self.client.post),
        ]
        self.purchase.refresh_from_db()


    def test__general__no_login(self) -> None:
        """Redirects non-logged in users."""

        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):

                response = call(self.url)
                self.assertRedirects(response, reverse('login'))


    def test__general__unknown_purchases(self) -> None:
        """Raises a 404 if the purchase is not recognised."""

        self.client.login(username = 'DevTeam', password = 'password')
        url = reverse(self.url_name, kwargs = {'purchase_id': 1000})

        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):

                response = call(url)
                self.assertEqual(response.status_code, 404)


    def test__general__purchases_for_other_team(self) -> None:
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
    def test__general__market_closed(self, markets_mock: Mock) -> None:
        """Switching a cox purchase is not allowed, and redirects to the market page."""

        self.client.login(username = 'DevTeam', password = 'password')

        self.purchase.seat = models.Seat.objects.get(cox = True)
        self.purchase.save()

        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):

                response = call(self.url)
                self.assertRedirects(response, self.market_page)

                self.assertMessages(response, [
                    ('warning', 'Markets are not open to alter this purchase.'),
                ])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__general__switching_coxes(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Switching a cox purchase is not allowed, and redirects to the market page."""

        self.client.login(username = 'DevTeam', password = 'password')

        self.purchase.seat = models.Seat.objects.get(cox = True)
        self.purchase.save()

        # Call both GET and POST
        for method, call in self.general_methods:
            with self.subTest(method = method):

                response = call(self.url)
                self.assertRedirects(response, self.market_page)

                self.assertMessages(response, [('warning', 'Coxes must stay in their place.')])


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__get(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
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
        self.assertTemplateUsed(response, self.template)

        self.assertEqual(response.context['purchase'], self.purchase)
        self.assertQuerySetEqual(
            response.context['rowers'],
            [self.ath_bow, self.ath_two, self.ath_thr],  # Does not include ath_cox
        )

        self.assertQuerySetEqual(
            response.context['other_purchased_athletes'],
            [self.ath_two],
        )

        self.assertQuerySetEqual(
            response.context['seats'],
            list(models.Seat.objects.all()),
            ordered = False,
        )

        self.assertQuerySetEqual(
            response.context['recent_events'],
            list(models.Event.objects.all()),
        )


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__post__no_data(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Does not change the athlete or seat on the purchase."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url)
        self.assertRedirects(response, self.market_page)

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)
        self.assertEqual(self.purchase.seat, self.seat_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__not_in_crew(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Cannot switch to an athlete not in the crew."""

        self.client.login(username = 'DevTeam', password = 'password')

        second_crew = exists(models.Crew.objects.last())
        self.assertNotEqual(second_crew, self.crew)
        ath_other = second_crew.crew_lists.create(
            event = self.event,
            seat = self.seat_bow,
            name = 'Other',
        )

        POST_data = {'athlete': ath_other.id, 'seat': self.seat_bow.id}
        response = self.client.post(self.url, POST_data)
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [('warning', 'Must pick a rower from the purchased crew.')])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__cox(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Cannot switch to the cox."""

        self.client.login(username = 'DevTeam', password = 'password')

        POST_data = {'athlete': self.ath_cox.id, 'seat': self.seat_bow.id}
        response = self.client.post(self.url, POST_data)
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [('warning', 'Must pick a rower from the purchased crew.')])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__set(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Adds an athlete to the purchase."""

        self.client.login(username = 'DevTeam', password = 'password')

        self.purchase.athlete = None
        self.purchase.save()

        POST_data = {'athlete': self.ath_bow.id, 'seat': self.seat_bow.id}
        response = self.client.post(self.url, POST_data)
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [
            ('success', "Selected Athlete 1 (Oriel W1) for your women's bow seat."),
        ])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__unset(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Removes the athlete from the purchase."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'athlete': '0', 'seat': self.seat_bow.id})
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [
            ('success', "Selected Oriel W1 for your women's bow seat."),
        ])

        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__switch(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Switches the athlete on the purchase."""

        self.client.login(username = 'DevTeam', password = 'password')

        POST_data = {'athlete': self.ath_two.id, 'seat': self.seat_bow.id}
        response = self.client.post(self.url, POST_data)
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [
            ('success', "Selected Athlete 2 (Oriel W1) for your women's bow seat."),
        ])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_two)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__already_purchased(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """Cannot switch to a named athlete already purchased."""

        self.client.login(username = 'DevTeam', password = 'password')

        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = self.ath_two,
        )

        POST_data = {'athlete': self.ath_two.id, 'seat': self.seat_bow.id}
        response = self.client.post(self.url, POST_data)
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [('warning', 'Cannot pick the same rower twice.')])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.athlete, self.ath_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__athlete__allow_double_unnamed(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """Can have multiple unnamed athletes."""

        self.client.login(username = 'DevTeam', password = 'password')

        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
        )

        response = self.client.post(self.url, {'athlete': '0', 'seat': self.seat_bow.id})
        self.assertRedirects(response, self.market_page)

        self.purchase.refresh_from_db()
        self.assertIsNone(self.purchase.athlete)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__seat__unknown(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Cannot switch an unknown seat."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'seat': '11'})
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [('warning', 'Target seat does not exist.')])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__seat__cox(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Cannot switch to the coxing seat."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'seat': self.seat_cox.id})
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [('warning', "Rowers can't cox.")])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__seat__unchanged(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Performs no action if switching to current seat."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'seat': self.seat_bow.id})
        self.assertRedirects(response, self.market_page)

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__seat__unoccupied(
        self,
        market_closes_mock: Mock,
        markets_mock: Mock,
    ) -> None:
        """Moves athlete into empty seat."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'seat': self.seat_two.id})
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [
            ('success', "Selected Athlete 1 (Oriel W1) for your women's 2-seat."),
        ])

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__seat__occupied(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """Switches places with athlete in target seat."""

        self.client.login(username = 'DevTeam', password = 'password')

        other_purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = self.ath_two,
        )
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_thr,
            crew = self.crew,
            athlete = self.ath_thr,
        )

        response = self.client.post(self.url, {'seat': self.seat_two.id})
        self.assertRedirects(response, self.market_page)

        self.assertMessages(response, [
            ('success', "Selected Athlete 1 (Oriel W1) for your women's 2-seat."),
        ])

        self.purchase.refresh_from_db()
        other_purchase.refresh_from_db()
        self.assertEqual(self.purchase.seat, self.seat_two)
        self.assertEqual(other_purchase.seat, self.seat_bow)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count__get(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT purchase, crew, day, event, and seat
            (1) SELECT recent events
            (1) SELECT purchase.athlete  (Skipped by above, because nullable)
            (1) SELECT list of crew's rowers
            (1) SELECT list of other purchases
            (1) SELECT list of seats
        """

        self.client.login(username = 'DevTeam', password = 'password')

        with self.assertNumQueries(9):
            self.client.get(self.url)


    @patching.market_is_open(True)
    @patching.market_closes(timezone.localtime() + timedelta(1))  # Required for redirect page
    def test__query_count__post(self, market_closes_mock: Mock, markets_mock: Mock) -> None:
        """ Expect:
            (2) Django internals
            (1) SELECT user's team  (Could be avoided by comparing on User, but that feels wrong)
            (1) SELECT purchase, crew, day, event, and seat
            (1) SELECT new seat
            (1) SELECT new athlete
            (2) Transaction overhead
            (1) SELECT purchase.athlete  (Skipped by above, because nullable)
            (3) Main action
        """

        self.client.login(username = 'DevTeam', password = 'password')

        self.team.purchases.create(
            day = self.day,
            seat = self.seat_two,
            crew = self.crew,
            athlete = self.ath_two,
        )
        self.team.purchases.create(
            day = self.day,
            seat = self.seat_thr,
            crew = self.crew,
        )

        with self.assertNumQueries(12):
            self.client.post(self.url, {'athlete': self.ath_thr.id, 'seat': self.seat_two.id})



class Test__Market_Hold(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_team']
    url = reverse('fantasy:market-hold')

    event: models.Event

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())


    def test__deny_get(self) -> None:
        """Rejects non-POST requests."""

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)


    def test__no_login(self) -> None:
        """Redirects non-logged in users."""

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)


    def test__not_superuser(self) -> None:
        """Redirects non-superusers."""

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('login'))

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)


    def test__no_event(self) -> None:
        """Raises a 404 if the event is not known."""

        user = auth.User.objects.get(username = 'DevTeam')
        user.is_superuser = True
        user.save()

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': 'unknown'})
        self.assertEqual(response.status_code, 404)

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)


    def test__no_toggle_status(self) -> None:
        """Markets stay open if no previous toggle status is specified."""

        user = auth.User.objects.get(username = 'DevTeam')
        user.is_superuser = True
        user.save()

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': self.event.tag})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)


    def test__close_market(self) -> None:
        """Toggles the `market_held_closed` flag."""

        user = auth.User.objects.get(username = 'DevTeam')
        user.is_superuser = True
        user.save()

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': self.event.tag, 'toggle-from': 'False'})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.event.refresh_from_db()
        self.assertTrue(self.event.market_held_closed)


    def test__reopen_market(self) -> None:
        """Toggles the `market_held_closed` flag."""

        user = auth.User.objects.get(username = 'DevTeam')
        user.is_superuser = True
        user.save()

        self.client.login(username = 'DevTeam', password = 'password')

        response = self.client.post(self.url, {'event': self.event.tag, 'toggle-from': 'True'})
        self.assertRedirects(response, reverse('fantasy:index'))

        self.event.refresh_from_db()
        self.assertFalse(self.event.market_held_closed)

