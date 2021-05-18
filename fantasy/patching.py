from unittest.mock import patch, PropertyMock
from datetime import datetime, timedelta

from django.utils import timezone
import pytz

from core.settings import TIME_ZONE

from . import models


def localtime_time(time, shift = timedelta(0)):
    """Replace the time component of the `timezone.localtime()` function with the time provided.
    
    Cannot apply timedelta to time when called, since `time` + `timedelta` is not a permitted
    operation.
    """
    
    naive = datetime.combine(
        timezone.localtime().date(),
        time,
    ) + shift
    
    return patch(
        'django.utils.timezone.localtime',
        return_value = pytz.timezone(TIME_ZONE).localize(naive),
    )


def market_opens(datetime):
    return patch.object(
        models.Day,
        'market_opens',
        new_callable = PropertyMock,
        return_value = datetime,
    )


def market_closes(datetime):
    return patch.object(
        models.Day,
        'market_closes',
        new_callable = PropertyMock,
        return_value = datetime,
    )


def market_is_open(status):
    return patch.object(
        models.Day,
        'market_is_open',
        new_callable = PropertyMock,
        return_value = status,
    )


team_get_crew = patch(
    'fantasy.models.Team.get_crew',
    autospec = True,
    side_effect = lambda team, day, gender: (team, day, gender),
)

