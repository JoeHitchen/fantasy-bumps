from datetime import datetime, timedelta

from .common import TORPIDS, EIGHTS, LENTS, MAYS, series_text_map


def anu_day_code(series: str, year: int, day_number: int) -> list[str]:
    """Provides the correct day code for loading data from Anu."""

    if (series, year) == (TORPIDS, 2021):
        return [['tue'], ['wed'], ['thu'], ['fri'], ['end']][day_number - 1]

    return [['wed', 'sta'], ['thu'], ['fri'], ['sat'], ['end']][day_number - 1]


def anu_data_url_template(series: str, year: int) -> str:
    """Generates the template for the dynamic part of Anu's data file's URLs."""

    if (series, year) == (TORPIDS, 2022):
        return '{}/{}{}{}{}.dat'

    return '{1}{2}{3}{4}.dat'


def ourcs_event_id(series: str, year: int) -> int:
    """Returns the OURCs event ID for historical events."""

    try:
        return {
            (TORPIDS, 2013): 103,
            (TORPIDS, 2017): 173,
            (EIGHTS, 2017): 174,
            (TORPIDS, 2018): 184,
            (EIGHTS, 2018): 186,
            (TORPIDS, 2019): 195,
            (EIGHTS, 2019): 198,
            (TORPIDS, 2021): 217,
            (TORPIDS, 2022): 229,
            (EIGHTS, 2022): 230,
            (TORPIDS, 2023): 239,
            (EIGHTS, 2023): 241,
            (EIGHTS, 2024): 253,
            (TORPIDS, 2025): 262,
        }[(series, year)]

    except KeyError:
        raise ValueError(f'No OURCs event mapped for {series_text_map.get(series)} {year}')


def camfm_event_id(series: str, year: int) -> int | None:
    """Returns the CamFM event ID for historical events."""

    event_id = {
        (LENTS, 2017): 1029,
        (MAYS, 2017): 1064,
        (LENTS, 2018): 1175,
        (MAYS, 2018): 1214,
        (LENTS, 2019): 1318,
        (MAYS, 2019): 1353,
        (LENTS, 2020): 1400,
        (LENTS, 2022): 2000,
        (MAYS, 2022): 3100,
    }.get((series, year), None)

    if year < datetime.now().year and not event_id:
        raise ValueError('Historical results not mapped for {} {}'.format(
            series_text_map.get(series),
            year,
        ))

    return event_id


def saturday_race_time_shift(series: str) -> timedelta:
    """The expected changes between the first race times on Saturday and other days."""

    return {
        EIGHTS: timedelta(hours = 1),
        LENTS: timedelta(hours = 1, minutes = 20),
        MAYS: timedelta(hours = 2),
    }.get(series, timedelta(0))

