import re
import html

from bs4 import BeautifulSoup
import requests

from .common import TORPIDS, EIGHTS, seat_parser, club_parser


def _crew_box(box, ext_club):
    
    crew_header = box.find('a').string
    club = club_parser(crew_header)
    gender = crew_header[-2]
    rank = int(crew_header[-1])
    
    crew_list = {
        seat_parser(crew_row.find('th').string): html.unescape(crew_row.find('td').string)
        for crew_row in box.find_all('tr')
    }
    
    return ((club, gender, rank), crew_list)


def get_crew_lists(series, year):
    
    try:
        event_id = {
            (TORPIDS, 2017): 173,
            (EIGHTS, 2017): 174,
            (TORPIDS, 2018): 184,
            (EIGHTS, 2018): 186,
            (TORPIDS, 2019): 195,
            (EIGHTS, 2019): 198,
            (TORPIDS, 2021): 217,
            (TORPIDS, 2022): 229,
            (EIGHTS, 2022): 230,
        }[(series, year)]
    
    except KeyError:
        raise ValueError('Historical crew lists not mapped for {} {}'.format(
            {TORPIDS: 'Torpids', EIGHTS: 'Eights'}.get(series),
            year,
        ))
    
    print('Retriving OURCs crew lists for event #{}'.format(event_id))  # noqa: T201
    
    url = 'https://ourcs.co.uk/racing/entries/events/event/{}/crew_lists/'.format(event_id)
    response = requests.get(url, allow_redirects = False)
    
    if not response.status_code == 200:
        raise IOError('Could not load crew lists page')
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    crews = {}
    for club_box in soup.find_all(id = re.compile('club-[a-z]{4}')):
        for crew_box in club_box.find_all(class_ = 'panel-default'):
            crew = _crew_box(crew_box, club_box['id'][5:])
            crews[crew[0]] = crew[1]
    
    return crews

