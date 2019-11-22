from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone

from parsing import live_bumps

from ... import models
from ...constants import series as event_series
from ...game_tools import get_all_crews, add_rankings, roll_over_purchases, evaluate_all_investments


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--forced',
            action = 'store_true',
            help = 'Force advance by shifting dates forward by 1 day',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Get current events
        now = timezone.now()
        events = (
            models.Event.objects
            .filter(days__date__range = (now - timedelta(7), now + timedelta(7)))
            .distinct()
        )
        
        # Iterate over all events
        for event in events:
            self.stdout.write('Advancing {}...'.format(event))
            
            # Shift dates for forced updates
            if kwargs['forced']:
                event.days.update(date = F('date') - timedelta(1))
            
            # Get relevant days
            if event.active_day.first_race and now >= event.active_day.first_race:
                # Racing started on the active day
                
                old_day = event.active_day
                new_day = event.active_day.next
            
            elif event.active_day.prev:
                # A previous day exists
                
                old_day = event.active_day.prev
                new_day = event.active_day
            
            else:
                # Pre-event, no action required
                self.stdout.write('No new racing has occurred.')
                continue
            
            # Check results required for new day
            if new_day.ranking.count():
                self.stdout.write('Results for {} already loaded.'.format(new_day))
                continue
            
            self.stdout.write('Loading start order for {}...'.format(new_day))
            
            # Demo events
            if event.series == event_series.DEMO:
                call_command(
                    'loaddata',
                    'demo_start_day{}'.format(new_day.id),
                )
            
            # Bumps events
            else:
                results = live_bumps.get_results(event.series, event.year)
                crews = get_all_crews(results.keys())
                add_rankings(new_day, crews, results)
            
            roll_over_purchases(old_day)
            evaluate_all_investments(old_day)
            self.stdout.write('Completed!')

