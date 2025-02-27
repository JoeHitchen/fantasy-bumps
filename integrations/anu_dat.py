from datetime import time
import logging
import re

import requests

from .types import PositionMap, CrewPosition, Division, StartOrder
from .common import series_text_map, MEN, WOMEN, gender_map
from .common import roman_parser, race_time_parser, club_parser, start_order_to_positions
from . import magic

logger = logging.getLogger(__name__)
BASE_URL = 'http://eodg.atm.ox.ac.uk/user/dudhia/rowing/'


def get_start_order_by_gender(
    series: str,
    year: int,
    gender: str,
    day_number: int,
) -> StartOrder:
    """Retrieves the start order for a given race day and gender from Anu's .dat files."""
    logger.info("Retrieving {}'s start order for {} {} (day {}) from Anu .dat".format(
        gender_map[gender].lower(),
        series_text_map[series],
        year,
        day_number,
    ))

    # Get raw data
    day_codes = magic.anu_day_code(series, year, day_number)
    for day_code in day_codes:
        response = requests.get(BASE_URL + magic.anu_data_url_template(series, year).format(
            series_text_map[series].lower(),
            series.lower(),
            str(year)[2:4],
            day_code,
            gender.lower(),
        ))
        if response.ok:
            break
        if day_code == day_codes[-1]:
            response.raise_for_status()

    data = response.text.split('\n')
    data = [line for line in data if line.strip()]

    # Parse header
    event = data.pop(0)  # noqa: 841
    num_div_match = re.search(r'(\d) div', data.pop(0))
    assert num_div_match
    number_of_divisions = int(num_div_match.groups()[0])

    # Parse divisions in turn
    divisions: list[Division] = []
    for _i in range(number_of_divisions):

        # Parses division rows
        div_header = data.pop(0)
        div_finalised = '?' not in div_header

        div_number_match = re.search('([IV]+)', div_header)
        assert div_number_match
        div_number = roman_parser(div_number_match.groups()[0])

        div_size_match = re.search(r'(\d{1,2}) crews', div_header)
        assert div_size_match
        div_size = int(div_size_match.groups()[0])

        divisions.append({
            'gender': gender,
            'number': div_number,
            'race_time': race_time_parser(div_header),
            'size': div_size,
            'finalised': div_finalised,
            'crews': [_parse_crew(data, gender, div_finalised) for _ in range(div_size)],
        })

    if len(data) > 0:

        # Parses division rows
        div_header = data.pop(0)

        div_size_match = re.search(r'(\d{1,2}) crews', div_header)
        assert div_size_match
        div_size = int(div_size_match.groups()[0])

        divisions.append({
            'gender': gender,
            'number': 10,
            'race_time': time(11, 00),
            'size': div_size,
            'finalised': False,
            'crews': [_parse_crew(data, gender, False) for _ in range(div_size)],
        })

    divisions.sort(key = lambda div: div['race_time'])

    logger.info("Retrieved {} {}'s divisions and {} crews for {} {} (day {}) from Anu .dat".format(
        len(divisions),
        gender_map[gender].lower(),
        sum(len(division['crews']) for division in divisions),
        series_text_map[series],
        year,
        day_number,
    ))
    return divisions


def get_start_order(series: str, year: int, day_number: int) -> StartOrder:
    """Retrieves the day's start order from Anu's .dat files."""

    return sorted([
        *get_start_order_by_gender(series, year, MEN, day_number),
        *get_start_order_by_gender(series, year, WOMEN, day_number),
    ], key = lambda div: div['race_time'])


def get_positions_by_gender(series: str, year: int, gender: str, day_number: int) -> PositionMap:
    """Generates a crew/position map for one gender from Anu's .dat files."""

    return start_order_to_positions(get_start_order_by_gender(series, year, gender, day_number))


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from Anu's .dat files."""

    return start_order_to_positions(get_start_order(series, year, day_number))


def _parse_crew(data: list[str], gender: str, finalised: bool) -> CrewPosition:
    """Parses a crew record from a data file line"""

    crew_str = data.pop(0).strip()

    if crew_str[-1] in ['I', 'V']:
        crew_match = re.search("([A-Za-z'. ]+) ([IV]+)", crew_str)
        assert crew_match

        club_str = crew_match.groups()[0]
        crew_rank = roman_parser(crew_match.groups()[1])

    else:
        crew_match = re.search("([A-Za-z'. ]+)", crew_str)
        assert crew_match

        club_str = crew_match.groups()[0]
        crew_rank = 1

    return (
        (club_parser(club_str.strip()), gender, crew_rank),
        finalised and '?' not in crew_str,
    )

