import re
import html

from bs4 import BeautifulSoup
import requests

from .common import TORPIDS, EIGHTS, series_text_map, seat_parser, club_parser


def _parse_crew_box(box, ext_club):
    
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
    """Generates a crew/crew-list map from the public OURCs records."""
    series_text = series_text_map[series]
    print(f'Retriving crew lists for {series_text} {year} from OURCs')  # noqa: T201
    
    # Identify OURCs event
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
        print(f'Using OURCs event #{event_id} for {series_text} {year}')  # noqa: T201
    
    except KeyError:
        raise ValueError(f'No OURCs event mapped for {series_text} {year}')
    
    # Load page into parser
    response = requests.get(
        f'https://ourcs.co.uk/racing/entries/events/event/{event_id}/crew_lists/',
        allow_redirects = False,
    )
    if not response.ok:
        raise response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract crew lists
    crews = {}
    for club_box in soup.find_all(id = re.compile('club-[a-z]{4}')):
        for crew_box in club_box.find_all(class_ = 'panel-default'):
            crew, crew_list = _parse_crew_box(crew_box, club_box['id'][5:])
            crews[crew] = crew_list
    
    print(f'Retrieved {len(crews)} crews from OURCs for {series_text} {year}')  # noqa: T201
    return crews

