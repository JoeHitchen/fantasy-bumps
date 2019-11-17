import requests

from .common import seat_parser, boat_code_parser


def get_crew_lists(series, year):
    event_string = {'T': 'Torpids', 'E': 'Eights'}[series]
    print('Retriving crew lists for {} {} via Live Bumps'.format(event_string, year))  # noqa: T001
    
    url = 'https://bumps.live/data/{}_{}_crews.json'.format(event_string.lower(), year)
    response = requests.get(url)
    
    if not response.status_code == 200:
        raise IOError('Could not load crew lists page')
    
    crews = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in club_data['men'].items():
            
            crew_list = {
                seat_parser(person['pos']): person['name']
                for person in crew_data
            }
            crews[(club, 'M', int(crew_rank))] = crew_list
        
        
        for crew_rank, crew_data in club_data['women'].items():
            
            crew_list = {
                seat_parser(person['pos']): person['name']
                for person in crew_data
            }
            crews[(club, 'W', int(crew_rank))] = crew_list
    
    return crews

