from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone

from parsing import live_bumps, anu, camfm

from ... import models
from ...constants import Series as EventSeries
from ... import game_tools as tools

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_advance')


def _demo_wrapper(event, year, day_number):
    call_command(
        'loaddata',
        'demo_start_day{}'.format(day_number),
    )
    return {}


class Command(BaseCommand):
    """Advance the game state by one (optionally forced) day."""
    
    LIVE = 'live'
    ANU = 'anu'
    CAMFM = 'camfm'
    
    OXFORD = 'OXFORD'
    CAMBRIDGE = 'CAMBRIDGE'
    DEMO = 'DEMO'
    
    oxford_source_map = {
        LIVE: live_bumps.get_positions,
        ANU: anu.get_positions,
    }
    
    series_location_map = {
        EventSeries.TORPIDS: OXFORD,
        EventSeries.EIGHTS: OXFORD,
        EventSeries.LENTS: CAMBRIDGE,
        EventSeries.MAYS: CAMBRIDGE,
        EventSeries.DEMO: DEMO,
    }
    
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
            help = f'The source of start order data for Oxford events (default: {self.LIVE})',
        )
    
    
    @staticmethod
    def perform_game_advance(source_function, event):
        """Loads any new results and updates the game state accordingly."""
        
        # Get relevant days
        if event.active_day.first_race and timezone.now() >= event.active_day.first_race:
            old_day = event.active_day  # Racing underway for active day
            new_day = event.active_day.next
        elif event.active_day.prev:
            old_day = event.active_day.prev  # No active racing but a previous day exists
            new_day = event.active_day
        else:
            logger.info(f'No new racing has occurred for {event}')  # Pre-event, no action required
            return
        
        
        # Check results required for new day
        if new_day.ranking.count():
            logger.info(f'Crew positions for the {new_day} of {event} are already loaded')
            return
        
        
        # Get positions
        day_number = new_day.event.days.filter(date__lte = new_day.date).count()  # One-indexed
        new_positions = source_function(event.series, event.year, day_number)
        
        
        # Update records
        crews = tools.get_all_crews(new_positions.keys())
        tools.add_rankings(new_day, crews, new_positions)
        tools.roll_over_purchases(old_day)
        tools.evaluate_all_investments(old_day)
    
    
    def handle(self, *args, **kwargs):
        """Identifies the sources and events for the `perform` function to act on.
        
        Optionally shifts all event dates to simulate a day passing.
        """
        
        forced = bool(kwargs.get('forced', False))
        oxford_source = kwargs.get('oxf_source', self.LIVE)
        
        location_source_map = {
            self.OXFORD: self.oxford_source_map[oxford_source],
            self.CAMBRIDGE: camfm.get_positions,
            self.DEMO: _demo_wrapper,
        }
        series_source_map = {
            series: location_source_map[location]
            for series, location in self.series_location_map.items()
        }
        
        
        date_range = (timezone.now() - timedelta(7), timezone.now() + timedelta(7))
        events = models.Event.objects.filter(days__date__range = date_range).distinct()
        if not events:
            logger.info('No games to advance')
            return
        
        for event in events:
            logger.info(f'Advancing {event}')
            if forced:
                event.days.update(date = F('date') - timedelta(1))
            
            self.perform_game_advance(series_source_map[event.series], event)
            logger.info(f'Advanced {event}')

