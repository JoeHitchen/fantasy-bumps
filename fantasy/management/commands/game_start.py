from datetime import date, time, timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from ... import models
from ...constants import Series as EventSeries
from . import utils, parsers

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_start')


series_reverser = {series.label.lower(): series for series in EventSeries}


class Command(BaseCommand):
    help = 'Creates a new event to play FantasyBumps against.'
    
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
            choices = [
                source.value
                for sources in parsers.location_event_sources_map.values()
                for source in sources
            ],
            help = 'The source of start order data (default: {} or {})'.format(
                parsers.location_event_sources_map[parsers.Locations.OXFORD][0],
                parsers.location_event_sources_map[parsers.Locations.CAMBRIDGE][0],
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
                parsers.location_crew_list_sources_map[parsers.Locations.OXFORD][0],
            ),
        )
    
    
    def handle(self, *args, **kwargs):
        
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
        event_source = parsers.get_validated_event_source(series_location, kwargs.get('source'))
        crew_list_source = parsers.get_validated_crew_list_source(
            series_location,
            kwargs.get('crew_lists'),
        )
        logger.info('Using `{}` as the event source and `{}` for crew lists'.format(
            event_source['source'],
            crew_list_source['source'],
        ))
        
        # Create event and load data
        event, weds = create_event(series, year, start_date)
        utils.load_crew_rankings(event_source['function'], weds)
        utils.load_crew_lists(crew_list_source['function'], event)
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

