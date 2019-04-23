from unittest.mock import patch, PropertyMock

from . import models


def market_is_open(status):
    return patch.object(
        models.Day,
        'market_is_open',
        new_callable = PropertyMock,
        return_value = status,
    )

