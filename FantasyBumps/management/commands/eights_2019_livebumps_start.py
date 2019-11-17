from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from parsing import live_bumps

from ... import models
from .common import get_all_crews, add_rankings, add_athletes


class Command(BaseCommand):
    def handle(self, *args, **kwags):
        """Prepares a demonstration game.
        
        Requires a database with no pre-existing events.
        """
        
        event = models.Event.objects.create(
            name = 'Eights 2019',
            tag = 'eights2019',
            mens_divisions = 7,
            womens_divisions = 6,
            boats_per_division = 13,
        )
        
        weds = create_days(event, timezone.now() + timedelta(5))
        
        results = live_bumps.get_results('E', 2019)
        crews = get_all_crews(results.keys())
        add_rankings(weds, crews, results)
        add_athletes(event, crews, live_bumps.get_crew_lists('E', 2019))


def create_days(event, start_date):
    
    weds = models.Day(
        event = event,
        name = 'Wednesday',
        date = start_date,
        first_race_time = time(12, 00),
    )
    weds.save()
    
    event.days.create(
        name = 'Thursday',
        date = start_date + timedelta(1),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Friday',
        date = start_date + timedelta(2),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Saturday',
        date = start_date + timedelta(3),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Finish',
        date = start_date + timedelta(4),
    )
    
    return weds

