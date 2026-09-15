import json
from typing import Any

from django.test import TestCase
from django.contrib.auth import models as auth
from django.urls import reverse

from core.tests import exists

from .constants import Genders
from . import models


class Test__MCPTools(TestCase):

    fixtures = [
        'dev_event',
        'dev_days',
        'dev_crews',
        'dev_start_day1',
        'dev_start_day2',
        'dev_start_day3',
        'seats',
    ]

    event: models.Event
    day: models.Day
    prev_day: models.Day
    team_1: models.Team
    team_2: models.Team
    team_3: models.Team
    crew_mens: models.Crew
    crew_womens: models.Crew

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())
        cls.day = exists(cls.event.active_day)
        cls.prev_day = exists(cls.day.prev)

        cls.crew_mens = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        cls.crew_womens = exists(models.Crew.objects.filter(gender = Genders.WOMEN).first())

        cls.team_1 = auth.User.objects.create_user('One', '', '').team
        cls.team_2 = auth.User.objects.create_user('Two', '', '').team
        cls.team_3 = auth.User.objects.create_user('Three', '', '').team

        cls.event.fantasies.create(
            team = cls.team_1,
            mens_budget = 967, mens_balance = 126,
            womens_budget = 1209, womens_balance = 103,
            valid_entry = True,
        )
        cls.event.fantasies.create(
            team = cls.team_2,
            mens_budget = 754, womens_budget = 456,
            mens_balance = 120, womens_balance = 105,
            valid_entry = True,
        )
        cls.event.fantasies.create(
            team = cls.team_3,
            mens_budget = 701, womens_budget = 713,
            mens_balance = 117, womens_balance = 112,
            valid_entry = False,
            has_subs = True,
        )


    def tool_call(self, name: str, arguments: dict[str, Any]) -> Any:
        """Makes a real tool call to /mcp/ and returns the JSON-RPC result."""

        response = self.client.post(
            '/mcp/',
            data = json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'tools/call',
                'params': {'name': name, 'arguments': arguments},
            }),
            content_type = 'application/json',
            HTTP_ACCEPT = 'application/json',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['result']


    def get_api_json(
        self,
        url_name: str,
        url_kwargs: dict[str, Any] = {},
        query: dict[str, int] = {},
    ) -> Any:
        """Fetches a public JSON endpoint for comparison data."""

        response = self.client.get(
            reverse('fantasy:{}'.format(url_name), kwargs = url_kwargs),
            HTTP_ACCEPT = 'application/json',
            data = query,
        )
        return response.json()


    def test__list_events(self) -> None:
        """Returns data matching the API's index response."""

        result = self.tool_call('list_events', {})
        self.assertFalse(result['isError'])

        self.assertEqual(
            result['structuredContent']['result'],
            self.get_api_json('index')['events'],
        )


    def test__get_event_details__event_unknown(self) -> None:
        """Returns a tool-level error for unknown events and a readable message in the content."""

        result = self.tool_call('get_event_details', {'series': 'X', 'year': 2009})
        self.assertTrue(result['isError'])


    def test__get_event_details__event_exists(self) -> None:
        """Returns data matching the API's event response."""

        result = self.tool_call('get_event_details', {
            'series': self.event.series,
            'year': self.event.year,
        })
        self.assertFalse(result['isError'])

        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('event', {'event_tag': self.event.tag}),
        )


    def test__get_event_market__event_unknown(self) -> None:
        """Returns a tool-level error for unknown events and a readable message in the content."""

        result = self.tool_call('get_event_market', {
            'series': 'X',
            'year': 2009,
            'gender': Genders.MEN.value,
        })
        self.assertTrue(result['isError'])


    def test__get_event_market__mens_market(self) -> None:
        """Returns data matching the API's men's market response."""

        result = self.tool_call('get_event_market', {
            'series': self.event.series,
            'year': self.event.year,
            'gender': Genders.MEN.value,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('men', {'event_tag': self.event.tag}),
        )


    def test__get_event_market__womens_market(self) -> None:
        """Returns data matching the API's women's market response."""

        result = self.tool_call('get_event_market', {
            'series': self.event.series,
            'year': self.event.year,
            'gender': Genders.WOMEN.value,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('women', {'event_tag': self.event.tag}),
        )


    def test__get_event_leaderboard__event_unknown(self) -> None:
        """Returns a tool-level error for unknown events and a readable message in the content."""

        result = self.tool_call('get_event_leaderboard', {'series': 'X', 'year': 2009})
        self.assertTrue(result['isError'])


    def test__get_event_leaderboard__overall(self) -> None:
        """Returns data matching the API's overall leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('leaderboard', {'event_tag': self.event.tag}),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': True, 'allow-subs': True, 'returners': True},
        )


    def test__get_event_leaderboard__mens(self) -> None:
        """Returns data matching the API's mens's leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
            'gender': Genders.MEN.value,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('leaderboard_men', {'event_tag': self.event.tag}),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': True, 'allow-subs': True, 'returners': True},
        )


    def test__get_event_leaderboard__womens(self) -> None:
        """Returns data matching the API's womens's leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
            'gender': Genders.WOMEN.value,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('leaderboard_women', {'event_tag': self.event.tag}),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': True, 'allow-subs': True, 'returners': True},
        )


    def test__get_event_leaderboard__invalid_entries(self) -> None:
        """Returns data matching the API's filtered leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
            'invalid_entries': False,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json(
                'leaderboard',
                {'event_tag': self.event.tag},
                query = {'invalid-entries': False},
            ),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': False, 'allow-subs': True, 'returners': True},
        )


    def test__get_event_leaderboard__allow_subs_filter(self) -> None:
        """Returns data matching the API's allow-subs-filtered leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
            'allow_subs': False,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json(
                'leaderboard',
                {'event_tag': self.event.tag},
                query = {'allow-subs': False},
            ),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': True, 'allow-subs': False, 'returners': True},
        )


    def test__get_event_leaderboard__returners(self) -> None:
        """Returns data matching the API's filtered leaderboard response."""

        result = self.tool_call('get_event_leaderboard', {
            'series': self.event.series,
            'year': self.event.year,
            'returners': False,
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json(
                'leaderboard',
                {'event_tag': self.event.tag},
                query = {'returners': False},
            ),
        )
        self.assertEqual(
            result['structuredContent']['filters'],
            {'invalid-entries': True, 'allow-subs': True, 'returners': False},
        )


    def test__get_event_team_crews__unknown_event(self) -> None:
        """Returns a tool-level error for unknown events and a readable message in the content."""

        result = self.tool_call('get_event_team_crews', {
            'series': 'X',
            'year': 2009,
            'team_name': str(self.team_1),
        })
        self.assertTrue(result['isError'])


    def test__get_event_team_crews__unknown_team(self) -> None:
        """Returns a tool-level error for unknown teams and a readable message in the content."""

        result = self.tool_call('get_event_team_crews', {
            'series': self.event.series,
            'year': self.event.year,
            'team_name': 'Unknown',
        })
        self.assertTrue(result['isError'])


    def test__matches_public_json_api(self) -> None:
        """Returns data matching the API's team page response."""

        for day in self.event.days.all():
            self.team_1.purchases.create(
                day = day,
                crew = self.crew_mens,
                seat = exists(models.Seat.objects.first()),
            )

        result = self.tool_call('get_event_team_crews', {
            'series': self.event.series,
            'year': self.event.year,
            'team_name': str(self.team_1),
        })
        self.assertFalse(result['isError'])
        self.assertEqual(
            result['structuredContent'],
            self.get_api_json('team', {
                'event_tag': self.event.tag,
                'team_name': str(self.team_1),
            }),
        )
