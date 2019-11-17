from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone

from parsing import live_bumps

from .common import get_all_crews, add_rankings
from ... import models
from ...utils import evaluate_all_investments


class Command(BaseCommand):
    def handle(self, *args, **kwags):
        
        event = models.Event.objects.get(tag = 'eights2019')
        if not event:
            raise CommandError('No event found!')
        
        first_race = event.active_day.first_race
        
        if first_race and first_race < timezone.now() or not event.active_day.ranking.count():
            
            results = live_bumps.get_results('E', 2019)
            crews = get_all_crews(results.keys())
            add_rankings(event.active_day.next, crews, results)
            
            event.active_day.advance_purchases_to_next()
            evaluate_all_investments(event.active_day)
        
        event.days.update(date = F('date') - timedelta(1))
        
        self.stdout.write('Successfully advanced the demonstration by 24 hours.')

