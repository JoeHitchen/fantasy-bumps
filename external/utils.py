from . import models
from .constants import genders


def get_start_order(gender):
    """Untested, due to temporary nature."""
    start_order = models.Position.objects.filter(crew__gender = gender)
    return [
        start_order[0:4],
        start_order[4:8],
    ]


def reverse_gender(gender):
    """Untested, due to simplistic nature."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]

