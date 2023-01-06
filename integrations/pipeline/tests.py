from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch, call
import json
import os

import requests

from . import anu, live
from ..types import PositionMap
from ..common import TORPIDS, MEN, WOMEN, boat_code_parser
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
                    for div_crew in division['crews']:
                        ranks[div_crew[1]] += 1
                        parsed[(div_crew[0], div_crew[1], div_crew[2])] = ranks[div_crew[1]]
                
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


class Test__Live_Bumps(TestCase):
    
    @patch.object(requests, 'post')
    def test__(self, post_mock: Mock) -> None:
        
        all_positions = [load_expected_positions(TORPIDS, 2022, day) for day in range(1, 6)]
        all_positions_with_status = [
            {crew: (position, True) for crew, position in day_positions.items()}
            for day_positions in all_positions
        ]
        
        live.post_all_rankings(TORPIDS, 2022, all_positions_with_status)
        
        self.assertEqual(post_mock.call_count, 134)
        with open('integrations/expected_results/torpids_2022_live_bumps.json') as file:
            target_data = json.load(file)
        
        for club_code, club_data in target_data.items():
            for gender, gender_data in club_data.items():
                for rank, crew_data in enumerate(gender_data, 1):
                    crew_tuple = (boat_code_parser(club_code), gender[0].upper(), rank)
                    with self.subTest(crew = crew_tuple):
                        self.assertIn(
                            call(
                                'https://{}/bump/torpids/2022'.format((
                                    os.environ.get('LIVE_BUMPS_HOST')
                                )),
                                json = {
                                    'club': club_code,
                                    'gender': gender,
                                    'number': rank - 1,
                                    'moves': crew_data['moves'],
                                },
                                headers = {
                                    'Authorization': os.environ.get('LIVE_BUMPS_KEY', ''),
                                    'Content-Type': 'application/json',
                                },
                            ),
                            post_mock.call_args_list,
                        )

