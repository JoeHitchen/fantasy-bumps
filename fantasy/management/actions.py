from datetime import date, time, timedelta

from integrations.types import StartOrder
from integrations import magic

from ..constants import Series, Genders
from .. import models
from .commands.utils import create_crew_tuple_map


def create_event(
    series: Series,
    year: int,
    start_date: date,
    start_order: StartOrder,
) -> models.Event:
    """Creates an event. days, and starting positions for an event."""
    
    ordered_divisions = sorted(start_order, key = lambda div: div['race_time'], reverse = True)
    mens_divisions = [div for div in ordered_divisions if div['gender'] == Genders.MEN]
    womens_divisions = [div for div in ordered_divisions if div['gender'] == Genders.WOMEN]
    
    event = models.Event.objects.create(
        series = series,
        year = year,  # Can't use start_date.year to support historical events
        tag = f'{series.label.lower()}{year}',
        mens_division_sizes = [div['size'] for div in mens_divisions],
        womens_division_sizes = [div['size'] for div in womens_divisions],
    )
    create_days(event, start_date, ordered_divisions[-1]['race_time'])
    create_gendered_crew_positions(event, mens_divisions)
    create_gendered_crew_positions(event, womens_divisions)
    return event


def create_days(event: models.Event, start_date: date, main_race_time: time) -> models.Day:
    """Creates days for a standard four-day bumps regatta."""
    
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
    
    saturday_shift = magic.saturday_race_time_shift(Series(event.series))
    event.days.create(
        name = 'Saturday',
        date = start_date + timedelta(3),
        first_race_time = (weds.first_race - saturday_shift).time(),
    )
    
    event.days.create(
        name = 'Finish',
        date = start_date + timedelta(4),
    )
    
    return weds


def create_gendered_crew_positions(event: models.Event, divisions: StartOrder) -> None:
    """Greates crew positions for one gender's start order."""
    
    flattened_crews = [crew[0] for division in divisions for crew in division['crews']]
    crew_map = create_crew_tuple_map(flattened_crews)
    
    models.Position.objects.bulk_create([
        models.Position(
            day = event.first_day,
            crew = crew_map[crew],
            rank = rank,
        )
        for rank, crew in enumerate(flattened_crews, start = 1)
    ])


