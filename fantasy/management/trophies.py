from django.db import models as db

from ..constants import Series
from .. import models


def assign_new_veterans(event: models.Event) -> int:
    """Assigns the new veterans for an event and returns the number of new veterans."""

    oxford_series = [Series.TORPIDS, Series.EIGHTS]
    cambridge_series = [Series.MAYS, Series.LENTS]

    if event.series in oxford_series:
        veteran_property = 'oxford_veteran'
        location_filter = db.Q(entries__event__series__in = oxford_series)

    elif event.series in cambridge_series:
        veteran_property = 'cambridge_veteran'
        location_filter = db.Q(entries__event__series__in = cambridge_series)
    else:
        raise ValueError(f'Unable to assign veterans for {event.series}')

    return (
        models.Team.objects
        .filter(**{veteran_property: False})
        .annotate(entries_count = db.Count('entries', filter = location_filter))
        .filter(entries_count__gte = 5)
        .update(**{veteran_property: True})
    )

