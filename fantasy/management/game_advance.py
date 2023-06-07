from django.db import transaction

from integrations import types as integrations

from .. import models
from .. import game_tools as tools
from .commands import utils


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

