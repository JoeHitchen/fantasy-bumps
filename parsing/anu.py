import re

from bs4 import BeautifulSoup
import requests

from .common import club_parser

BASE_URL = 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/'


def _roman_parser(numerals):
    return {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}.get(numerals)


def _parse_division(table):
    rows = re.split('<tr>', str(table))
    
    division_match = re.search(
        '<th colspan="2"> (?P<gender>Men|Women)\'s Div (?P<num>[IV]{1,3})',
        rows[1],
    )
    
    gender = division_match.group('gender')[0]
    division = _roman_parser(division_match.group('num'))
    
    start_order = []
    for row in rows[2:]:
        url_pattern = BASE_URL + 'bumps/[a-z]{4}/(?P<club>[a-z]{4})_[mw](?P<rank>[0-9])'
        full_pattern = '(?P<bungline>[0-9]{{1,2}}). .*<td> <a href="{}'.format(url_pattern)
        bungline_match = re.search(full_pattern, row)
        start_order.append((
            int(bungline_match.group('bungline')),
            club_parser(bungline_match.group('club')),
            _roman_parser(bungline_match.group('rank')) or 1,
        ))
    
    return (gender, division, start_order)


def _convert_divisions_to_ranking(divisions, gender):
    
    gendered_divisions = [div for div in divisions if div[0] == gender]
    gendered_divisions.sort(key = lambda div: div[1])
    
    crews = {}
    prev_lowest_bungline = 0
    for (_, _, start_order) in gendered_divisions:
        
        for bungline, club, rank in start_order:
            crews[(club, gender, rank)] = prev_lowest_bungline + bungline
        
        prev_lowest_bungline += bungline
    
    return crews


def get_start_order(series, year, day):
    
    url = BASE_URL + '{}/{}{}{}.html'.format(
        {'T': 'torpids', 'E': 'eights'}[series],
        series.lower(),
        str(year)[-2:],
        day,
    )
    response = requests.get(url)
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    divisions = []
    for table in soup.find_all('table')[2:]:
        
        if table.string is not None:
            continue
        divisions.append(_parse_division(table))
    
    mens_positions = _convert_divisions_to_ranking(divisions, 'M')
    womens_positions = _convert_divisions_to_ranking(divisions, 'W')
    
    return {**mens_positions, **womens_positions}

