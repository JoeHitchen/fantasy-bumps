from datetime import date, time, datetime, timedelta
import zoneinfo
import logging

from django.utils import timezone
from django.db import transaction

from core.settings import TIME_ZONE
from integrations.types import StartOrder
from integrations import magic, anu_dat, live_bumps

from ..constants import Series, Genders, timings
from .. import models
from .commands.utils import create_crew_tuple_map

logging.basicConfig(level = logging.INFO)


@transaction.atomic()
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
        initial_market_open = datetime.combine(
            start_date - timedelta(3),  # Sunday before racing
            timings.MARKET_INITIAL,
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        ),
    )
    create_days(
        event,
        start_date,
        ordered_divisions[-1]['race_time'],
        ordered_divisions[0]['race_time'],
    )
    create_gendered_crew_positions(event, mens_divisions)
    create_gendered_crew_positions(event, womens_divisions)
    return event


def create_days(
    event: models.Event,
    start_date: date,
    first_race_time: time,
    last_race_time: time,
) -> models.Day:
    """Creates days for a standard four-day bumps regatta."""

    weds = models.Day(
        event = event,
        name = 'Wednesday',
        date = start_date,
        first_race_time = first_race_time,
        last_race_time = last_race_time,
    )
    weds.save()
    assert weds.first_race and weds.last_race  # MyPy purposes

    event.days.create(
        name = 'Thursday',
        date = start_date + timedelta(1),
        first_race_time = first_race_time,
        last_race_time = last_race_time,
    )

    event.days.create(
        name = 'Friday',
        date = start_date + timedelta(2),
        first_race_time = first_race_time,
        last_race_time = last_race_time,
    )

    saturday_shift = magic.saturday_race_time_shift(Series(event.series))
    event.days.create(
        name = 'Saturday',
        date = start_date + timedelta(3),
        first_race_time = (weds.first_race - saturday_shift).time(),
        last_race_time = (weds.last_race - saturday_shift).time(),
    )

    event.days.create(
        name = 'Finish',
        date = start_date + timedelta(4),
    )

    return weds


def create_gendered_crew_positions(event: models.Event, divisions: StartOrder) -> None:
    """Greates crew positions for one gender's start order."""

    flattened_crews = [
        models.Crew.make_tuple(*crew)
        for division in divisions
        for crew, _ in division['crews']
    ]
    crew_map = create_crew_tuple_map(flattened_crews)

    models.Position.objects.bulk_create([
        models.Position(
            day = event.first_day,
            crew = crew_map[crew],
            rank = rank,
        )
        for rank, crew in enumerate(flattened_crews, start = 1)
    ])


def update_live_bumps(event: models.Event, gender: Genders) -> live_bumps.WriteOutcome:
    """Loads crew positions from Anu's data files and pushes them to Live Bumps."""

    logger = logging.getLogger('fantasy.live_pipeline')
    logger.info('Updating Live Bumps for {} ({})'.format(event, gender.label))

    now = timezone.localtime(timezone.now())
    active_days = list(event.days.filter(date__lte = now + timedelta(1)))
    if len(active_days) < 2:
        return (0, 0, 0)

    # Load positions
    positions_by_day = []
    for day_number, day in enumerate(active_days, 1):
        positions_by_day.append(anu_dat.get_positions_by_gender(
            event.series,
            event.year,
            gender,
            day_number,
        ))

    # Prune unraced crews
    if active_days[-1].date > now.date():

        start_order = anu_dat.get_start_order_by_gender(
            event.series,
            event.year,
            gender,
            len(active_days) - 1,
        )
        unraced_crews = [
            crew for division in start_order for crew, _ in division['crews']
            if division['race_time'] >= now.time()
        ]
        for crew in unraced_crews:
            del positions_by_day[-1][crew]

    output = live_bumps.write_positions(event.series, event.year, positions_by_day)
    logger.info('Updated Live Bumps for {} ({})'.format(event, gender.label))
    return output

