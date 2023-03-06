import logging
import re

import requests

from .types import PositionMap, Division, StartOrder
from .common import series_text_map, MEN, WOMEN, gender_map
from .common import roman_parser, race_time_parser, club_parser, start_order_to_positions
from . import magic

logger = logging.getLogger(__name__)
BASE_URL = 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/'


def load_start_order_by_gender(
    series: str,
    year: int,
    gender: str,
    day_number: int,
) -> StartOrder:
    """Retrieves the start order for a given race day and gender from Anu's .dat files."""
    logger.info("Retrieving {}'s start order for {} {} (day {}) from Anu .dat".format(
        gender_map[gender].lower(),
        series_text_map[series],
        year,
        day_number,
    ))
    
    # Get raw data
    response = requests.get(BASE_URL + magic.anu_data_url_template(series, year).format(
        series_text_map[series].lower(),
        series.lower(),
        str(year)[2:4],
        magic.anu_day_code(series, year, day_number),
        gender.lower(),
    ))
    if not response.ok:
        response.raise_for_status()
    
    data = response.text.split('\n')
    data = [line for line in data if line.strip()]
    
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
            'number': roman_parser(div_number_match.groups()[0]),
            'race_time': race_time_parser(div_header),
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
                crew_rank = roman_parser(crew_match.groups()[1])
            
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
    divisions.sort(key = lambda div: div['race_time'])
    
    logger.info("Retrieved {} {}'s divisions and {} crews for {} {} (day {}) from Anu .dat".format(
        len(divisions),
        gender_map[gender].lower(),
        sum(len(division['crews']) for division in divisions),
        series_text_map[series],
        year,
        day_number,
    ))
    return divisions


def get_start_order(series: str, year: int, day_number: int) -> StartOrder:
    """Retrieves the day's start order from Anu's .dat files."""
    
    return sorted([
        *load_start_order_by_gender(series, year, MEN, day_number),
        *load_start_order_by_gender(series, year, WOMEN, day_number),
    ], key = lambda div: div['race_time'])


def get_positions_by_gender(series: str, year: int, gender: str, day_number: int) -> PositionMap:
    """Generates a crew/position map for one gender from Anu's .dat files."""
    
    return start_order_to_positions(load_start_order_by_gender(series, year, gender, day_number))


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from Anu's .dat files."""
    
    return start_order_to_positions(get_start_order(series, year, day_number))

