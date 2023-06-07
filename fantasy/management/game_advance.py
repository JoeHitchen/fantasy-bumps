import logging

from django.db import transaction
from django.utils import timezone
from django.core.mail import mail_admins

from integrations import types as integrations

from .. import models
from .. import game_tools as tools
from .commands import utils

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_advance')


def perform_advance(
    source_function: integrations.PositionFcn,
    event: models.Event,
    override_hold: bool = False,
) -> None:
    """Loads any new results and updates the game state accordingly."""
     
    # Get relevant days
    if event.active_day.is_racing_day and timezone.now() >= event.active_day.first_race:
        old_day = event.active_day  # Racing underway for active day
        new_day = event.active_day.next
    elif event.active_day.prev:
        old_day = event.active_day.prev  # No active racing but a previous day exists
        new_day = event.active_day
    else:
        logger.info(f'No new racing has occurred for {event}')  # Pre-event, no action required
        return
    
    
    # Check results required for new day
    if new_day.ranking.count():
        logger.info(f'Crew positions for the {new_day} of {event} are already loaded')
        return
    
    
    # Update records
    try:
        advance_core(old_day, source_function, override_hold)
        
    except models.Day.DoesNotExist:
        logger.info(f'{old_day} of {event} has already been advanced')
        
    except Exception as err:
        logger.error(f'An error occurred advancing {old_day} of {event}\n >> {err}')
        
        event.market_held_closed = True
        event.save()
        
        mail_admins(f'Game Advance Failed - {event}', (
            f'An unknown error occurred when advancing {old_day} of {event}.'
            + f'\n\n >> {err}'
            + '\n\nThe markets are held closed. '
            + "Hopefully it's an easy fix..."
        ), fail_silently = True)


@transaction.atomic
def advance_core(
    day: models.Day,
    source_function: integrations.PositionFcn,
    override_hold: bool = False,
) -> None:
    """The sensitive core of the game advance routine."""
    
    reject_for_hold_args = {'event__market_held_closed': False} if not override_hold else {}
    
    transaction_day = (
        models.Day.objects
        .select_for_update()
        .filter(**reject_for_hold_args)
        .get(id = day.id, advanced = False)
    )
    
    utils.load_crew_rankings(source_function, transaction_day.next)
    tools.roll_over_purchases(transaction_day)
    tools.evaluate_all_investments(transaction_day)
    
    transaction_day.advanced = True
    transaction_day.save()

