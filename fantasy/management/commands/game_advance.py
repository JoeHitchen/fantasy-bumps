from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone

from parsing import live_bumps, anu, camfm

from ... import models
from ...constants import Series as EventSeries
from ... import game_tools as tools


def _demo_wrapper(event, year, day_number):
    call_command(
        'loaddata',
        'demo_start_day{}'.format(day_number),
    )
    return {}


class Command(BaseCommand):
    """Advance the game state by one (optionally forced) day
    
    N.B. Anu's results rely on tomorrow's day of the week, so do not work for forced advances.
    """
    
    LIVE = 'live'
    ANU = 'anu'
    CAMFM = 'camfm'
    
    OXFORD = 'OXFORD'
    CAMBRIDGE = 'CAMBRIDGE'
    DEMO = 'DEMO'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forced',
            action = 'store_true',
            help = 'Force advance by shifting dates forward by 1 day',
        )
        
        parser.add_argument(
            '--oxf-source',
            default = self.LIVE,
            choices = [self.LIVE, self.ANU],
            help = f'The source of start order data for Oxford (default: {self.LIVE})',
        )
        
        parser.add_argument(
            '--cam-source',
            default = self.CAMFM,
            choices = [self.CAMFM],
            help = f'The source of start order data for Cambridge (default: {self.CAMFM})',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Parse command arguments
        forced = bool(kwargs['forced'])
        oxford_source = kwargs.get('oxf_source', self.LIVE)
        cambridge_source = kwargs.get('cam_source', self.CAMFM)
        
        source_function_map = {
            self.OXFORD: {
                self.LIVE: live_bumps.get_positions,
                self.ANU: anu.get_positions,
            }[oxford_source],
            self.CAMBRIDGE: {self.CAMFM: camfm.get_positions}[cambridge_source],
            self.DEMO: _demo_wrapper,
        }
        series_source_map = {
            EventSeries.TORPIDS: self.OXFORD,
            EventSeries.EIGHTS: self.OXFORD,
            EventSeries.LENTS: self.CAMBRIDGE,
            EventSeries.MAYS: self.CAMBRIDGE,
            EventSeries.DEMO: self.DEMO,
        }
        
        
        # Get current events
        now = timezone.now()
        events = (
            models.Event.objects
            .filter(days__date__range = (now - timedelta(7), now + timedelta(7)))
            .distinct()
        )
        if not events:
            self.stdout.write('No games to advance')
            return
        
        
        # Iterate over all events
        for event in events:
            self.stdout.write('Advancing {}...'.format(event))
            
            # Shift dates for forced updates
            if forced:
                event.days.update(date = F('date') - timedelta(1))
            
            
            # Get relevant days
            if event.active_day.first_race and now >= event.active_day.first_race:
                old_day = event.active_day  # Racing underway for active day
                new_day = event.active_day.next
            elif event.active_day.prev:
                old_day = event.active_day.prev  # No active racing but a previous day exists
                new_day = event.active_day
            else:
                self.stdout.write('No new racing has occurred.')  # Pre-event, no action required
                continue
            
            
            # Check results required for new day
            if new_day.ranking.count():
                self.stdout.write('Results for {} already loaded.'.format(new_day))
                continue
            
            self.stdout.write('Loading start order for {}...'.format(new_day))
            
            
            # Get positions
            day_number = new_day.event.days.filter(date__lte = new_day.date).count()  # One-indexed
            source = series_source_map[event.series]
            new_positions = source_function_map[source](event.series, event.year, day_number)
            
            
            # Update records
            crews = tools.get_all_crews(new_positions.keys())
            tools.add_rankings(new_day, crews, new_positions)
            tools.roll_over_purchases(old_day)
            tools.evaluate_all_investments(old_day)
            self.stdout.write('Completed!')

