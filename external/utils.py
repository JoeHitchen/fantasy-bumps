# flake8: noqa: E121

from .constants import genders

start_order_women = [
  [
    'Oriel W1',
    'Wadham W1',
    'Pembroke W1',
    'Christ Church W1',
  ],
  [
    'Keble W1',
    'Hertford W1',
    'Wolfson W1',
    'St John\'s W1',
  ],
]
start_order_men = [
  [
    'Oriel M1',
    'Pembroke M1',
    'Wadham M1',
    'Christ Church M1',
  ],
  [
    'St Catherine\'s M1',
    'Wolfson M1',
    'Hertford M1',
    'Balliol M1',
  ],
]


def get_start_order(gender):
    """Untested, due to temporary nature."""
    return {
        genders.MENS: start_order_men,
        genders.WOMENS: start_order_women,
    }[gender]

