from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from external import models as ext

from . import models


def get_crew(team, day, gender):
    """Return all purchases for a team, day, and gender."""
    return models.Purchase.objects.filter(team = team, day = day, crew__gender = gender)


def has_all_seats(purchases):
    """Checks that a queryset of purchase objects has every seat filled exactly once."""
    
    seats_filled = purchases.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in ext.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise ValueError('Seat filled too many times.')
    
    return all(seats_filled)


def markets_open(day):
    """Indicates whether trades can be made for the day provided.
    
    Markets open at 8pm four days before the first day of racing and the night before subsequent
    days. Markets close at 11:30am on each day of racing.
    """
    
    now = timezone.now()
    earlier_days = day.event.day_set.exclude(date__gte = day.date).exists()
    
    open_time = datetime.combine(
        day.date - timedelta(1 if earlier_days else 4),
        time(hour = 20),
        tzinfo = now.tzinfo,
    )
    
    closing_time = datetime.combine(
        day.date,
        time(hour = 11, minute = 30),
        tzinfo = now.tzinfo,
    )
    
    return open_time <= now < closing_time

