from datetime import date, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone

from parsing import ourcs, live_bumps, anu, camfm

from ... import models
from ...constants import Series as EventSeries
from . import utils


class Command(BaseCommand):
    help = 'Creates a new event to play FantasyBumps against.'
    
    LIVE_BUMPS = 'live'
    ANU = 'anu'
    CAMFM = 'camfm'
    
    def add_arguments(self, parser):
        
        type_group = parser.add_mutually_exclusive_group()
        
        type_group.add_argument(
            '--demo',
            dest = 'type',
            action = 'store_const',
            const = EventSeries.DEMO,
            help = 'Create a Demo event. Requires an empty database and ignores year and date.',
        )
        type_group.add_argument(
            '--torpids',
            dest = 'type',
            action = 'store_const',
            const = EventSeries.TORPIDS,
            help = 'Create a Torpids event.',
        )
        type_group.add_argument(
            '--eights',
            dest = 'type',
            action = 'store_const',
            const = EventSeries.EIGHTS,
            help = 'Create a Summer Eights event.',
        )
        type_group.add_argument(
            '--mays',
            dest = 'type',
            action = 'store_const',
            const = EventSeries.MAYS,
            help = 'Create a May Bumps event.',
        )
        
        date_group = parser.add_mutually_exclusive_group()
        
        date_group.add_argument(
            '--date',
            type = date.fromisoformat,
            help = 'The start date of the event.',
        )
        date_group.add_argument(
            '--year',
            type = int,
            help = 'The year of the event to create/simulate.',
        )
        
        parser.add_argument(
            '--source',
            default = self.LIVE_BUMPS,
            choices = [self.LIVE_BUMPS, self.ANU, self.CAMFM],
            help = 'The source of start order data (default: live)',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Parse arguments
        if not kwargs['type']:
            raise CommandError('Must supply event type flag.')
        
        series = kwargs['type']
        is_demo_event = series == EventSeries.DEMO
        
        if kwargs['date'] and not is_demo_event:
            start_date = kwargs['date']
        else:
            start_date = timezone.now() + timedelta(5)
        
        year = kwargs['year'] if kwargs['year'] else start_date.year
        source = kwargs.get('source', self.LIVE_BUMPS)
        
        event, weds = create_event(is_demo_event, series, year, start_date)
        
        # Demo event with OURCs crew lists
        if is_demo_event:
            call_command('loaddata', 'demo_start_day1')
            return
        
        # Bumps event
        if source == self.LIVE_BUMPS:
            source_function = live_bumps.get_positions
        elif source == self.CAMFM:
            source_function = camfm.get_positions
        else:
            source_function = anu.get_positions
        
        utils.load_crew_rankings(source_function, weds)
        
        crew_list_source = None if source == self.CAMFM else ourcs.get_crew_lists
        
        if crew_list_source:
            utils.load_crew_lists(crew_list_source, event)


def create_event(source, series, year, start_date):
    
    main_race_time = time(12, 00)
    saturday_race_time = main_race_time
    
    # Demo events
    if source:
    
        if models.Event.objects.exists():
            raise CommandError('Cannot create a Demo event if the database is not empty!')
        
        call_command('loaddata', 'demo_crews', 'demo_event')
        event = models.Event.objects.first()
        year = event.year
    
    # Bumps events
    else:
        
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
                'mens_division_sizes': [13, 13, 13, 13, 13, 13, 14],
                'womens_division_sizes': [13, 13, 13, 13, 13, 14],
            }
        elif series == EventSeries.EIGHTS:
            saturday_race_time = time(11, 00)
            division_structure = {
                'mens_division_sizes': [12, 12, 12, 12, 12, 12, 13],
                'womens_division_sizes': [12, 12, 12, 12, 12, 12, 11],
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

