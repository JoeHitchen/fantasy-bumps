from unittest import TestCase
from unittest.mock import Mock, patch, call
from datetime import datetime
import json

import requests

from . import live_bumps, anu_html, anu_dat, ourcs, camfm
from .types import PositionMap, Division, StartOrder
from .common import TORPIDS, EIGHTS, LENTS, MAYS, MEN, WOMEN
from .common import gender_map, boat_code_parser, boat_code_map


def load_expected_start_order(series: str, year: int, day: int) -> StartOrder:
    """A helper to load expected start orders from file."""

    series_tag = {TORPIDS: 'torpids', MAYS: 'mays'}.get(series)
    filename = f'integrations/expected_results/{series_tag}_{year}_day{day}_start_order.json'
    with open(filename) as file:
        raw = json.load(file)
    
    divisions = []
    for item in raw:
        divisions.append(Division(
            gender = item['gender'],
            number = item['number'],
            race_time = datetime.strptime(item.pop('race_time'), '%H:%M').time(),
            size = item['size'],
            crews = [
                ((crew[0:4], crew[5].upper(), int(crew[6])), True)
                for crew in item.pop('crews')
            ],
            finalised = item['finalised'],
        ))
    
    return divisions


def load_expected_positions(series: str, year: int, day: int) -> PositionMap:
    """A helper to load expected positions from file."""
    
    series_tag = {TORPIDS: 'torpids', MAYS: 'mays'}.get(series)
    filename = f'integrations/expected_results/{series_tag}_{year}_day{day}_positions.json'
    with open(filename) as file:
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
    
    
    def test__start_orders__torpids_2022(self) -> None:
        """The start order given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = live_bumps.get_start_order(*day_code)
                expected = load_expected_start_order(*day_code)
                
                self.assertEqual(len(parsed), len(expected))
                for index, division in enumerate(parsed):
                    with self.subTest('{}Div{}'.format(division['gender'], division['number'])):
                        self.assertEqual(division, expected[index])
    
    
    def test__start_orders__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            (TORPIDS, 2017, 11, 134),
            (EIGHTS, 2017, 13, 170),
            (TORPIDS, 2018, 11, 134),
            (EIGHTS, 2018, 13, 171),
            (TORPIDS, 2019, 11, 134),
            (EIGHTS, 2019, 13, 168),
            (TORPIDS, 2021, 14, 128),
            (TORPIDS, 2022, 11, 134),
            (EIGHTS, 2022, 14, 168),
        ]
        
        for series, year, num_divs, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    start_order = live_bumps.get_start_order(series, year, day_number)
                    self.assertEqual(len(start_order), num_divs)
                    self.assertEqual(sum(len(div['crews']) for div in start_order), num_crews)
    
    
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
    
    
    @patch.object(requests, 'post')
    @patch('integrations.live_bumps.get_all_positions')
    def test__write_positions__updates(self, live_positions_mock: Mock, post_mock: Mock) -> None:
        """Writes all results for Torpids 2022."""
        
        all_positions = [load_expected_positions(TORPIDS, 2022, day) for day in range(1, 6)]
        with open('integrations/expected_results/torpids_2022_live_bumps.json') as file:
            expected_data = json.load(file)
        
        outcome = live_bumps.write_positions(TORPIDS, 2022, all_positions)
        self.assertEqual(outcome, (134, 0, 0))
        self.assertEqual(post_mock.call_count, 134)
        
        for club_code, club_data in expected_data.items():
            for gender, gender_data in club_data.items():
                for rank, crew_data in enumerate(gender_data, 1):
                    
                    crew_tuple = (boat_code_parser(club_code), gender[0].upper(), rank)
                    with self.subTest(crew = crew_tuple):
                        
                        self.assertIn(
                            call(
                                '{}/bump/torpids/2022'.format(live_bumps.BASE_URL),
                                headers = {
                                    'Authorization': live_bumps.AUTH_KEY,
                                    'Content-Type': 'application/json',
                                },
                                json = {
                                    'club': club_code,
                                    'gender': gender,
                                    'number': rank - 1,
                                    'moves': crew_data['moves'],
                                },
                            ),
                            post_mock.call_args_list,
                        )
    
    
    @patch.object(requests, 'post')
    @patch('integrations.live_bumps.get_all_positions')
    def test__write_positions__skips(self, live_positions_mock: Mock, post_mock: Mock) -> None:
        """Positions which are match the already live positions are not updated."""
        
        all_positions = [load_expected_positions(TORPIDS, 2022, day) for day in range(1, 6)]
        
        # Exclude four crews
        crews = [('lady', 'W', 1), ('newc', 'W', 2), ('wadh', 'M', 3), ('wolf', 'W', 4)]
        live_positions_mock.return_value = {}
        for day_positions in all_positions:
            for crew, position in day_positions.items():
                if crew not in crews:
                    continue
                if crew not in live_positions_mock.return_value:
                    live_positions_mock.return_value[crew] = []
                live_positions_mock.return_value[crew].append(position)
        
        
        outcome = live_bumps.write_positions(TORPIDS, 2022, all_positions)
        self.assertEqual(outcome, (130, 0, 4))
        self.assertEqual(post_mock.call_count, 130)
        
        for crew in crews:
            with self.subTest(crew = crew):
                
                crew_positions = [
                    position
                    for day_positions in all_positions
                    for itr_crew, position in day_positions.items()
                    if itr_crew == crew
                ]
                
                self.assertNotIn(
                    call(
                        '{}/bump/torpids/2022'.format(live_bumps.BASE_URL),
                        headers = {
                            'Authorization': live_bumps.AUTH_KEY,
                            'Content-Type': 'application/json',
                        },
                        json = {
                            'club': boat_code_map[crew[0]],
                            'gender': gender_map[crew[1]].lower(),
                            'number': crew[2] - 1,
                            'moves': live_bumps._positions_to_moves(crew_positions)['moves'],
                        },
                    ),
                    post_mock.call_args_list,
                )


class Test__Anu__HTML(TestCase):
    
    def test__start_orders__torpids_2022(self) -> None:
        """The start order given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu_html.get_start_order(*day_code)
                expected = load_expected_start_order(*day_code)
                
                self.assertEqual(len(parsed), len(expected))
                for index, division in enumerate(parsed):
                    with self.subTest('{}Div{}'.format(division['gender'], division['number'])):
                        self.assertEqual(division, expected[index])
    
    
    def test__start_orders__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            (TORPIDS, 2022, 11, 134),
            (EIGHTS, 2022, 14, 168),
            (TORPIDS, 2023, 12, 146),
        ]
        
        for series, year, num_divs, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    start_order = anu_html.get_start_order(series, year, day_number)
                    self.assertEqual(len(start_order), num_divs)
                    self.assertEqual(sum(len(div['crews']) for div in start_order), num_crews)
    
    
    def test__positions__torpids_2022(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu_html.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__postions__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            # At time of writing, no pre-Covid start orders are available
            (TORPIDS, 2022, 134),
            (EIGHTS, 2022, 168),
        ]
        
        for series, year, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    positions = anu_html.get_positions(series, year, day_number)
                    self.assertEqual(len(positions.keys()), num_crews)


