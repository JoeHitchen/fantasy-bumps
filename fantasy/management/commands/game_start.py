from datetime import date, time, timedelta
import logging

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

from parsing import live_bumps, anu, ourcs, camfm

from ... import models
from ...constants import Series as EventSeries
from . import utils

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_start')


def _demo_positions(series, year, day_number):
    call_command(
        'loaddata',
        'demo_crews',
        'demo_start_day{}'.format(day_number),
    )
    return {}


def _demo_crew_lists(series, year):
    return ourcs.get_crew_lists(EventSeries.TORPIDS, 2013)


def _noop_crew_lists(series, year):
    return {}


series_reverser = {series.label.lower(): series for series in EventSeries}


class Command(BaseCommand):
    help = 'Creates a new event to play FantasyBumps against.'
    
    DEMO_LOC = 'D'
    OXFORD = 'O'
    CAMBRIDGE = 'C'
    
    DEMO_SRC = 'demo'
    LIVE_BUMPS = 'live'
    ANU = 'anu'
    OURCS = 'ourcs'
    CAMFM = 'camfm'
    NOOP = 'noop'
    
    series_location_map = {
        EventSeries.DEMO: DEMO_LOC,
        EventSeries.TORPIDS: OXFORD,
        EventSeries.EIGHTS: OXFORD,
        EventSeries.MAYS: CAMBRIDGE,
        EventSeries.MAYS: CAMBRIDGE,
    }
    
    location_event_sources_map = {
        DEMO_LOC: [DEMO_SRC],
        OXFORD: [LIVE_BUMPS, ANU],
        CAMBRIDGE: [CAMFM],
    }
    location_crew_list_sources_map = {
        DEMO_LOC: [DEMO_SRC],
        OXFORD: [LIVE_BUMPS, OURCS],
        CAMBRIDGE: [NOOP],
    }
    
    event_source_function_map = {
        DEMO_SRC: _demo_positions,
        LIVE_BUMPS: live_bumps.get_positions,
        ANU: anu.get_positions,
        CAMFM: camfm.get_positions,
    }
    
    crew_list_source_function_map = {
        DEMO_SRC: _demo_crew_lists,
        LIVE_BUMPS: live_bumps.get_crew_lists,
        OURCS: ourcs.get_crew_lists,
        NOOP: _noop_crew_lists,
    }
    
    def add_arguments(self, parser):
        
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
            choices = [self.LIVE_BUMPS, self.ANU, self.CAMFM, self.DEMO_SRC],
            help = f'The source of start order data (default: {self.LIVE_BUMPS} or {self.CAMFM})',
        )
        parser.add_argument(
            '--crew-lists',
            choices = [self.LIVE_BUMPS, self.OURCS, self.DEMO_SRC],
            help = f'The source of crew list data (default: {self.LIVE_BUMPS})',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Parse series and date/year inputs
        series = series_reverser[kwargs['series']]
        series_location = self.series_location_map[series]
        start_date = kwargs['date'] if kwargs['date'] else timezone.now().date() + timedelta(5)
        year = kwargs['year'] if kwargs['year'] else start_date.year
        
        # Parse data source inputs
        valid_event_sources = self.location_event_sources_map[series_location]
        event_source = valid_event_sources[0]
        if kwargs.get('source'):
            assert_error = 'Source is invalid for this location'
            assert kwargs['source'] in valid_event_sources, assert_error
            event_source = kwargs['source']
        
        valid_crew_list_sources = self.location_crew_list_sources_map[series_location]
        crew_list_source = valid_crew_list_sources[0]
        if kwargs.get('crew_lists'):
            assert_error = 'Crew lists are invalid for this location'
            assert kwargs['crew_lists'] in valid_crew_list_sources, assert_error
            crew_list_source = kwargs['crew_lists']
        
        logger.info('Creating a new game for {} {}, starting on {}'.format(
            series.label,
            year,
            start_date.isoformat(),
        ))
        logger.info('Using `{}` as the event source and `{}` for crew lists'.format(
            event_source,
            crew_list_source,
        ))
        
        # Create event and load data
        event, weds = create_event(series, year, start_date)
        
        event_source_function = self.event_source_function_map[event_source]
        utils.load_crew_rankings(event_source_function, weds)
        
        crew_lists_source_function = self.crew_list_source_function_map[crew_list_source]
        utils.load_crew_lists(crew_lists_source_function, event)
        
        logger.info('Created a new game for {} {}, starting on {}'.format(
            series.label,
            year,
            start_date.isoformat(),
        ))


def create_event(series, year, start_date):
    
    main_race_time = time(12, 00)
    saturday_race_time = main_race_time
    
    if series == EventSeries.DEMO:
        division_structure = {
            'mens_division_sizes': [12, 12, 12, 12, 12, 13],
            'womens_division_sizes': [12, 12, 12, 12, 13],
        }
    if series == EventSeries.TORPIDS and year == 2021:
        division_structure = {
            'mens_division_sizes': [9, 9, 9, 9, 9, 9, 10],
            'womens_division_sizes': [9, 9, 9, 9, 9, 9, 10],
        }
    elif series == EventSeries.TORPIDS:
        division_structure = {
            'mens_division_sizes': [12, 12, 12, 12, 12, 13],
            'womens_division_sizes': [12, 12, 12, 12, 13],
        }
    elif series == EventSeries.EIGHTS and year == 2022:
        main_race_time = time(12, 15)
        saturday_race_time = time(11, 15)
        division_structure = {
            'mens_division_sizes': [12, 12, 12, 12, 12, 12, 13],
            'womens_division_sizes': [12, 12, 12, 12, 12, 12, 11],
        }
    elif series == EventSeries.EIGHTS:
        saturday_race_time = time(11, 00)
        division_structure = {
            'mens_division_sizes': [13, 13, 13, 13, 13, 13, 14],
            'womens_division_sizes': [13, 13, 13, 13, 13, 14],
        }
    elif series == EventSeries.MAYS and year == 2022:
        main_race_time = time(13, 45)
        saturday_race_time = time(11, 45)
        division_structure = {
            'mens_division_sizes': [17, 17, 17, 17, 12],
            'womens_division_sizes': [17, 17, 17, 17, 6],
        }
    elif series == EventSeries.MAYS:
        main_race_time = time(13, 45)
        saturday_race_time = time(11, 45)
        division_structure = {
            'mens_division_sizes': [17, 17, 17, 17, 17, 6],
            'womens_division_sizes': [17, 17, 17, 17, 9],
        }
    
    event_tag = '{}{}'.format(series.label.lower(), year)
    event = models.Event.objects.create(
        id = 1 if series == EventSeries.DEMO else None,
        series = series,
        year = year,
        tag = event_tag,
        **division_structure,
    )
    
    first_day = create_days(event, start_date, main_race_time, saturday_race_time)
    return event, first_day


def create_days(event, start_date, main_race_time, saturday_race_time):
    
    weds = models.Day(
        event = event,
        name = 'Wednesday',
        date = start_date,
        first_race_time = main_race_time,
    )
    weds.save()
    
    event.days.create(
        name = 'Thursday',
        date = start_date + timedelta(1),
        first_race_time = main_race_time,
    )
    
    event.days.create(
        name = 'Friday',
        date = start_date + timedelta(2),
        first_race_time = main_race_time,
    )
    
    event.days.create(
        name = 'Saturday',
        date = start_date + timedelta(3),
        first_race_time = saturday_race_time,
    )
    
    event.days.create(
        name = 'Finish',
        date = start_date + timedelta(4),
    )
    
    return weds

