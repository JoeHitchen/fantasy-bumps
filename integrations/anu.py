from typing import List, Tuple
import logging
import re

from bs4 import BeautifulSoup
import requests

from .types import PositionMap
from .common import club_parser, TORPIDS, series_text_map, MEN, WOMEN

logger = logging.getLogger(__name__)
BASE_URL = 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/'

Bungline = Tuple[int, str, int]
Division = Tuple[str, int, List[Bungline]]


def _roman_parser(numerals: str) -> int:
    """Maps roman numerals to integers."""
    return {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}[numerals]


def _parse_division(table: str) -> Division:
    rows = re.split('<tr>', str(table))
    
    division_match = re.search(
        '<th colspan="2"> (?P<gender>Men|Women)\'s Div (?P<num>[IV]{1,3})',
        rows[1],
    )
    assert division_match
    
    gender = division_match.group('gender')[0]
    division = _roman_parser(division_match.group('num'))
    
    start_order = []
    for row in rows[2:]:
        
        url_pattern = BASE_URL + 'bumps/[a-z]{4}/(?P<club>[a-z]{4})_[mw](?P<rank>[0-9])'
        full_pattern = '(?P<bungline>[0-9]{{1,2}}). .*<td> <a href="{}'.format(url_pattern)
        bungline_match = re.search(full_pattern, row)
        assert bungline_match
        
        start_order.append((
            int(bungline_match.group('bungline')),
            club_parser(bungline_match.group('club')),
            int(bungline_match.group('rank')),
        ))
    
    return (gender, division, start_order)


def _convert_divisions_to_ranking(divisions: List[Division], gender: str) -> PositionMap:
    
    gendered_divisions = [div for div in divisions if div[0] == gender]
    gendered_divisions.sort(key = lambda div: div[1])
    
    crews = {}
    prev_lowest_bungline = 0
    for (_, _, start_order) in gendered_divisions:
        
        for bungline, club, rank in start_order:
            crews[(club, gender, rank)] = prev_lowest_bungline + bungline
        
        prev_lowest_bungline += bungline
    
    return crews


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from Anu's records."""
    
    series_text = series_text_map[series]
    logger.info('Retrieving crew positions for {} {} (day {}) from Anu'.format(
        series_text,
        year,
        day_number,
    ))
    
    # Map days of historical events
    if (series, year) == (TORPIDS, 2021):
        day_map = ['tue', 'wed', 'thu', 'fri', 'end']
    else:
        day_map = ['wed', 'thu', 'fri', 'sat', 'end']
    
    
    # Load page into parser
    response = requests.get(BASE_URL + '{}/{}{}{}.html'.format(
        series_text.lower(),
        series.lower(),
        str(year)[-2:],
        day_map[day_number - 1],
    ))
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    
    # Extract crew positions
    divisions = []
    for table in soup.find_all('table')[2:]:
        if table.string is not None:
            continue
        
        divisions.append(_parse_division(table))
    
    positions = {
        **_convert_divisions_to_ranking(divisions, MEN),
        **_convert_divisions_to_ranking(divisions, WOMEN),
    }
    logger.info('Retrieved {} crew positions for {} {} (day {}) from Anu'.format(
        len(positions),
        series_text,
        year,
        day_number,
    ))
    return positions

