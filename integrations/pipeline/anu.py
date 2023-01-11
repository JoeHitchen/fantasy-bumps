from datetime import time
import logging
import re

import requests

from ..types import PositionMap, Division, StartOrder
from ..common import TORPIDS, MEN, WOMEN, club_parser
from ..anu import _roman_parser


logger = logging.getLogger('Anu')
logger.setLevel('INFO')


def _race_time_parser(div_header: str) -> time:
    """Extracts the division time from the division header data."""
    
    time_match = re.search(r'\((\d\d?)[:.](\d\d)\)', div_header)
    assert time_match
    hour_str, min_str = time_match.groups()[0:2]
    return time(int(hour_str), int(min_str))


def __start_order_to_positions(start_order: StartOrder) -> PositionMap:
    """Converts a start order to a set of positions."""
    
    rank = 0
    positions = {}
    for division in start_order:
        for crew, status in division['crews']:
            rank += 1
            positions[crew] = (rank, status)
    
    return positions


def _get_datafile_url(series: str, year: int, gender: str, day_number: int) -> str:
    
    # Get day string map
    if (series, year) == (TORPIDS, 2021):
        day_map = ['tue', 'wed', 'thu', 'fri', 'end']
    else:
        day_map = ['wed', 'thu', 'fri', 'sat', 'end']
    
    # Generate URL
    if series == TORPIDS and year == 2022:
        return 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/{}/{}{}{}{}.dat'.format(
            {'T': 'Torpids', 'E': 'Eights'}[series].lower(),
            series.lower(),
            str(year)[2:4],
            day_map[day_number - 1],
            gender.lower(),
        )
    
    else:
        return 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/{}{}{}{}.dat'.format(
            series.lower(),
            str(year)[2:4],
            day_map[day_number - 1],
            gender.lower(),
        )


def load_start_order_by_gender(
    series: str,
    year: int,
    gender: str,
    day_number: int,
) -> StartOrder:
    """Retrieves the start order for a given race day and gender from Anu's data files."""
    logger.info('Retrieving results from Anu...\n  Options: {}, {}, {}, & {} '.format(
        series,
        year,
        gender,
        day_number,
    ))
    
    # Get raw data
    url = _get_datafile_url(series, year, gender, day_number)
    response = requests.get(url)
    if not response.ok:
        response.raise_for_status()
    
    data = response.text.split('\n')
    
    # Parse header
    event = data.pop(0)  # noqa: 841
    num_div_match = re.search(r'(\d) div', data.pop(0))
    assert num_div_match
    number_of_divisions = int(num_div_match.groups()[0])
    
    # Parse divisions in turn
    divisions = []
    for _i in range(number_of_divisions):
        
        # Parses division rows
        div_header = data.pop(0)
        div_number_match = re.search('([IV]+)', div_header)
        div_size_match = re.search(r'(\d{1,2}) crews', div_header)
        assert div_number_match and div_size_match
        
        division: Division = {
            'gender': gender,
            'number': _roman_parser(div_number_match.groups()[0]),
            'race_time': _race_time_parser(div_header),
            'size': int(div_size_match.groups()[0]),
            'finalised': '?' not in div_header,
            'crews': [],
        }
        
        # Parses crews and results
        for _j in range(division['size']):
            crew_str = data.pop(0).strip()
            
            if crew_str[-1] in ['I', 'V']:
                crew_match = re.search("([A-Za-z'. ]+) ([IV]+)", crew_str)
                assert crew_match
                
                club_str = crew_match.groups()[0]
                crew_rank = _roman_parser(crew_match.groups()[1])
            
            else:
                crew_match = re.search("([A-Za-z'. ]+)", crew_str)
                assert crew_match
                
                club_str = crew_match.groups()[0]
                crew_rank = 1
            
            division['crews'].append((
                (club_parser(club_str.strip()), gender, crew_rank),
                division['finalised'] and '?' not in crew_str,
            ))
        
        divisions.append(division)
    
    return divisions


def get_positions_by_gender(series: str, year: int, gender: str, day_number: int) -> PositionMap:
    """Generates a crew/position map for one gender from Anu's .dat files."""
    
    return __start_order_to_positions(load_start_order_by_gender(series, year, gender, day_number))


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from Anu's .dat files."""
    
    return {
        **get_positions_by_gender(series, year, MEN, day_number),
        **get_positions_by_gender(series, year, WOMEN, day_number),
    }

