from . import models
from .constants import genders

start_order_women = [
    [
        models.Crew(name = "Oriel W1", gender = genders.WOMENS),
        models.Crew(name = "Wadham W1", gender = genders.WOMENS),
        models.Crew(name = "Pembroke W1", gender = genders.WOMENS),
        models.Crew(name = "Christ Church W1", gender = genders.WOMENS),
    ],
    [
        models.Crew(name = "Keble W1", gender = genders.WOMENS),
        models.Crew(name = "Hertford W1", gender = genders.WOMENS),
        models.Crew(name = "Wolfson W1", gender = genders.WOMENS),
        models.Crew(name = "St John's W1", gender = genders.WOMENS),
    ],
]
start_order_men = [
    [
        models.Crew(name = "Oriel M1", gender = genders.MENS),
        models.Crew(name = "Pembroke M1", gender = genders.MENS),
        models.Crew(name = "Wadham M1", gender = genders.MENS),
        models.Crew(name = "Christ Church M1", gender = genders.MENS),
    ],
    [
        models.Crew(name = "St Catherine's M1", gender = genders.MENS),
        models.Crew(name = "Wolfson M1", gender = genders.MENS),
        models.Crew(name = "Hertford M1", gender = genders.MENS),
        models.Crew(name = "Balliol M1", gender = genders.MENS),
    ],
]


def get_start_order(gender):
    """Untested, due to temporary nature."""
    return {
        genders.MENS: start_order_men,
        genders.WOMENS: start_order_women,
    }[gender]


def reverse_gender(gender):
    """Untested, due to simplistic nature."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]

