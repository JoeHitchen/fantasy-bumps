from .constants import genders


def reverse_gender(gender):
    """Untested, due to simplistic nature."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]

