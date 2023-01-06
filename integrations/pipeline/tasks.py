import traceback
import logging

from celery.schedules import crontab

from core import tasks_app

from . import common, utils


logger = logging.getLogger('BumpsTasks')
logger.setLevel('INFO')


@tasks_app.task
def anu_to_live_bumps(series, first_day, gender):
    """A light wrapper to provide better error logging."""
    
    logging.info("Piping Anu's results to LiveBumps\n  Arguments: {} {} {}".format(
        series,
        first_day,
        gender,
    ))
    
    try:
        utils.anu_to_live_bumps(series, first_day, gender)
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


