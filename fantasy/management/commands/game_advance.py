from datetime import timedelta
from typing import Dict, TypedDict
from argparse import ArgumentParser
import logging

from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone
from typing_extensions import Unpack, NotRequired

from integrations import types as integrations

from ... import models
from ... import game_tools as tools
from ...constants import Locations, Series
from . import utils, parsers

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_advance')


class AdvanceArgs(TypedDict):
    oxf_source: NotRequired[str]


class Command(BaseCommand):
    """Advance the game state by one (optionally forced) day."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--forced',
            action = 'store_true',
            help = 'Force advance by shifting dates forward by 1 day',
        )
        
        oxford_sources = parsers.location_event_sources_map[Locations.OXFORD]
        parser.add_argument(
            '--oxf-source',
            default = oxford_sources[0],
            choices = [src.value for src in oxford_sources],
            help = f'The source of start order data for Oxford events (default: {oxford_sources})',
        )
    
    
    @staticmethod
    def perform_game_advance(
        source_function: integrations.PositionFcn,
        event: models.Event,
    ) -> None:
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
        
        
        # Update records
        utils.load_crew_rankings(source_function, new_day)
        tools.roll_over_purchases(old_day)
        tools.evaluate_all_investments(old_day)
    
    
    def handle(self, **kwargs: Unpack[AdvanceArgs]) -> None:
        """Identifies the sources and events for the `perform` function to act on.
        
        Optionally shifts all event dates to simulate a day passing.
        """
        
        forced = bool(kwargs.get('forced', False))
        oxf_source = kwargs.get('oxf_source', '')
        
        location_source_map: Dict[Locations, parsers.PositionSource] = {
            Locations.OXFORD: parsers.get_validated_position_source(Locations.OXFORD, oxf_source),
            Locations.CAMBRIDGE: parsers.get_validated_position_source(Locations.CAMBRIDGE, ''),
            Locations.DEMO: parsers.get_validated_position_source(Locations.DEMO, ''),
        }
        series_source_map: Dict[Series, parsers.PositionSource] = {
            series: location_source_map[location]
            for series, location in parsers.series_location_map.items()
        }
        
        
        date_range = (timezone.now() - timedelta(7), timezone.now() + timedelta(7))
        events = (
            models.Event.objects
            .filter(days__date__range = date_range)
            .exclude(market_held_closed = True)
            .distinct()
        )
        if not events:
            logger.info('No games to advance')
            return
        
        for event in events:
            logger.info(f'Advancing {event}')
            if forced:
                event.days.update(date = F('date') - timedelta(1))
            
            self.perform_game_advance(series_source_map[Series(event.series)]['function'], event)
            logger.info(f'Advanced {event}')

