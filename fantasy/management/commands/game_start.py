from datetime import date, timedelta
from typing import TypedDict
from argparse import ArgumentParser
import logging

from django.core.management.base import BaseCommand
from django.db import models as db
from django.utils import timezone
from typing_extensions import Unpack, NotRequired

from integrations import live_bumps

from ...constants import Locations, Series as EventSeries, CoachingCompetitions
from ... import models
from ..actions import create_event
from .. import tasks
from . import utils, parsers

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_start')


series_reverser = {series.label.lower(): series for series in EventSeries}


class StartArgs(TypedDict):
    series: str
    date: date | None
    year: int | None
    source: NotRequired[str]
    crew_lists: NotRequired[str]
    coaching: NotRequired[str]


class Command(BaseCommand):
    help = 'Creates a new event to play FantasyBumps against.'

    def add_arguments(self, parser: ArgumentParser) -> None:

        parser.add_argument(
            'series',
            choices = [label.lower() for label in EventSeries.labels],
            help = "The game's event series",
        )
        parser.add_argument(
            '--date',
            type = date.fromisoformat,
            help = 'The start date of the game.',
        )
        parser.add_argument(
            '--year',
            type = int,
            help = 'The year of the event to create/simulate.',
        )

        parser.add_argument(
            '--source',
            choices = [
                source.value
                for sources in parsers.location_event_sources_map.values()
                for source in sources
            ],
            help = 'The source of start order data (default: {} or {})'.format(
                parsers.location_event_sources_map[Locations.OXFORD][0],
                parsers.location_event_sources_map[Locations.CAMBRIDGE][0],
            ),
        )
        parser.add_argument(
            '--crew-lists',
            choices = [
                source.value
                for sources in parsers.location_crew_list_sources_map.values()
                for source in sources
            ],
            help = 'The source of crew list data (default: {})'.format(
                parsers.location_crew_list_sources_map[Locations.OXFORD][0],
            ),
        )
        parser.add_argument(
            '--coaching',
            choices = list(CoachingCompetitions) + ['none'],
            help = 'The coaching competition to run for this event.',
            default = 'none',
            required = False,
        )


    def handle(self, **kwargs: Unpack[StartArgs]) -> None:

        # Parse series and date/year inputs
        series = series_reverser[kwargs['series']]
        series_location = parsers.series_location_map[series]
        start_date = kwargs['date'] if kwargs['date'] else timezone.now().date() + timedelta(5)
        year = kwargs['year'] if kwargs['year'] else start_date.year

        logger.info('Creating a new game for {} {}, starting on {}'.format(
            series.label,
            year,
            start_date.isoformat(),
        ))

        # Parse data source inputs
        event_source = parsers.get_validated_start_order_source(
            series_location,
            kwargs.get('source', ''),
        )
        crew_list_source = parsers.get_validated_crew_list_source(
            series_location,
            kwargs.get('crew_lists', ''),
        )
        logger.info('Using `{}` as the event source and `{}` for crew lists'.format(
            event_source['source'],
            crew_list_source['source'],
        ))

        # Create event and load data
        start_order = event_source['function'](series, year, 1)
        if series_location != Locations.DEMO:
            event = create_event(series, year, start_date, start_order)
        else:
            event = models.Event.objects.get(tag = 'demogame')
            event.days.update(date = db.F('date') + (start_date - event.first_day.date))
        utils.load_crew_lists(crew_list_source['function'], event)

        # Set coaching competition
        try:
            event.coaching_competition = CoachingCompetitions(kwargs['coaching'])
            event.save()
            logger.info('Using "{}" as the coaching competition for {}'.format(
                event.coaching_competition.label,
                event,
            ))
        except (KeyError, ValueError):
            logger.info('No coaching competition set for {}'.format(event))

        # Ancillary actions
        tasks.schedule_game_advances(event)

        if series_location == Locations.OXFORD and live_bumps.write_enabled:
            live_bumps.create_event(event.series, event.year, start_order)
            tasks.schedule_live_bumps_updates(event)

        logger.info('Created a new game for {} {}, starting on {}'.format(
            series.label,
            year,
            start_date.isoformat(),
        ))

