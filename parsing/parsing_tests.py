import json

from django.test import TestCase, tag

from parsing import anu, camfm


@tag('external')
class Test__Anu(TestCase):
    
    cases = [
        # At time of writing, no pre-Covid start orders are available
        ('T', 2021, ['tue', 'wed', 'thu', 'fri', 'end'], 128),
        ('T', 2022, ['wed', 'thu', 'fri', 'sat', 'end'], 134),
    ]
    
    def test__anu(self):
        """Checks no errors are raised parsing all Anu's known start/finish orders."""
        
        for series, year, days, num_crews in self.cases:
            for day in days:
                
                with self.subTest((series, year, day)):
                    order = anu.get_start_order(series, year, day)
                    self.assertEqual(len(order.keys()), num_crews)


@tag('external')
class Test__CamFM(TestCase):
    
    @staticmethod
    def load_expected_positions(series, year, day):
        """A helper to load expected positions from file."""
        
        series_tag = {camfm.MAYS: 'mays'}.get(series)
        with open(f'parsing/expected_results/{series_tag}_{year}_day{day}.json') as file:
            raw = json.load(file)
        
        results = {}
        for crew_key, position in raw.items():
            crew_code = (crew_key[0:4], crew_key[5].upper(), int(crew_key[6]))
            results[crew_code] = int(position)
        
        return results
    
    
    def test__mays_2019(self):
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (camfm.MAYS, 2019, day)
                parsed = camfm.get_positions(*day_code)
                expected = self.load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])

