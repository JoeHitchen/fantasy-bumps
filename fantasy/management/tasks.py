from datetime import datetime, timedelta
import json
import logging

from django_celery_beat.models import IntervalSchedule, PeriodicTask
from django.utils import timezone
from django.db.models import F

from core.tasks import app
from fantasy import models
from fantasy.constants import Series, Locations, Genders, money
from fantasy.management.commands import parsers
from fantasy.management.commands.update_live_bumps import Command as UpdateLiveBumps
from integrations.live_bumps import WriteOutcome as LiveBumpsWriteOutcome

from . import game_advance

series_reverser = {series.label.lower(): series for series in Series}
gender_reverser = {gender.label.lower(): gender for gender in Genders}

logger = logging.getLogger('fantasy.tasks')


@app.task
def perform_game_advance(series: str, year: int, source: str = '') -> None:
    """A task wrapper for performing game advances for a given event."""
    
    game_advance.perform_advance(
        models.Event.objects.get(series = series_reverser[series], year = year),
        parsers.get_validated_position_source(Locations.OXFORD, source)['function'],
    )


def boost_crabs(
    team: models.Team,
    event: models.Event,
    amounts: tuple[int, int],
    apply_at: datetime = timezone.now(),
) -> None:
    """A wrapper for the boost crabs task to be applied at a certain time."""
    boost_crabs_task.apply_async((str(team), event.tag, amounts), eta = apply_at)


@app.task
def boost_crabs_task(team_name: str, event_tag: str, amounts: tuple[int, int]) -> None:
    """Provides a crab boost to a given team for an event.
    
    *Assumes that the target team is on the starting budget.*
    """
    
    logger.info('Boosting {} for {} by {} (men) & {} (women)'.format(
        team_name,
        event_tag,
        *amounts,
    ))
    
    outcome = models.GameEntry.objects.filter(
        team__user__username = team_name,
        event__tag = event_tag,
        mens_budget = money.INITIAL_BALANCE,  # Protection against double execution
        womens_budget = money.INITIAL_BALANCE,
    ).update(
        mens_budget = F('mens_budget') + amounts[0],
        womens_budget = F('womens_budget') + amounts[1],
        mens_balance = F('mens_balance') + amounts[0],
        womens_balance = F('womens_balance') + amounts[1],
    )
    
    logger.info(f'Boost of {team_name} for {event_tag} ' + ('successful' if outcome else 'failed'))


@app.task
def update_live_bumps(series: str, year: int, gender: str) -> LiveBumpsWriteOutcome:
    """A light wrapper that calls the Update Live Bumps management command."""
    
    return UpdateLiveBumps().perform_update(
        models.Event.objects.get(series = series_reverser[series], year = year),
        gender_reverser[gender],
    )


def schedule_live_bumps_updates(event: models.Event) -> None:
    """Schedules a minutely update of Live Bumps until after the expected end of racing."""
    
    every_minute, _ = IntervalSchedule.objects.get_or_create(
        period = IntervalSchedule.MINUTES,
        every = 1,
    )
    assert event.last_racing_day.first_race  # MyPy purposes
    
    for gender in Genders:
        PeriodicTask.objects.update_or_create(
            task = 'fantasy.management.tasks.update_live_bumps',
            kwargs = json.dumps({
                'series': event.get_series_display().lower(),
                'year': event.year,
                'gender': gender.label.lower(),
            }),
            defaults = {
                'name': 'Live Bumps // {} {}'.format(event, gender.label),
                'interval': every_minute,
                'expires': event.last_racing_day.last_race + timedelta(hours = 6),
            },
        )

