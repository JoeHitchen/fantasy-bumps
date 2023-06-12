from datetime import date, time
from typing import List

from django.test import TestCase

from integrations.types import StartOrder, Division, Crew

from ..constants import Series, Genders
from . import actions


def make_division(gender: Genders, size: int, race_time: time, crews: List[Crew]) -> Division:
    return {
        'gender': gender,
        'number': 0,
        'race_time': race_time,
        'size': size,
        'crews': [(crew, True) for crew in crews],
        'finalised': True,
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

