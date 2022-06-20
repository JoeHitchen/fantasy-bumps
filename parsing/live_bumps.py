import html
import logging

import requests

from .common import TORPIDS, EIGHTS, MEN, WOMEN, series_text_map, seat_parser, boat_code_parser

logger = logging.getLogger(__name__)


def _crew_results(crew_data):
    positions = [crew_data['start']]
    
    for move in crew_data['moves']:
        positions.append(positions[-1] - move['moves'])  # Sign reversed
    
    return positions


def _parse_crew_list(crew_data):
    return {
        seat_parser(person['pos']): html.unescape(person['name'])
        for person in crew_data
    }


def get_positions(series, year, day_number):
    event_string = {TORPIDS: 'Torpids', EIGHTS: 'Eights'}[series]
    print('Retriving results for {} {} via Live Bumps'.format(event_string, year))  # noqa: T201
    
    url = 'https://bumps.live/data/{}_{}.json'.format(event_string.lower(), year)
    response = requests.get(url)
    
    if not response.status_code == 200:
        raise IOError('Could not load crew lists page')
    
    crews = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in enumerate(club_data['men']):
            crew_results = _crew_results(crew_data)
            index = min(day_number, len(crew_results)) - 1
            crews[(club, MEN, crew_rank + 1)] = crew_results[index]
        
        for crew_rank, crew_data in enumerate(club_data['women']):
            crew_results = _crew_results(crew_data)
            index = min(day_number, len(crew_results)) - 1
            crews[(club, WOMEN, crew_rank + 1)] = crew_results[index]
    
    return crews


def get_crew_lists(series, year):
    """Generates a crew/crew-list map from the Live Bumps records."""
    
    series_text = series_text_map[series]
    logger.info(f'Retriving crew lists for {series_text} {year} from Live Bumps')
    
    # Load data
    response = requests.get(f'https://bumps.live/data/{series_text.lower()}_{year}_crews.json')
    if not response.ok:
        raise response.raise_for_status()
    
    # Extract crew lists
    crew_lists = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in club_data['men'].items():
            crew_lists[(club, MEN, int(crew_rank))] = _parse_crew_list(crew_data)
        
        for crew_rank, crew_data in club_data['women'].items():
            crew_lists[(club, WOMEN, int(crew_rank))] = _parse_crew_list(crew_data)
    
    logger.info(f'Retrieved {len(crew_lists)} crews from Live Bumps for {series_text} {year}')
    return crew_lists

