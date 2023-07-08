from datetime import timedelta
from typing import TypedDict
from argparse import ArgumentParser
import logging

from django.core.management.base import BaseCommand
from django.db import models as db
from django.utils import timezone
from typing_extensions import Unpack, NotRequired

from ... import models
from ...constants import Locations, Series
from ..game_advance import perform_advance
from . import parsers

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_advance')


class AdvanceArgs(TypedDict):
    oxf_source: NotRequired[str]
    override: NotRequired[bool]


class Command(BaseCommand):
    """Advance the game state by one (optionally forced) day."""
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--forced',
            action = 'store_true',
            help = 'Force advance by shifting dates forward by 1 day',
        )
        parser.add_argument(
            '--override',
            action = 'store_true',
            help = 'Overrides any market holds in place',
        )
        
        oxford_sources = parsers.location_event_sources_map[Locations.OXFORD]
        parser.add_argument(
            '--oxf-source',
            default = oxford_sources[0],
            choices = [src.value for src in oxford_sources],
            help = f'The source of start order data for Oxford events (default: {oxford_sources})',
        )
    
    
    def handle(self, **kwargs: Unpack[AdvanceArgs]) -> None:
        """Identifies the sources and events for the `perform` function to act on.
        
        Optionally shifts all event dates to simulate a day passing.
        """
        
        forced = bool(kwargs.get('forced', False))
        oxf_source = kwargs.get('oxf_source', '')
        override_hold = bool(kwargs.get('override', False))
        
        location_source_map: dict[Locations, parsers.PositionSource] = {
            Locations.OXFORD: parsers.get_validated_position_source(Locations.OXFORD, oxf_source),
            Locations.CAMBRIDGE: parsers.get_validated_position_source(Locations.CAMBRIDGE, ''),
            Locations.DEMO: parsers.get_validated_position_source(Locations.DEMO, ''),
        }
        series_source_map: dict[Series, parsers.PositionSource] = {
            series: location_source_map[location]
            for series, location in parsers.series_location_map.items()
        }
        
        
        date_range = (timezone.now() - timedelta(7), timezone.now() + timedelta(7))
        market_hold_args = {'market_held_closed': True} if not override_hold else {}
        events = (
            models.Event.objects
            .filter(days__date__range = date_range)
            .exclude(**market_hold_args)
            .distinct()
        )
        if not events:
            logger.info('No games to advance')
            return
        
        for event in events:
            logger.info(f'Advancing {event}')
            if forced:
                event.days.update(date = db.F('date') - timedelta(1))
            
            perform_advance(
                event,
                series_source_map[Series(event.series)]['function'],
                override_hold,
            )
            logger.info(f'Advanced {event}')

