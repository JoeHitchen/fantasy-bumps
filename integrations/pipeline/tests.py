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
                
                start_order_men = anu.load_start_order_by_gender(TORPIDS, 2022, MEN, day)
                start_order_women = anu.load_start_order_by_gender(TORPIDS, 2022, WOMEN, day)
                
                ranks = {MEN: 0, WOMEN: 0}
                parsed: PositionMap = {}
                for division in start_order_men + start_order_women:
                    for div_crew, _ in division['crews']:
                        ranks[div_crew[1]] += 1
                        parsed[(*div_crew[0:3],)] = (ranks[div_crew[1]], True)
                
                expected = load_expected_positions(TORPIDS, 2022, day)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__positions__smoke(self) -> None:
        """Positions from other historical events should be parsed without error."""
        
        events = [
            # At time of writing, only one start order is available
            (TORPIDS, 2022, 134),
        ]
        
        for series, year, num_crews in events:
            for day in range(1, 6):
                
                with self.subTest([series, year, MEN, day]):
                    anu.load_start_order_by_gender(series, year, MEN, day)
                
                with self.subTest([series, year, WOMEN, day]):
                    anu.load_start_order_by_gender(series, year, WOMEN, day)

