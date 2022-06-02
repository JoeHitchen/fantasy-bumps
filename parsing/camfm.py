import re

import requests
from bs4 import BeautifulSoup


MAYS = 'M'


def _cambridge_club_parser(club_str):
    
    if club_str.lower() == 'clare hall':
        return 'clah'
    
    return {
        'chris': 'chrc',
        'clare': 'clar',
        'corpu': 'cocc',
        'first': 'fatt',
        'jesus': 'jesc',
        'lady ': 'ladc',
        'magda': 'magc',
        'pembr': 'pemc',
        'queen': 'quec',
        'st. c': 'scac',
        'st. e': 'sedc',
        'trini': 'trih',
        'wolfs': 'wolc',
    }.get(club_str[0:5].lower(), club_str[0:4].lower())


def _get_crews_for_division(division_soup, finish):
    
    order_class = 'division_boats_finish' if finish else 'division_boats_start'
    
    start_div = division_soup.findChildren('div', {'class': order_class})[0]
    boat_divs = start_div.findChildren('div', {'class': 'boat_container'})
    
    crews = []
    for boat_div in boat_divs:
        
        crew_name = boat_div.findChildren('p')
        if not crew_name:
            continue
        
        crew_match = re.match(r'(?P<club>.*) (?P<gender>[MW])(?P<number>\d)', crew_name[0].text)
        
        crews.append((
            _cambridge_club_parser(crew_match.group('club')),
            crew_match.group('gender'),
            int(crew_match.group('number')),
        ))
    
    return crews


def _get_positions_for_gender(division_soups, day_number):
    """Generates the crew-position map for one gender from a parsed set of divisions."""
    
    ranking = []
    for division_soup in division_soups:
        ranking.extend(_get_crews_for_division(division_soup, day_number != 1))
    
    positions = {crew: rank0 + 1 for rank0, crew in enumerate(ranking)}
    
    return positions


def get_positions(series, year, day_number):
    """Generates the crew-position map for a given day of racing.
    
    **Currently hardcoded to only process Mays 2019**
    """
    
    if series != MAYS or year != 2019:
        raise ValueError('CamFM parsing only supports Mays 2019 currently')
    
    # Load results page into parser
    response = requests.get('https://bumps.camfm.co.uk/?bumps_id=1353&allboats=true')
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    charts = soup.find_all('div', {'class': 'bumps_container'})
    
    # Generate positions map
    mens_divisions = charts[0].findChildren('div', {'class': 'bumps_division_container'})
    womens_divisions = charts[1].findChildren('div', {'class': 'bumps_division_container'})
    return {
        **_get_positions_for_gender(mens_divisions, day_number),
        **_get_positions_for_gender(womens_divisions, day_number),
    }

