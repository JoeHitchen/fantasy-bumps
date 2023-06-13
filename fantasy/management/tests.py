from datetime import date, time, datetime, timedelta
from unittest.mock import patch, Mock, call
from typing import List

from django.test import TestCase
from django.db import models as db
from django.utils import timezone

from integrations.types import StartOrder, Division, Crew

from ..constants import Series, Clubs, Genders
from .. import models
from . import actions


PositionsMap = dict[models.Crew.Tuple, int]


def make_division(gender: Genders, size: int, race_time: time, crews: List[Crew]) -> Division:
    return {
        'gender': gender,
        'number': 0,
        'race_time': race_time,
        'size': size,
        'crews': [(crew, True) for crew in crews],
        'finalised': True,
    }


def dummy_positions_by_gender(
    series: str,
    year: int,
    gender: Genders,
    day_number: int,
) -> PositionsMap:
    return {
        (Clubs.HERT, gender, 1): day_number + 1,
        (Clubs.LADY, gender, 1): day_number + 2,
    }


class Test__EventCreation(TestCase):
    
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
    
    start_order: StartOrder = [
        make_division(Genders.MEN, 2, time(13, 00), mens_ranking[2:4]),
        make_division(Genders.WOMEN, 4, time(13, 30), womens_ranking[4:8]),
        make_division(Genders.MEN, 3, time(11, 55), mens_ranking[4:7]),
        make_division(Genders.WOMEN, 5, time(12, 30), womens_ranking[8:13]),
        make_division(Genders.MEN, 2, time(14, 30), mens_ranking[0:2]),
        make_division(Genders.WOMEN, 4, time(14, 00), womens_ranking[0:4]),
    ]
    
    
    def test__torpids(self) -> None:
        """Creates a Torpids event correct orders & separates divisions."""
        
        event = actions.create_event(Series.TORPIDS, 2023, date(2023, 3, 22), self.start_order)
        
        self.assertEqual(event.series, Series.TORPIDS)
        self.assertEqual(event.year, 2023)
        self.assertEqual(event.mens_division_sizes, [2, 2, 3])
        self.assertEqual(event.womens_division_sizes, [4, 4, 5])
        
        self.assertEqual(event.days.count(), 5)
        self.assertQuerySetEqual(
            event.days.values_list('first_race_time', flat = True),
            [time(11, 55), time(11, 55), time(11, 55), time(11, 55), None],
        )
        self.assertQuerySetEqual(
            event.days.values_list('last_race_time', flat = True),
            [time(14, 30), time(14, 30), time(14, 30), time(14, 30), None],
        )
        
        self.assertEqual(event.first_day.ranking.count(), 20)
        mens_positions = {crew: rank for rank, crew in enumerate(self.mens_ranking, start = 1)}
        womens_positions = {crew: rank for rank, crew in enumerate(self.womens_ranking, start = 1)}
        self.assertDictEqual(
            {ranking.crew.as_tuple(): ranking.rank for ranking in event.first_day.ranking.all()},
            {**mens_positions, **womens_positions},
        )
    
    
    def test__eights(self) -> None:
        """Creates a Summer Eights event and applies a Saturday race time shift."""
        
        event = actions.create_event(Series.EIGHTS, 2023, date(2023, 3, 22), self.start_order)
        
        self.assertEqual(event.series, Series.EIGHTS)
        self.assertEqual(event.year, 2023)
        self.assertEqual(event.mens_division_sizes, [2, 2, 3])
        self.assertEqual(event.womens_division_sizes, [4, 4, 5])
        
        self.assertEqual(event.days.count(), 5)
        self.assertQuerySetEqual(
            event.days.values_list('first_race_time', flat = True),
            [time(11, 55), time(11, 55), time(11, 55), time(10, 55), None],
        )
        self.assertQuerySetEqual(
            event.days.values_list('last_race_time', flat = True),
            [time(14, 30), time(14, 30), time(14, 30), time(13, 30), None],
        )
        
        self.assertEqual(event.first_day.ranking.count(), 20)
        mens_positions = {crew: rank for rank, crew in enumerate(self.mens_ranking, start = 1)}
        womens_positions = {crew: rank for rank, crew in enumerate(self.womens_ranking, start = 1)}
        self.assertDictEqual(
            {ranking.crew.as_tuple(): ranking.rank for ranking in event.first_day.ranking.all()},
            {**mens_positions, **womens_positions},
        )


