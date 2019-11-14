import re

from bs4 import BeautifulSoup
import requests


def _seat_parser(seat_str):
    return {
        'Bow': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        '5': 5,
        '6': 6,
        '7': 7,
        'Str': 8,
        'Cox': 9,
        'Coach': 10,
    }[seat_str]


def _club_parser(club_str):
    return {
        'green ': 'grte',
        'new co': 'newc',
        'st ann': 'sann',
        'st ant': 'sant',
        'st ben': 'sben',
        'st cat': 'scat',
        'st edm': 'sedm',
        'st hil': 'shil',
        'st hug': 'shug',
        'st joh': 'sjoh',
        'st pet': 'spet',
    }.get(club_str[0:6].lower(), club_str[0:4].lower())


def _crew_box(box, ext_club):
    
    crew_header = box.find('a').string
    club = _club_parser(crew_header)
    gender = crew_header[-2]
    rank = int(crew_header[-1])
    
    crew_list = {
        _seat_parser(crew_row.find('th').string): crew_row.find('td').string
        for crew_row in box.find_all('tr')
    }
    
    return ((club, gender, rank), crew_list)


def get_crew_lists(event_id):
    print('Retriving OURCs crew lists for event #{}'.format(event_id))  # noqa: T001
    
    url = 'https://ourcs.co.uk/racing/entries/events/event/{}/crew_lists/'.format(event_id)
    response = requests.get(url)
    
    if not response.status_code == 200:
        raise IOError('Could not load crew lists page')
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    crews = {}
    for club_box in soup.find_all(id = re.compile('club-[a-z]{4}')):
        for crew_box in club_box.find_all(class_ = 'panel-default'):
            crew = _crew_box(crew_box, club_box['id'][5:])
            crews[crew[0]] = crew[1]
    
    return crews

