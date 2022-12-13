from django.db.models import Prefetch

from .constants import Genders
from . import models
from . import utils


def roll_over_purchases(day):
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


def evaluate_all_investments(day):
    """Update entered teams budgets for changes in crew value from places gained/lost on day."""
    
    def purchases_prefetch(day, gender, target):
        """Prefetch a gendered crew list for day, and set to target attribute on Team model."""
        return Prefetch(
            'team__purchases',
            (
                models.Purchase.objects
                .filter(day = day, crew__gender = gender)
                .select_related('day', 'crew')
            ),
            to_attr = target,
        )
    
    
    def update_entry_with_investment_outcome(entry):
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
    payout_matrix = utils.create_payout_matrix(day)
    all_seats = models.Seat.objects.all()
    
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

