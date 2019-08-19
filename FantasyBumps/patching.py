from unittest.mock import patch, PropertyMock
from datetime import datetime, timedelta

from django.utils import timezone

from . import models


def timezone_now_time(time, shift = timedelta(0)):
    
    now = timezone.now()
    
    return patch(
        'django.utils.timezone.now',
        return_value = datetime.combine(
            now.date(),
            time,
            tzinfo = now.tzinfo,
        ) + shift,
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

