import logging
import re

from bs4 import BeautifulSoup
import requests

from .types import PositionMap, Division, StartOrder
from .common import series_text_map
from .common import roman_parser, race_time_parser, club_parser, start_order_to_positions
from . import magic


logger = logging.getLogger(__name__)
BASE_URL = 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/'


def _parse_division(table: str) -> Division:
    rows = re.split('<tr>', str(table))

    division_match = re.search(
        "(?P<gender>Men|Women)'s Div (?P<num>[IV]{1,3})",
        rows[1],
    )
    assert division_match

    gender = division_match.group('gender')[0]
    division_number = roman_parser(division_match.group('num'))
    division_time = race_time_parser(rows[1])

    start_order = []
    for row in rows[2:]:

        url_pattern = BASE_URL + 'bumps/[a-z]{4}/(?P<club>[a-z]{4})_[mw](?P<rank>[0-9])'
        full_pattern = '(?P<bungline>[0-9]{{1,2}}). .*<td> <a href="{}'.format(url_pattern)
        bungline_match = re.search(full_pattern, row)
        assert bungline_match

        start_order.append((
            (
                club_parser(bungline_match.group('club')),
                gender,
                int(bungline_match.group('rank')),
            ),
            True,
        ))

    return Division(
        gender = gender,
        number = division_number,
        race_time = division_time,
        size = len(start_order),
        crews = start_order,
        finalised = True,
    )


def get_start_order(series: str, year: int, day_number: int) -> StartOrder:
    """Retrieves the day's start order from Anu's records."""

    series_text = series_text_map[series]
    logger.info('Retrieving start order for {} {} (day {}) from Anu'.format(
        series_text,
        year,
        day_number,
    ))


    # Load page into parser
    day_codes = magic.anu_day_code(series, year, day_number)
    for day_code in day_codes:
        response = requests.get(BASE_URL + '{}/{}{}{}.html'.format(
            series_text.lower(),
            series.lower(),
            str(year)[-2:],
            day_code,
        ))
        if response.ok:
            break
        if day_code == day_codes[-1]:
            response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')


    # Extract crew positions
    divisions = []
    for table in soup.find_all('table')[2:]:
        if table.string is not None:
            continue

        divisions.append(_parse_division(table))

    logger.info('Retrieved start order ({} crews) for {} {} (day {}) from Anu'.format(
        sum(len(division['crews']) for division in divisions),
        series_text,
        year,
        day_number,
    ))
    return sorted(divisions, key = lambda div: div['race_time'])


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from Anu's records."""

    return start_order_to_positions(get_start_order(series, year, day_number))

