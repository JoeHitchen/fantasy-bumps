from datetime import date, timedelta
import traceback
import logging

from django.utils import timezone
from celery.schedules import crontab

from core import tasks_app

from . import common, anu, live


logger = logging.getLogger('BumpsTasks')
logger.setLevel('INFO')


def _anu_to_live_bumps(series, first_day, gender):
    """Loads the latest data from Anu's data files and pushes the results to Live Bumps."""
    
    # Get event days
    first_day = date.fromisoformat(first_day)
    days = [first_day + timedelta(i) for i in range(5)]
    
    active_days = [day for day in days if day <= timezone.now().date() + timedelta(1)]
    if len(active_days) < 2:
        return
    
    # Get event rankings
    rankings = []
    for day in active_days:
        
        start_order = anu.load_start_order(series, day, gender, day == days[-1])
        rankings.append(common.start_order_to_ranking(start_order))
        if not day == active_days[-1]:
            prev_start_order = start_order
    
    # Prune un-raced crews
    unraced_divisions = [
        division for division in prev_start_order
        if division['race_time'] >= timezone.now()
    ]
    unraced_crews = [
        (club, gender, crew_rank) for division in unraced_divisions
        for club, gender, crew_rank, _ in division['crews']
    ]
    for crew in unraced_crews:
        del rankings[-1][crew]
    
    # Update Live Bumps
    live.post_all_rankings(series, first_day.year, rankings)


@tasks_app.task
def anu_to_live_bumps(series, first_day, gender):
    """A light wrapper to provide better error logging."""
    
    logging.info("Piping Anu's results to LiveBumps\n  Arguments: {} {} {}".format(
        series,
        first_day,
        gender,
    ))
    
    try:
        _anu_to_live_bumps(series, first_day, gender)
    except Exception:
        logger.error("Error piping Anu's results to LiveBumps\n  Arguments: {} {} {}\n  {}".format(
            series,
            first_day,
            gender,
            '\n  '.join(traceback.format_exc().split('\n')),
        ))
    else:
        logger.info("Completed piping Anu's results to LiveBumps\n  Arguments: {} {} {}".format(
            series,
            first_day,
            gender,
        ))


@tasks_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    
    sender.add_periodic_task(
        crontab(minute = '*/1'),
        anu_to_live_bumps.s(common.EIGHTS, '2022-05-25', common.MEN),
    )
    sender.add_periodic_task(
        crontab(minute = '*/1'),
        anu_to_live_bumps.s(common.EIGHTS, '2022-05-25', common.WOMEN),
    )


