from collections import Counter

from django.db.models import Prefetch

from .constants import genders
from . import models
from . import errors


def has_all_seats(purchases, expected_seats):
    """Checks that a set of purchase objects has every seat filled exactly once."""
    
    seat_count = Counter(purchase.seat.id for purchase in purchases)
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
            'payout': round( (0.1 * change + 0.05) * crew_value ) if change >= 0 else 0,  # noqa: E201 E202 E501
        }
    
    return matrix

