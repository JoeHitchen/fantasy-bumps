from unittest.mock import patch, PropertyMock

from . import models


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

