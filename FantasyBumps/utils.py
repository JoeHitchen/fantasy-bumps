from django.db.models import Count, Prefetch

from .constants import genders
from . import models
from . import errors


def has_all_seats(purchases):
    """Checks that a queryset of purchase objects has every seat filled exactly once."""
    
    seats_filled = purchases.values('seat').annotate(count = Count('seat'))
    seats_filled = {seat['seat']: seat['count'] for seat in seats_filled}
    seats_filled = [seats_filled.get(seat.id, 0) for seat in models.Seat.objects.all()]
    
    if any([count > 1 for count in seats_filled]):
        raise errors.DuplicateSeatError
    
    return all(seats_filled)


def reverse_gender(gender):
    """Return opposite gender constant to that provided."""
    return {
        genders.MENS: genders.WOMENS,
        genders.WOMENS: genders.MENS,
    }[gender]


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
    
    def return_on_investment(purchases, target_day):
        """Calculate the net change in value for a set of purchases advancing to the target day."""
        return sum(
            purchase.crew.value(target_day)
            - purchase.crew.value(purchase.day)
            for purchase in purchases
        )
    
    # Main function body
    entries = (
        models.GameEntry.objects
        .select_related('team')
        .filter(event = day.event)
        .prefetch_related(
            purchases_prefetch(day, genders.MENS, 'mens_crew'),
            purchases_prefetch(day, genders.WOMENS, 'womens_crew'),
        )
    )
    
    for entry in entries:
        entry.mens_budget += return_on_investment(entry.team.mens_crew, day.next)
        entry.womens_budget += return_on_investment(entry.team.womens_crew, day.next)
    
    models.GameEntry.objects.bulk_update(entries, ['mens_budget', 'womens_budget'])

