from django.db.models import Count

from external import models as ext

from . import models


def get_crew(team, gender):
    """Returns all rower objects associated with a team and of the specified gender."""
    return models.Rower.objects.filter(team = team, crew__gender = gender)


def has_all_seats(rowers):
    """Checks that a queryset of rower objects has every seat filled exactly once."""
    
    seats_filled = rowers.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in ext.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise ValueError('Seat filled too many times.')
    
    return all(seats_filled)

