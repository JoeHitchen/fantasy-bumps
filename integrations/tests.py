from unittest import TestCase
import json

from . import live_bumps, anu, ourcs, camfm
from .types import PositionMap
from .common import TORPIDS, EIGHTS, LENTS, MAYS


def load_expected_positions(series: str, year: int, day: int) -> PositionMap:
    """A helper to load expected positions from file."""
    
    series_tag = {TORPIDS: 'torpids', MAYS: 'mays'}.get(series)
    with open(f'integrations/expected_results/{series_tag}_{year}_day{day}.json') as file:
        raw = json.load(file)
    
    results = {}
    for crew_key, position in raw.items():
        crew_code = (crew_key[0:4], crew_key[5].upper(), int(crew_key[6]))
        results[crew_code] = (int(position), True)
    
    return results


class Test__LiveBumps(TestCase):
    
    def test__positions__torpids_2022(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = live_bumps.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__positions__smoke(self) -> None:
        """Positions from other historical events should be parsed without error."""
        
        events = [
            (TORPIDS, 2017, 134),
            (EIGHTS, 2017, 170),
            (TORPIDS, 2018, 134),
            (EIGHTS, 2018, 171),
            (TORPIDS, 2019, 134),
            (EIGHTS, 2019, 168),
            (TORPIDS, 2021, 128),
            (TORPIDS, 2022, 134),
            (EIGHTS, 2022, 168),
        ]
        
        for series, year, num_crews in events:
            with self.subTest([series, year]):
                
                positions = live_bumps.get_positions(series, year, 5)
                self.assertEqual(len(positions.keys()), num_crews)
    
    
    def test__crew_lists__smoke(self) -> None:
        """Crew lists from historical events should be parsed without error."""
        
        events = [
            (TORPIDS, 2017, 166),
            (EIGHTS, 2017, 177),
            (TORPIDS, 2018, 163),
            (EIGHTS, 2018, 174),
            (TORPIDS, 2019, 157),
            (EIGHTS, 2019, 169),
            (TORPIDS, 2021, 137),
            (TORPIDS, 2022, 164),
            (EIGHTS, 2022, 181),
        ]
        
        for series, year, num_crews in events:
            with self.subTest([series, year]):
                
                crew_lists = live_bumps.get_crew_lists(series, year)
                self.assertEqual(len(crew_lists.keys()), num_crews)


class Test__Anu(TestCase):
    
    def test__torpids_2022(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            # At time of writing, no pre-Covid start orders are available
            (TORPIDS, 2021, 128),
            (TORPIDS, 2022, 134),
            (EIGHTS, 2022, 168),
        ]
        
        for series, year, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    positions = anu.get_positions(series, year, day_number)
                    self.assertEqual(len(positions.keys()), num_crews)


class Test__OURCs(TestCase):
    
    def test__crew_lists__smoke(self) -> None:
        """Crew lists from historical events should be parsed without error."""
        
        events = [
            (TORPIDS, 2017, 166),
            (EIGHTS, 2017, 177),
            (TORPIDS, 2018, 163),
            (EIGHTS, 2018, 174),
            (TORPIDS, 2019, 157),
            (EIGHTS, 2019, 169),
            (TORPIDS, 2021, 137),
            (TORPIDS, 2022, 164),
            (EIGHTS, 2022, 181),
        ]
        
        for series, year, num_crews in events:
            with self.subTest([series, year]):
                
                crew_lists = ourcs.get_crew_lists(series, year)
                self.assertEqual(len(crew_lists.keys()), num_crews)


class Test__CamFM(TestCase):
    
    def test__mays_2019(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (MAYS, 2019, day)
                parsed = camfm.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            (LENTS, 2017, 120),
            (MAYS, 2017, 155),
            (LENTS, 2018, 120),
            (MAYS, 2018, 154),
            (LENTS, 2019, 120),
            (MAYS, 2019, 168),
            (LENTS, 2020, 120),
            (LENTS, 2022, 120),
        ]
        
        for series, year, num_crews in events:
            with self.subTest([series, year]):
                
                positions = camfm.get_positions(series, year, 5)
                self.assertEqual(len(positions.keys()), num_crews)

