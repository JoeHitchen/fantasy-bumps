from datetime import timedelta

from ..constants import Series


def saturday_race_time_shift(series: Series) -> timedelta:
    """The expected changes between the first race times on Saturday and other days."""
    
    return {
        Series.EIGHTS: timedelta(hours = 1),
        Series.LENTS: timedelta(hours = 1, minutes = 20),
        Series.MAYS: timedelta(hours = 2),
    }.get(series, timedelta(0))

