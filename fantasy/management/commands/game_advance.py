from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone

from parsing import live_bumps, anu

from ... import models
from ...constants import Series as EventSeries
from ... import game_tools as tools


class Command(BaseCommand):
    """Advance the game state by one (optionally forced) day
    
    N.B. Anu's results rely on tomorrow's day of the week, so do not work for forced advances.
    """
    
    LIVE_BUMPS = 'live'
    ANU = 'anu'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forced',
            action = 'store_true',
            help = 'Force advance by shifting dates forward by 1 day',
        )
        
        parser.add_argument(
            '--source',
            default = self.LIVE_BUMPS,
            choices = [self.LIVE_BUMPS, self.ANU],
            help = 'The source of start order data (default: live)',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Get current events
        now = timezone.now()
        events = (
            models.Event.objects
            .filter(days__date__range = (now - timedelta(7), now + timedelta(7)))
            .distinct()
        )
        source = kwargs.get('source', self.LIVE_BUMPS)
        
        if not events:
            self.stdout.write('No games to advance')
            return
        
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
            if event.series == EventSeries.DEMO:
                call_command(
                    'loaddata',
                    'demo_start_day{}'.format(new_day.id),
                )
            
            # Bumps events
            elif source == self.LIVE_BUMPS:
                new_day_index = tools.get_day_index(new_day)
                results = live_bumps.get_results(event.series, event.year, new_day_index)
                crews = tools.get_all_crews(results.keys())
                tools.add_rankings(new_day, crews, results)
            else:
                day_tag = new_day.date.strftime('%a').lower() if new_day.first_race_time else 'end'
                results = anu.get_start_order(event.series, event.year, day_tag)
                crews = tools.get_all_crews(results.keys())
                tools.add_rankings(new_day, crews, results)
            
            tools.roll_over_purchases(old_day)
            tools.evaluate_all_investments(old_day)
            self.stdout.write('Completed!')

