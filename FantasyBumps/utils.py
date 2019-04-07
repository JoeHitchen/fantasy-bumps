from django.db.models import Count

from external import models as ext

from . import models


def get_crew(team, gender):
    """Return all purchases for a team and gender."""
    return models.Purchase.objects.filter(team = team, crew__gender = gender)


def has_all_seats(purchases):
    """Checks that a queryset of purchase objects has every seat filled exactly once."""
    
    seats_filled = purchases.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in ext.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise ValueError('Seat filled too many times.')
    
    return all(seats_filled)

