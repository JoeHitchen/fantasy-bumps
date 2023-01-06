from datetime import datetime, date, timedelta
import logging
import re

import requests
import pytz

from . import common
from ..common import TORPIDS, club_parser
from ..anu import _roman_parser


logger = logging.getLogger('Anu')
logger.setLevel('INFO')


def _race_time_parser(day: date, div_header: str) -> datetime:
    """Extracts the division time from the division header data."""
    
    time_match = re.search(r'\((\d\d?)[:.](\d\d)\)', div_header)
    assert time_match
    hour_str, min_str = time_match.groups()[0:2]
    
    race_time = datetime.strptime('{} {}:{}'.format(day, hour_str, min_str), '%Y-%m-%d %H:%M')
    if race_time.hour < 9:
        race_time += timedelta(hours = 12)
    
    return pytz.timezone('Europe/London').localize(race_time)


def _get_datafile_url(series: str, day: date, gender: str, finish: bool) -> str:
    
    if series == TORPIDS and day.year == 2022:
        return 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/{}/{}{}{}{}.dat'.format(
            {'T': 'Torpids', 'E': 'Eights'}[series].lower(),
            series.lower(),
            day.strftime('%y'),
            'end' if finish else day.strftime('%a').lower(),
            gender.lower(),
        )
    
    else:
        return 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/{}{}{}{}.dat'.format(
            series.lower(),
            day.strftime('%y'),
            'end' if finish else day.strftime('%a').lower(),
            gender.lower(),
        )


def load_start_order(
    series: str,
    day: date,
    gender: str,
    finish: bool = False,
) -> common.StartOrder:
    """Retrieves the start order for a given race day and gender from Anu's data files."""
    logger.info('Retrieving results from Anu...\n  Options: {}, {}, {}, & {} '.format(
        series,
        day,
        gender,
        finish,
    ))
    
    # Get raw data
    url = _get_datafile_url(series, day, gender, finish)
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
        
        division: common.StartOrderDivision = {
            'gender': gender,
            'number': _roman_parser(div_number_match.groups()[0]),
            'race_time': _race_time_parser(day, div_header),
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
                club_parser(club_str.strip()),
                gender,
                crew_rank,
                division['finalised'] and '?' not in crew_str,
            ))
        
        divisions.append(division)
    
    return divisions

