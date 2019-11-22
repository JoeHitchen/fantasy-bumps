from datetime import date, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone

from parsing import ourcs, live_bumps

from ... import models
from ...constants import series as event_series
from ...game_tools import get_all_crews, add_rankings, add_athletes


class Command(BaseCommand):
    help = 'Creates a new event to play FantasyBumps against.'

    def add_arguments(self, parser):
        
        type_group = parser.add_mutually_exclusive_group()
        
        type_group.add_argument(
            '--demo',
            dest = 'type',
            action = 'store_const',
            const = event_series.DEMO,
            help = 'Create a Demo event. Requires an empty database and ignores year and date.',
        )
        type_group.add_argument(
            '--torpids',
            dest = 'type',
            action = 'store_const',
            const = event_series.TORPIDS,
            help = 'Create a Torpids event.',
        )
        type_group.add_argument(
            '--eights',
            dest = 'type',
            action = 'store_const',
            const = event_series.EIGHTS,
            help = 'Create a Summer Eights event.',
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
    
    
    def handle(self, *args, **kwargs):
        
        # Parse arguments
        if not kwargs['type']:
            raise CommandError('Must supply event type flag.')
        
        series = kwargs['type']
        is_demo_event = series == event_series.DEMO
        
        if kwargs['date'] and not is_demo_event:
            start_date = kwargs['date']
        else:
            start_date = timezone.now() + timedelta(5)
        
        year = kwargs['year'] if kwargs['year'] else start_date.year
        
        # Demo events
        if is_demo_event:
        
            if models.Event.objects.exists():
                raise CommandError('Cannot create a Demo event if the database is not empty!')
            
            call_command('loaddata', 'demo_crews', 'demo_event')
            event = models.Event.objects.first()
            year = event.year
        
        # Bumps events
        else:
            division_structure = {
                event_series.TORPIDS: {
                    'mens_divisions': 6,
                    'womens_divisions': 5,
                    'boats_per_division': 12,
                },
                event_series.EIGHTS: {
                    'mens_divisions': 7,
                    'womens_divisions': 6,
                    'boats_per_division': 13,
                },
            }[series]
            
            event_tag = '{}{}'.format(
                {
                    event_series.TORPIDS: 'torpids',
                    event_series.EIGHTS: 'eights',
                }[series],
                year,
            )
            event = models.Event.objects.create(
                series = series,
                year = year,
                tag = event_tag,
                **division_structure,
            )
        
        
        # Add days
        weds = create_days(event, start_date)
        
        
        # Demo event with OURCs crew lists
        if is_demo_event:
            call_command('loaddata', 'demo_start_day1')
            crews = {
                (crew.club, crew.gender, crew.rank): crew
                for crew in models.Crew.objects.all()
            }
            
            crew_lists = ourcs.get_crew_lists(event_id = 103)
            
            add_athletes(event, crews, crew_lists)
            return
        
        # Bumps event via Live Bumps
        results = live_bumps.get_results(series, year)
        crews = get_all_crews(results.keys())
        add_rankings(weds, crews, results)
        add_athletes(event, crews, live_bumps.get_crew_lists(series, year))


def create_days(event, start_date):
    
    weds = models.Day(
        event = event,
        name = 'Wednesday',
        date = start_date,
        first_race_time = time(12, 00),
    )
    weds.save()
    
    event.days.create(
        name = 'Thursday',
        date = start_date + timedelta(1),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Friday',
        date = start_date + timedelta(2),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Saturday',
        date = start_date + timedelta(3),
        first_race_time = time(12, 00),
    )
    
    event.days.create(
        name = 'Finish',
        date = start_date + timedelta(4),
    )
    
    return weds

