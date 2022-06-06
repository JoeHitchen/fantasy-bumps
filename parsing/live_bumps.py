import html

import requests

from .common import seat_parser, boat_code_parser


def _crew_results(crew_data):
    positions = [crew_data['start']]
    
    for move in crew_data['moves']:
        positions.append(positions[-1] - move['moves'])  # Sign reversed
    
    return positions


def get_positions(series, year, day_number):
    event_string = {'T': 'Torpids', 'E': 'Eights'}[series]
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
            crews[(club, 'M', crew_rank + 1)] = crew_results[index]
        
        for crew_rank, crew_data in enumerate(club_data['women']):
            crew_results = _crew_results(crew_data)
            index = min(day_number, len(crew_results)) - 1
            crews[(club, 'W', crew_rank + 1)] = crew_results[index]
    
    return crews


def get_crew_lists(series, year):
    event_string = {'T': 'Torpids', 'E': 'Eights'}[series]
    print('Retriving crew lists for {} {} via Live Bumps'.format(event_string, year))  # noqa: T201
    
    url = 'https://bumps.live/data/{}_{}_crews.json'.format(event_string.lower(), year)
    response = requests.get(url)
    
    if not response.status_code == 200:
        raise IOError('Could not load crew lists page')
    
    crews = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in club_data['men'].items():
            
            crew_list = {
                seat_parser(person['pos']): html.unescape(person['name'])
                for person in crew_data
            }
            crews[(club, 'M', int(crew_rank))] = crew_list
        
        
        for crew_rank, crew_data in club_data['women'].items():
            
            crew_list = {
                seat_parser(person['pos']): html.unescape(person['name'])
                for person in crew_data
            }
            crews[(club, 'W', int(crew_rank))] = crew_list
    
    return crews

