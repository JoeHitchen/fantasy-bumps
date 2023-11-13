import re
import html
from typing import cast
import logging

from bs4 import BeautifulSoup, Tag
import requests

from .types import Crew, CrewList, CrewListMap
from .common import series_text_map, seat_parser, club_parser
from . import magic

logger = logging.getLogger(__name__)


def _parse_crew_box(box: Tag) -> tuple[Crew, CrewList]:

    crew_header = cast(str, box.find('a').string)  # type: ignore
    club = club_parser(crew_header)
    gender = crew_header[-2]
    rank = int(crew_header[-1])

    crew_list = {
        seat_parser(crew_row.find('th').string): html.unescape(crew_row.find('td').string)
        for crew_row in box.find_all('tr')
    }

    return ((club, gender, rank), crew_list)


def get_crew_lists(series: str, year: int) -> CrewListMap:
    """Generates a crew/crew-list map from the public OURCs records."""

    series_text = series_text_map[series]
    logger.info(f'Retrieving crew lists for {series_text} {year} from OURCs')

    # Identify OURCs event
    event_id = magic.ourcs_event_id(series, year)
    logger.info(f'Using OURCs event #{event_id} for {series_text} {year}')

    # Load page into parser
    response = requests.get(
        f'https://ourcs.co.uk/racing/entries/events/event/{event_id}/crew_lists/',
        allow_redirects = False,
    )
    if not response.ok:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')


    # Extract crew lists
    crew_lists = {}
    for club_box in soup.find_all(id = re.compile('club-[a-z]{4}')):
        for crew_box in club_box.find_all(class_ = 'panel-default'):
            crew, crew_list = _parse_crew_box(crew_box)
            crew_lists[crew] = crew_list

    logger.info(f'Retrieved {len(crew_lists)} crews for {series_text} {year} from OURCs')
    return crew_lists