class Test__Anu__Dat(TestCase):
    
    def test__start_orders__torpids_2022(self) -> None:
        """The start order given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu_dat.get_start_order(*day_code)
                expected = load_expected_start_order(*day_code)
                
                self.assertEqual(len(parsed), len(expected))
                for index, division in enumerate(parsed):
                    with self.subTest('{}Div{}'.format(division['gender'], division['number'])):
                        self.assertEqual(division, expected[index])
    
    
    def test__start_orders__smoke(self) -> None:
        """Checks that other historical events can be parsed without error."""
        
        events = [
            (TORPIDS, 2022, 11, 134),
            (EIGHTS, 2022, 14, 168),
            (TORPIDS, 2023, 12, 146),
        ]
        
        for series, year, num_divs, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    start_order = anu_dat.get_start_order(series, year, day_number)
                    self.assertEqual(len(start_order), num_divs)
                    self.assertEqual(sum(len(div['crews']) for div in start_order), num_crews)
    
    
    def test__start_orders_by_gender__torpids_2022(self) -> None:
        """The start order given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            for gender in [MEN, WOMEN]:
                with self.subTest(day = day, gender = gender):
                    
                    day_code = (TORPIDS, 2022, day)
                    parsed = anu_dat.get_start_order_by_gender(
                        day_code[0],
                        day_code[1],
                        gender,
                        day_code[2],
                    )
                    expected = [
                        div for div in load_expected_start_order(*day_code)
                        if div['gender'] == gender
                    ]
                    
                    for index, div in enumerate(parsed):
                        with self.subTest('{}Div{}'.format(div['gender'], div['number'])):
                            self.assertEqual(div, expected[index])
    
    
    def test__positions__torpids_2022(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (TORPIDS, 2022, day)
                parsed = anu_dat.get_positions(*day_code)
                expected = load_expected_positions(*day_code)
                
                for crew in parsed.keys():
                    with self.subTest(crew = crew):
                        self.assertEqual(parsed[crew], expected[crew])
    
    
    def test__positions__smoke(self) -> None:
        """Positions from other historical events should be parsed without error."""
        
        events = [
            (TORPIDS, 2022, 134),
            (EIGHTS, 2022, 168),
            (TORPIDS, 2023, 146),
        ]
        
        for series, year, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    positions = anu_dat.get_positions(series, year, day_number)
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
    
    
    def test__start_orders__mays_2019(self) -> None:
        """The positions given by the parser should match the expected results."""
        
        for day in [1, 2, 5]:
            with self.subTest(day = day):
                
                day_code = (MAYS, 2019, day)
                parsed = camfm.get_start_order(*day_code)
                expected = load_expected_start_order(*day_code)
                
                self.assertEqual(len(parsed), len(expected))
                for index, division in enumerate(parsed):
                    with self.subTest('{}Div{}'.format(division['gender'], division['number'])):
                        self.assertEqual(division, expected[index])
    
    
    def test__start_orders__smoke(self) -> None:
        """Checks that other historical events can be retrieved without error."""
        
        events = [
            (MAYS, 2017, 9, 155),
            (MAYS, 2018, 9, 154),
            (MAYS, 2019, 11, 168),
        ]
        
        for series, year, num_divs, num_crews in events:
            for day_number in range(1, 6):
                with self.subTest([series, year, day_number]):
                    
                    start_order = camfm.get_start_order(series, year, day_number)
                    self.assertEqual(len(start_order), num_divs)
                    self.assertEqual(sum(len(div['crews']) for div in start_order), num_crews)

