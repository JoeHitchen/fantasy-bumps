from datetime import date, time

from django.test import TestCase
from django.contrib.auth import models as auth

from integrations.types import Division, Crew, StartOrder
from core.tests import exists

from ..constants import Series, Genders
from .. import models
from .actions import create_event
from .trophies import assign_new_veterans, award_trophies


mens_ranking = [
    ('chri', 'M', 1),
    ('wolf', 'M', 1),
    ('sedm', 'M', 1),
    ('newc', 'M', 1),
    ('pemb', 'M', 2),
    ('hert', 'M', 2),
    ('wolf', 'M', 4),
]
womens_ranking = [
    ('univ', 'W', 1),
    ('wolf', 'W', 1),
    ('wadh', 'W', 1),
    ('lady', 'W', 1),
    ('newc', 'W', 1),
    ('hert', 'W', 1),
    ('wolf', 'W', 2),
    ('scat', 'W', 1),
    ('worc', 'W', 1),
    ('worc', 'W', 2),
    ('wolf', 'W', 3),
    ('newc', 'W', 2),
    ('wolf', 'W', 4),
]


def make_division(gender: Genders, size: int, race_time: time, crews: list[Crew]) -> Division:
    return {
        'gender': gender,
        'number': 0,
        'race_time': race_time,
        'size': size,
        'crews': [(crew, True) for crew in crews],
        'finalised': True,
    }


start_order: StartOrder = [
    make_division(Genders.MEN, 2, time(13, 00), mens_ranking[2:4]),
    make_division(Genders.WOMEN, 4, time(13, 30), womens_ranking[4:8]),
    make_division(Genders.MEN, 3, time(11, 55), mens_ranking[4:7]),
    make_division(Genders.WOMEN, 5, time(12, 30), womens_ranking[8:13]),
    make_division(Genders.MEN, 2, time(14, 30), mens_ranking[0:2]),
    make_division(Genders.WOMEN, 4, time(14, 00), womens_ranking[0:4]),
]


class Test__VeteranStatus(TestCase):
    fixtures = ['dev_team']

    team: models.Team
    event: models.Event

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = models.Team.objects.get(user__username = 'DevTeam')

        for event_num in range(0, 5):
            year = 2015 + event_num
            event = create_event(
                series = Series.TORPIDS if event_num % 2 else Series.EIGHTS,
                year = year,
                start_date = date(year, 5, 25),
                start_order = start_order,
            )
            event.fantasies.create(team = cls.team)

        cls.event = exists(models.Event.objects.last())


    def test__assign_veterans__all_new_veterans(self) -> None:
        """Players who have entered enough events are granted veteran status."""

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 1)

        self.team.refresh_from_db()
        self.assertTrue(self.team.oxford_veteran)
        self.assertFalse(self.team.cambridge_veteran)


    def test__assign_veterans__existing_veteran(self) -> None:
        """Players who already have veteran status are ignored."""

        self.team.oxford_veteran = True
        self.team.save()

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 0)

        self.team.refresh_from_db()
        self.assertTrue(self.team.oxford_veteran)
        self.assertFalse(self.team.cambridge_veteran)


    def test__assign_veterans__not_enough_entries(self) -> None:
        """Players who do not have enough entries are not granted veteran status."""

        exists(self.team.entries.last()).delete()

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 0)

        self.team.refresh_from_db()
        self.assertFalse(self.team.oxford_veteran)
        self.assertFalse(self.team.cambridge_veteran)


    def test__assign_veterans__wrong_location(self) -> None:
        """Entries do not count towards the quota if they are from the Other Place."""

        event = exists(models.Event.objects.first())
        event.series = Series.MAYS
        event.save()

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 0)

        self.team.refresh_from_db()
        self.assertFalse(self.team.oxford_veteran)
        self.assertFalse(self.team.cambridge_veteran)


    def test__assign_veterans__cambridge(self) -> None:
        """Cambridge Veteran status is assigned to those meeting the criteria for their events."""

        for event in models.Event.objects.all():
            event.series = Series.MAYS if event.series == Series.EIGHTS else Series.LENTS
            event.save()

        self.event.refresh_from_db()

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 1)

        self.team.refresh_from_db()
        self.assertFalse(self.team.oxford_veteran)
        self.assertTrue(self.team.cambridge_veteran)


    def test__assign_veterans__multiple_new_veterans(self) -> None:
        """Multiple players will be granted veteran status if they meet the criteria."""

        other_team_1 = auth.User.objects.create_user(username = 'Other Team 1').team
        other_team_2 = auth.User.objects.create_user(username = 'Other Team 2').team
        for event in models.Event.objects.all():
            event.fantasies.create(team = other_team_1)
            event.fantasies.create(team = other_team_2)

        new_veterans = assign_new_veterans(self.event)
        self.assertEqual(new_veterans, 3)

        self.team.refresh_from_db()
        self.assertTrue(self.team.oxford_veteran)
        self.assertFalse(self.team.cambridge_veteran)

        other_team_1.refresh_from_db()
        self.assertTrue(other_team_1.oxford_veteran)
        self.assertFalse(other_team_1.cambridge_veteran)

        other_team_2.refresh_from_db()
        self.assertTrue(other_team_2.oxford_veteran)
        self.assertFalse(other_team_2.cambridge_veteran)


class Test__EventTrophies(TestCase):
    fixtures = ['dev_event', 'dev_days']

    event: models.Event
    teams: list[models.GameEntry]

    def compare_trophies(
            self,
            team: models.GameEntry,
            trophies: list[models.Trophy.Types],
    ) -> None:
        self.assertEqual(list(team.team.trophies.values_list('type', flat = True)), trophies)


    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = models.Event.objects.get(tag = 'devgame')

        cls.teams = []
        for i in range(0, 6):
            team = auth.User.objects.create_user(f'Player {i + 1}').team

            budgets = 1500 - 10 * i
            cls.teams.append(cls.event.fantasies.create(
                team = team,
                mens_budget = budgets,
                womens_budget = budgets,
            ))


    def test__simple_ordering(self) -> None:
        """The prizes are awarded in the order of budgets."""

        award_trophies(self.event)

        self.compare_trophies(self.teams[0], [
            models.Trophy.Types.GOLDEN_SWAN,
            models.Trophy.Types.GOLDEN_COB,
            models.Trophy.Types.GOLDEN_PEN,
        ])
        self.compare_trophies(self.teams[1], [models.Trophy.Types.SILVER_SWAN])
        self.compare_trophies(self.teams[2], [models.Trophy.Types.BRONZE_SWAN])
        self.compare_trophies(self.teams[3], [])
        self.compare_trophies(self.teams[4], [])
        self.compare_trophies(self.teams[5], [])


    def test__mixed_up_ordering(self) -> None:
        """The Golden Cob & Golden Pen do not always go to the overall winner."""

        self.teams[4].womens_budget = 1510
        self.teams[4].save()
        self.teams[5].mens_budget = 1535
        self.teams[5].save()

        award_trophies(self.event)

        self.compare_trophies(self.teams[0], [models.Trophy.Types.GOLDEN_SWAN])
        self.compare_trophies(self.teams[1], [models.Trophy.Types.BRONZE_SWAN])
        self.compare_trophies(self.teams[2], [])
        self.compare_trophies(self.teams[3], [])
        self.compare_trophies(self.teams[4], [models.Trophy.Types.GOLDEN_PEN])
        self.compare_trophies(self.teams[5], [
            models.Trophy.Types.SILVER_SWAN,
            models.Trophy.Types.GOLDEN_COB,
        ])

