from django.db import models as db

from ..constants import GENDERS_OVERALL, Genders, Series
from .. import models


def award_event_trophies(event: models.Event) -> None:
    """Awards the trophies for an event."""

    rankings = (
        event.fantasies
        .select_related('team', 'team__user')
        .extend_financials()
        .rank_by(GENDERS_OVERALL)
    )
    total_entries = rankings.count()

    if total_entries > 0:
        rankings[0].team.trophies.create(
            event = event,
            type = models.Trophy.Types.GOLDEN_SWAN,
        )
    if total_entries > 1:
        rankings[1].team.trophies.create(
            event = event,
            type = models.Trophy.Types.SILVER_SWAN,
        )
    if total_entries > 2:
        rankings[2].team.trophies.create(
            event = event,
            type = models.Trophy.Types.BRONZE_SWAN,
        )

    mens_winner = (
        event.fantasies
        .select_related('team', 'team__user')
        .extend_financials()
        .rank_by(Genders.MEN)
    ).first()
    if mens_winner:
        mens_winner.team.trophies.create(
            event = event,
            type = models.Trophy.Types.GOLDEN_COB,
        )

    womens_winner = (
        event.fantasies
        .select_related('team', 'team__user')
        .extend_financials()
        .rank_by(Genders.WOMEN)
    ).first()
    if womens_winner:
        womens_winner.team.trophies.create(
            event = event,
            type = models.Trophy.Types.GOLDEN_PEN,
        )

    cygnet_rankings = rankings.annotate(
        previous_entries = db.Count('id', filter = db.Q(team__entries__event_id__lt = event.id)),
    ).filter(previous_entries = 0)
    if cygnet_rankings.count() > 0:
        cygnet_rankings[0].team.trophies.create(
            event = event,
            type = models.Trophy.Types.GOLDEN_CYGNET,
        )

    steady_swan_rankings = rankings.filter(has_subs = False)
    if steady_swan_rankings.count() > 0:
        steady_swan_rankings[0].team.trophies.create(
            event = event,
            type = models.Trophy.Types.STEADY_SWAN,
        )

    teams_to_update = []
    for rank, ranking in enumerate(rankings[0:10], start = 1):
        ranking.team.top_five_finisher = rank <= 5
        ranking.team.top_ten_finisher = True
        teams_to_update.append(ranking.team)

    models.Team.objects.bulk_update(
        teams_to_update,
        ['top_five_finisher', 'top_ten_finisher'],
    )


def identify_new_veterans(event: models.Event) -> int:
    """Identifies the new veterans after an event and returns how many new veterans there are."""

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

