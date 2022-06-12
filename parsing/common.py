
TORPIDS = 'T'
EIGHTS = 'E'
LENTS = 'L'
MAYS = 'M'

MEN = 'M'
WOMEN = 'W'


def seat_parser(seat_str):
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


def club_parser(club_str):
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


def boat_code_parser(boat_code):
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
