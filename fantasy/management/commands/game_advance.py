from datetime import timedelta
from typing import Dict, TypedDict
from argparse import ArgumentParser
import logging

from django.core.management.base import BaseCommand
from django.db import models as db, transaction
from django.utils import timezone
from django.core.mail import mail_admins
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
    
    
    @staticmethod
    def advance_core(
        day: models.Day,
        source_function: integrations.PositionFcn,
        override_hold: bool = False,
    ) -> None:
        """The sensitive core of the game advance routine."""
        
        reject_for_hold_args = {'event__market_held_closed': False} if not override_hold else {}
        
        with transaction.atomic():
            transaction_day = (
                models.Day.objects
                .select_for_update()
                .filter(**reject_for_hold_args)
                .get(id = day.id, advanced = False)
            )
            
            utils.load_crew_rankings(source_function, transaction_day.next)
            tools.roll_over_purchases(transaction_day)
            tools.evaluate_all_investments(transaction_day)
            
            transaction_day.advanced = True
            transaction_day.save()
    
    
    @staticmethod
    def perform_game_advance(
        source_function: integrations.PositionFcn,
        event: models.Event,
        override_hold: bool = False,
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
        try:
            Command.advance_core(old_day, source_function, override_hold)
            
        except models.Day.DoesNotExist:
            logger.info(f'{old_day} of {event} has already been advanced')
            
        except Exception as err:
            logger.error(f'An error occurred advancing {old_day} of {event}\n >> {err}')
            
            event.market_held_closed = True
            event.save()
            
            mail_admins(f'Game Advance Failed - {event}', (
                f'An unknown error occurred when advancing {old_day} of {event}.'
                + f'\n\n >> {err}'
                + '\n\nThe markets are held closed. '
                + "Hopefully it's an easy fix..."
            ), fail_silently = True)
    
    
    def handle(self, **kwargs: Unpack[AdvanceArgs]) -> None:
        """Identifies the sources and events for the `perform` function to act on.
        
        Optionally shifts all event dates to simulate a day passing.
        """
        
        forced = bool(kwargs.get('forced', False))
        oxf_source = kwargs.get('oxf_source', '')
        override_hold = bool(kwargs.get('override', False))
        
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
            
            self.perform_game_advance(
                series_source_map[Series(event.series)]['function'],
                event,
                override_hold,
            )
            logger.info(f'Advanced {event}')

