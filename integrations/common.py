from datetime import time
import re

from .types import StartOrder, PositionMap

TORPIDS = 'T'
EIGHTS = 'E'
LENTS = 'L'
MAYS = 'M'
series_text_map = {TORPIDS: 'Torpids', EIGHTS: 'Eights', LENTS: 'Lents', MAYS: 'Mays'}


MEN = 'M'
WOMEN = 'W'
gender_map = {MEN: 'Men', WOMEN: 'Women'}


def roman_parser(numerals: str) -> int:
    """Maps roman numerals to integers."""

    return {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}[numerals]


def race_time_parser(div_header: str) -> time:
    """Extracts the division time from the division header data."""

    time_match = re.search(r'(\d\d?)[:.](\d\d)', div_header)
    assert time_match
    hour = int(time_match.groups()[0])
    mins = int(time_match.groups()[1])
    return time(hour if hour > 9 else hour + 12, mins)


def seat_parser(seat_str: str) -> int:
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


def club_parser(club_str: str) -> str:
    return {
        'green ': 'grte',
        'l.m.h.': 'lady',
        'new co': 'newc',
        'st ann': 'sann',
        'st ant': 'sant',
        'st ben': 'sben',
        'st cat': 'scat',
        'st edm': 'sedm',
        's.e.h.': 'sedm',
        'st hil': 'shil',
        'st hug': 'shug',
        'st joh': 'sjoh',
        'st pet': 'spet',
    }.get(club_str[0:6].lower(), club_str[0:4].lower())


def boat_code_parser(boat_code: str) -> str:
    return {
        'BAL': 'ball', 'BRC': 'bras', 'CHB': 'chri', 'COO': 'corp',
        'EXC': 'exet', 'GTM': 'grte', 'HEC': 'hert', 'JEO': 'jesu',
        'KEB': 'kebl', 'LMH': 'lady', 'LIN': 'lina', 'LIC': 'linc',
        'MAG': 'magd', 'MAN': 'mans', 'MER': 'mert', 'NEC': 'newc',
        'ORO': 'orie', 'OSG': 'osle', 'PMB': 'pemb', 'QCO': 'quee',
        'RPC': 'rege', 'SOM': 'some', 'SAC': 'sann', 'SAY': 'sant',
        'SBH': 'reub', 'SCO': 'scat', 'SEH': 'sedm', 'SHI': 'shil',
        'SHG': 'shug', 'SJO': 'sjoh', 'SPC': 'spet', 'TRO': 'trin',
        'UCO': 'univ', 'WAD': 'wadh', 'WOO': 'wolf', 'WRO': 'worc',
        'OSL': 'osle',
    }[boat_code.upper()]


boat_code_map = {
    'ball': 'BAL', 'bras': 'BRC', 'chri': 'CHB', 'corp': 'COO',
    'exet': 'EXC', 'grte': 'GTM', 'hert': 'HEC', 'jesu': 'JEO',
    'kebl': 'KEB', 'lady': 'LMH', 'lina': 'LIN', 'linc': 'LIC',
    'magd': 'MAG', 'mans': 'MAN', 'mert': 'MER', 'newc': 'NEC',
    'orie': 'ORO', 'osle': 'OSG', 'pemb': 'PMB', 'quee': 'QCO',
    'rege': 'RPC', 'some': 'SOM', 'sann': 'SAC', 'sant': 'SAY',
    'sben': 'SBH', 'scat': 'SCO', 'sedm': 'SEH', 'shil': 'SHI',
    'shug': 'SHG', 'sjoh': 'SJO', 'spet': 'SPC', 'trin': 'TRO',
    'univ': 'UCO', 'wadh': 'WAD', 'wolf': 'WOO', 'worc': 'WRO',
    'reub': 'SBH',
}


def start_order_to_positions(start_order: StartOrder) -> PositionMap:
    """Converts a start order to a map of positions."""

    ordered_divisions = sorted(start_order, key = lambda div: div['race_time'])

    positions = {}
    for gender in [MEN, WOMEN]:

        bungline = 0
        for division in ordered_divisions[::-1]:

            if division['gender'] != gender:
                continue

            for crew, position_status in division['crews']:
                bungline += 1
                positions[crew] = (bungline, position_status)

    return positions


def add_crews_by_gender(start_order: StartOrder, positions: PositionMap, gender: str) -> None:
    """Populates a start order from a position map for the gender given."""

    ordered_divisions = sorted(start_order, key = lambda div: div['race_time'])

    position_order = [
        (crew, position)
        for crew, position in positions.items()
        if crew[1] == gender
    ]
    position_order.sort(key = lambda item: item[1])

    for division in ordered_divisions[::-1]:

        if not division['gender'] == gender:
            continue

        division['crews'] = [
            (crew, position[1])
            for crew, position
            in position_order[:division['size']]
        ]

        if len(position_order) < division['size']:
            division['size'] = len(position_order)
            return

        position_order = position_order[division['size']:]

