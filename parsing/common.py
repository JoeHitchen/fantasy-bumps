
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
