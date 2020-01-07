from collections import Counter
from functools import lru_cache
from math import log

from django.db.models import Prefetch

from .constants import genders, money
from . import models
from . import errors


def has_all_seats(purchases, expected_seats):
    """Checks that a set of purchase objects has every seat filled exactly once."""
    
    seat_count = Counter(purchase.seat_id for purchase in purchases)
    seats_filled = [seat_count.get(seat.id, 0) for seat in expected_seats]
    
    if any([count > 1 for count in seats_filled]):
        raise errors.DuplicateSeatError
    
    return all(seats_filled)


def reverse_gender(gender):
    """Return opposite gender constant to that provided."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]


@lru_cache(maxsize = 20)
def _pricing_gradient(num_crews):
    """Returns a function to calculate the rounded pricing gradient at a bungline."""
    
    def fudge_factor(num_crews):
        """Calculates a fudge-factor to counter error caused by gradient rounding."""
        
        num_crews_1 = 61  # Women's Torpids
        fudge_1 = 0.995
        num_crews_2 = 92  # Men's Eights
        fudge_2 = 0.9997
        
        top = fudge_2 * (num_crews - num_crews_1) - fudge_1 * (num_crews - num_crews_2)
        return top / (num_crews_2 - num_crews_1)
    
    ratio = (money.PRICE_MIN / money.PRICE_MAX) ** (1 / (num_crews - 1))
    ratio *= fudge_factor(num_crews)
    return lambda position: round(money.PRICE_MAX * log(ratio) * ratio ** (position - 1))


@lru_cache(maxsize = 2000)
def pricing(bungline, num_crews):
    """Iteratively calculates the price of a crew on a given bungline for a given event size."""
    
    if bungline == 1:
        return money.PRICE_MAX
    elif bungline == num_crews:
        return money.PRICE_MIN
    
    price_delta = _pricing_gradient(num_crews)(bungline)
    return pricing(bungline + 1, num_crews) - min(price_delta, -1)


def pricing_by_day_and_gender(bungline, day, gender):
    """A shallow wrapper around the pricing function to expose a bungline/day/gender interface."""
    return pricing(bungline, day.event.num_crews(gender))


def create_payout_matrix(day):
    """Calculates the value change and payout for every crew racing on the day provided."""
    
    # Retrieve crews racing
    crews = (
        models.Crew.objects
        .filter(positions__day = day)
        .prefetch_related(
            Prefetch(
                'positions',
                models.Position.objects.filter(day = day),
                to_attr='posn_old',
            ),
            Prefetch(
                'positions',
                models.Position.objects.filter(day = day.next),
                to_attr='posn_new',
            ),
        )
    )
    
    # Generate payout matrix
    matrix = {}
    for crew in crews:
        
        crew_value = crew.value(day)
        change = crew.posn_old[0].rank - crew.posn_new[0].rank  # Sign reversed
        
        matrix[crew] = {
            'value_change': crew.value(day.next) - crew_value,
            'payout': round( (0.14 * change + 0.07) * crew_value ) if change >= 0 else 0,  # noqa: E201 E202 E501
        }
    
    return matrix

