from django.db.models import Count

from . import models
from external import models as ext


def get_crew(team):
    """Returns all rower objects associated with a team."""
    return models.Rower.objects.filter(team = team)


def has_all_seats(rowers):
    """Checks that a queryset of rower objects has every seat filled exactly once."""
    
    seats_filled = rowers.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in ext.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise ValueError('Seat filled too many times.')
    
    return all(seats_filled)

