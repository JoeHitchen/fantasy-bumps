from datetime import timedelta
import json

from celery import shared_task
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from fantasy import models
from fantasy.constants import Series, Genders
from fantasy.management.commands.update_live_bumps import Command as UpdateLiveBumps

series_reverser = {series.label.lower(): series for series in Series}
gender_reverser = {gender.label.lower(): gender for gender in Genders}


@shared_task
def update_live_bumps(**kwargs):
    """A light wrapper that calls the Update Live Bumps management command."""
    
    return UpdateLiveBumps().perform_update(
        models.Event.objects.get(
            series = series_reverser[kwargs['series']],
            year = kwargs['year'],
        ),
        gender_reverser[kwargs['gender']],
    )


def schedule_live_bumps_updates(event):
    """Schedules a minutely update of Live Bumps until after the expected end of racing."""
    
    every_minute, _ = IntervalSchedule.objects.get_or_create(
        period = IntervalSchedule.MINUTES,
        every = 1,
    )
    
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
                'expires': event.last_racing_day.first_race + timedelta(hours = 12),
            },
        )

