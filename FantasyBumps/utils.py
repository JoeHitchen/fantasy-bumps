from django.db.models import Count

from .constants import genders
from . import models
from . import errors


def has_all_seats(purchases):
    """Checks that a queryset of purchase objects has every seat filled exactly once."""
    
    seats_filled = purchases.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in models.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise errors.DuplicateSeatError
    
    return all(seats_filled)


def reverse_gender(gender):
    """Return opposite gender constant to that provided."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]

