
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
        'SBH': 'sben', 'SCO': 'scat', 'SEH': 'sedm', 'SHI': 'shil',
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
}