class Test__LiveBumps(TestCase):
    
    event: models.Event
    dummy_positions_by_day: list[PositionsMap]
    now: datetime
    
    @classmethod
    def setUpTestData(cls) -> None:
    
        cls.now = timezone.localtime(timezone.now())
        
        cls.event = models.Event.objects.create(
            series = Series.TORPIDS,
            year = cls.now.year,
            tag = f'{Series.TORPIDS.label.lower()}{cls.now.year}',
        )
        actions.create_days(cls.event, cls.now.date(), time(12, 00), time(18, 30))
        
        cls.dummy_positions_by_day = [dummy_positions_by_gender(
            cls.event.series,
            cls.event.year,
            Genders.WOMEN,
            day_number,
        ) for day_number in range(1, 6)]
    
    
    @patch('integrations.anu_dat.get_positions_by_gender')
    def test__update__before_first_day(self, positions_mock: Mock) -> None:
        """No action is taken before the first day."""
        
        self.event.days.update(date = db.F('date') + timedelta(1))
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        positions_mock.assert_not_called()
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__first_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(self.event.series, self.event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 3)
            ],
        )
        start_order_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            Genders.WOMEN,
            1,
        )
        write_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            self.dummy_positions_by_day[:2],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__second_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        self.event.days.update(date = db.F('date') - timedelta(1))
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(self.event.series, self.event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 4)
            ],
        )
        start_order_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            Genders.WOMEN,
            2,
        )
        write_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            self.dummy_positions_by_day[:3],
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__final_day(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the next day, current day, and all previous days."""
        
        self.event.days.update(date = db.F('date') - timedelta(3))
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(self.event.series, self.event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
        start_order_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            Genders.WOMEN,
            4,
        )
        write_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            self.dummy_positions_by_day,
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__after_event(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Positions are processed for the whole event after it has finished."""
        
        self.event.days.update(date = db.F('date') - timedelta(4))
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        self.assertEqual(
            positions_mock.call_args_list,
            [
                call(self.event.series, self.event.year, Genders.WOMEN, day_number)
                for day_number in range(1, 6)
            ],
        )
        start_order_mock.assert_not_called()
        write_mock.assert_called_once_with(
            self.event.series,
            self.event.year,
            self.dummy_positions_by_day,
        )
    
    
    @patch('integrations.live_bumps.write_positions')
    @patch('integrations.anu_dat.get_start_order_by_gender')
    @patch('integrations.anu_dat.get_positions_by_gender', side_effect = dummy_positions_by_gender)
    def test__update__racetime_filter(
        self,
        positions_mock: Mock,
        start_order_mock: Mock,
        write_mock: Mock,
    ) -> None:
        """Crews that have not raced on the current day are masked from the Live Bumps update."""
        
        start_order_mock.return_value = [
            {
                'race_time': (self.now - timedelta(minutes = 2)).time(),
                'crews': [((Clubs.HERT, Genders.WOMEN, 1), None)],
            },
            {
                'race_time': (self.now + timedelta(minutes = 2)).time(),
                'crews': [((Clubs.LADY, Genders.WOMEN, 1), None)],
            },
        ]
        
        self.event.days.update(date = db.F('date') - timedelta(1))
        actions.update_live_bumps(self.event, Genders.WOMEN)
        
        expected_positions = self.dummy_positions_by_day[:3]
        expected_positions[-1].pop((Clubs.LADY, Genders.WOMEN, 1))
        write_mock.assert_called_once_with(self.event.series, self.event.year, expected_positions)

