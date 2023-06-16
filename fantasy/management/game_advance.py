from typing import TypedDict
import logging

from django.db import models as db, transaction
from django.utils import timezone
from django.core.mail import mail_admins

from integrations import types as integrations
from core.tests import exists

from ..constants import Genders
from .. import models, utils
from .commands import utils as mgmt_utils

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.game_advance')


class CrewPayout(TypedDict):
    value_change: int
    payout: int


def perform_advance(
    event: models.Event,
    source_function: integrations.PositionFcn,
    override_hold: bool = False,
) -> bool:
    """Loads any new results and updates the game state accordingly."""
     
    # Get relevant days
    if event.active_day.first_race and timezone.now() >= event.active_day.first_race:
        old_day = event.active_day  # Racing underway for active day
        new_day = exists(event.active_day.next)
    elif event.active_day.prev:
        old_day = event.active_day.prev  # No active racing but a previous day exists
        new_day = event.active_day
    else:
        logger.info(f'No new racing has occurred for {event}')  # Pre-event, no action required
        return False
    
    
    # Check results required for new day
    if new_day.ranking.count():
        logger.info(f'Crew positions for the {new_day} of {event} are already loaded')
        return False
    
    
    # Update records
    try:
        
        reject_for_hold_args = {'event__market_held_closed': False} if not override_hold else {}
        
        with transaction.atomic():
            transaction_day = (
                models.Day.objects
                .select_for_update()
                .filter(**reject_for_hold_args)
                .get(id = old_day.id, advanced = False)
            )
            
            mgmt_utils.load_crew_rankings(source_function, exists(transaction_day.next))
            roll_over_purchases(transaction_day)
            evaluate_investments(transaction_day)
            
            transaction_day.advanced = True
            transaction_day.save()
        
            event.market_held_closed = False
            event.save()
        
        return True
        
    except models.Day.DoesNotExist:
        logger.info(f'{old_day} of {event} has already been advanced')
        
    except Exception as err:
        logger.exception(f'An error occurred advancing {old_day} of {event}\n >> {err}')
        
        event.market_held_closed = True
        event.save()
        
        mail_admins(f'Game Advance Failed - {event}', (
            f'An unknown error occurred when advancing {old_day} of {event}.'
            + f'\n\n >> {err}'
            + '\n\nThe markets are held closed. '
            + "Hopefully it's an easy fix..."
        ), fail_silently = True)
    
    return False


def roll_over_purchases(day: models.Day) -> None:
    """Creates a copy of all purchase records for today on the next day.
    
    MAX four queries. Recommend fetching day with select_related.
    """
    
    models.Purchase.objects.bulk_create([
        models.Purchase(
            team = purchase.team,
            day = day.next,
            crew = purchase.crew,
            seat = purchase.seat,
            athlete = purchase.athlete,
        )
        for purchase in day.purchases.select_related().all()
    ])


def evaluate_investments(day: models.Day) -> None:
    """Update entered teams budgets for changes in crew value from places gained/lost on day."""
    
    def purchases_prefetch(day: models.Day, gender: Genders, target: str) -> db.Prefetch:
        """Prefetch a gendered crew list for day, and set to target attribute on Team model."""
        return db.Prefetch(
            'team__purchases',
            (
                models.Purchase.objects
                .filter(day = day, crew__gender = gender)
                .select_related('day', 'crew')
            ),
            to_attr = target,
        )
    
    
    def update_entry_with_investment_outcome(entry: models.GameEntry) -> None:
        """Updates a GameEntry object's financials in-memory, but does not on the database."""
        
        # Crew appreciation/depreciation
        entry.mens_budget += sum(
            payout_matrix[purchase.crew]['value_change']
            for purchase in entry.team.mens_crew
        )
        entry.womens_budget += sum(
            payout_matrix[purchase.crew]['value_change']
            for purchase in entry.team.womens_crew
        )
        
        # Payouts
        men_have_all_seats = utils.has_all_seats(entry.team.mens_crew, all_seats)
        women_have_all_seats = utils.has_all_seats(entry.team.womens_crew, all_seats)
        if men_have_all_seats and women_have_all_seats:
            
            mens_payout = sum(
                payout_matrix[purchase.crew]['payout']
                for purchase in entry.team.mens_crew
            )
            entry.mens_budget += mens_payout
            entry.mens_balance += mens_payout
            
            womens_payout = sum(
                payout_matrix[purchase.crew]['payout']
                for purchase in entry.team.womens_crew
            )
            entry.womens_budget += womens_payout
            entry.womens_balance += womens_payout
    
    
    # Preparation
    payout_matrix = create_payout_matrix(day)
    all_seats = list(models.Seat.objects.all())
    
    # Main routine
    entries = (
        models.GameEntry.objects
        .select_related('team')
        .filter(event = day.event)
        .prefetch_related(
            purchases_prefetch(day, Genders.MEN, 'mens_crew'),
            purchases_prefetch(day, Genders.WOMEN, 'womens_crew'),
        )
    )
    
    for entry in entries:
        update_entry_with_investment_outcome(entry)
    
    models.GameEntry.objects.bulk_update(
        entries,
        [
            'mens_budget',
            'womens_budget',
            'mens_balance',
            'womens_balance',
        ],
    )


def create_payout_matrix(day: models.Day) -> dict[models.Crew, CrewPayout]:
    """Calculates the value change and payout for every crew racing on the day provided.
    
    Optimised when:
        select_related called when retrieving day
        day.next has been set
    """
    
    # Retrieve crews racing
    crews = (
        models.Crew.objects
        .filter(positions__day = day)
        .prefetch_related(
            db.Prefetch(
                'positions',
                models.Position.objects.filter(day = day),
                to_attr='posn_old',
            ),
            db.Prefetch(
                'positions',
                models.Position.objects.filter(day = day.next),
                to_attr='posn_new',
            ),
        )
    )
    
    # Generate payout matrix
    return {
        crew: utils.payout_by_day_gender_positions(
            day,
            crew.gender,
            crew.posn_old[0].rank,
            crew.posn_new[0].rank,
        ) for crew in crews
    }

