from unittest.mock import patch, Mock, PropertyMock
from datetime import time, datetime, timedelta
from typing import Callable, ParamSpec, TypeVar, Concatenate
import zoneinfo

from django.utils import timezone

from core.settings import TIME_ZONE

from . import models

_Params = ParamSpec('_Params')
_RetType = TypeVar('RetType_')
_OriginalFunc = Callable[_Params, _RetType]
_DecoratedFunc = Callable[Concatenate[Mock, _Params], _RetType]

Patch = Callable[[_OriginalFunc], _DecoratedFunc]


def localtime_time(time: time, shift: timedelta = timedelta(0)) -> Patch:
    """Replace the time component of the `timezone.localtime()` function with the time provided.
    
    Cannot apply timedelta to time when called, since `time` + `timedelta` is not a permitted
    operation.
    """
    
    localtime = datetime.combine(
        timezone.localtime().date(),
        time,
        tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
    ) + shift
    
    return patch('django.utils.timezone.localtime', return_value = localtime)


def market_opens(datetime: datetime) -> Patch:
    return patch.object(
        models.Day,
        'market_opens',
        new_callable = PropertyMock,
        return_value = datetime,
    )


def market_closes(datetime: datetime) -> Patch:
    return patch.object(
        models.Day,
        'market_closes',
        new_callable = PropertyMock,
        return_value = datetime,
    )


def market_is_open(status: bool) -> Patch:
    return patch.object(
        models.Day,
        'market_is_open',
        new_callable = PropertyMock,
        return_value = status,
    )


team_get_crew: Patch = patch(
    'fantasy.models.Team.get_crew',
    autospec = True,
    side_effect = lambda team, day, gender: (team, day, gender),
)

