from unittest.mock import patch
from datetime import datetime, time

from django.utils import timezone


def current_time(hour, minute = 0, second = 0):
    """Changes the time returned by timezone.now() to that specified."""
    
    now_old = timezone.now()
    now_new = datetime.combine(
        now_old.date(),
        time(hour, minute, second),
        tzinfo = now_old.tzinfo,
    )
    
    return patch('django.utils.timezone.now', return_value = now_new)

