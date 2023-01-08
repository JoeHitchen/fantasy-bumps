from datetime import date, timedelta
from unittest import TestCase

from . import anu
from ..types import PositionMap
from ..common import TORPIDS, MEN, WOMEN
from ..tests import load_expected_positions


class Test__Anu(TestCase):
    
    def test__positions__torpids_2022(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                
                start_order_men = anu.load_start_order(
                    day_code[0],
                    date(day_code[1], 3, 1) + timedelta(day),
                    MEN,
                    day == 5,
                )
                start_order_women = anu.load_start_order(
                    day_code[0],
                    date(day_code[1], 3, 1) + timedelta(day),
                    WOMEN,
                    day == 5,
                )
                ranks = {MEN: 0, WOMEN: 0}
                parsed: PositionMap = {}
                for division in start_order_men + start_order_women:
                    for div_crew, _ in division['crews']:
                        ranks[div_crew[1]] += 1
                        parsed[(*div_crew[0:3],)] = (ranks[div_crew[1]], True)
                
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__positions__smoke(self) -> None:
        """Checks no errors are raised parsing all Anu's known start/finish order data files."""
        
        event_days = [
            (TORPIDS, '2022-03-02', False),
            (TORPIDS, '2022-03-03', False),
            (TORPIDS, '2022-03-04', False),
            (TORPIDS, '2022-03-05', False),
            (TORPIDS, '2022-03-06', True),
        ]
        
        for day in event_days:
            
            event_date = date.fromisoformat(day[1])
            mens_args = (day[0], event_date, MEN, day[2])
            womens_args = (day[0], event_date, WOMEN, day[2])
        
            with self.subTest(call_args = mens_args):
                anu.load_start_order(*mens_args)
            
            with self.subTest(call_args = womens_args):
                anu.load_start_order(*womens_args)


