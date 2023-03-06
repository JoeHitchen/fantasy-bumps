from datetime import timedelta

from .common import TORPIDS, EIGHTS, LENTS, MAYS


def anu_day_code(series: str, year: int, day_number: int) -> str:
    """Provides the correct day code for loading data from Anu."""
    
    if (series, year) == (TORPIDS, 2021):
        return ['tue', 'wed', 'thu', 'fri', 'end'][day_number - 1]
    
    return ['wed', 'thu', 'fri', 'sat', 'end'][day_number - 1]
    


def saturday_race_time_shift(series: str) -> timedelta:
    """The expected changes between the first race times on Saturday and other days."""
    
    return {
        EIGHTS: timedelta(hours = 1),
        LENTS: timedelta(hours = 1, minutes = 20),
        MAYS: timedelta(hours = 2),
    }.get(series, timedelta(0))

