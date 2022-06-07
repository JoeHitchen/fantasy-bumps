import json

from django.test import TestCase, tag

from parsing import anu, camfm

from .common import TORPIDS, EIGHTS, LENTS, MAYS


def load_expected_positions(series, year, day):
    """A helper to load expected positions from file."""
    
    series_tag = {TORPIDS: 'torpids', MAYS: 'mays'}.get(series)
    with open(f'parsing/expected_results/{series_tag}_{year}_day{day}.json') as file:
        raw = json.load(file)
    
    results = {}
    for crew_key, position in raw.items():
        crew_code = (crew_key[0:4], crew_key[5].upper(), int(crew_key[6]))
        results[crew_code] = int(position)
    
    return results


@tag('external')
class Test__Anu(TestCase):
    
    def test__torpids_2022(self):
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__smoke(self):
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


@tag('external')
class Test__CamFM(TestCase):
    
    def test__mays_2019(self):
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (MAYS, 2019, day)
                parsed = camfm.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__smoke(self):
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

