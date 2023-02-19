from datetime import timedelta
import math as maths

from django.utils import timezone
from django_q.tasks import Schedule

from fantasy import models
from fantasy.constants import Series, Genders
from fantasy.management.commands.update_live_bumps import Command as UpdateLiveBumps

series_reverser = {series.label.lower(): series for series in Series}
gender_reverser = {gender.label.lower(): gender for gender in Genders}


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
    
    now = timezone.now()
    last_update = event.last_racing_day.first_race + timedelta(hours = 12)
    repeats = maths.ceil((last_update - now).total_seconds() / 60)
    
    Schedule.objects.update_or_create(
        func = 'fantasy.management.tasks.update_live_bumps',
        kwargs = {
            'series': event.get_series_display().lower(),
            'year': event.year,
            'gender': Genders.MEN.label.lower(),
        },
        defaults = {'schedule_type': Schedule.MINUTES, 'repeats': repeats},
    )
    Schedule.objects.update_or_create(
        func = 'fantasy.management.tasks.update_live_bumps',
        kwargs = {
            'series': event.get_series_display().lower(),
            'year': event.year,
            'gender': Genders.WOMEN.label.lower(),
        },
        defaults = {'schedule_type': Schedule.MINUTES, 'repeats': repeats},
    )

