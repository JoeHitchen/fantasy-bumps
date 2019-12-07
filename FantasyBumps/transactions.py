from django.db import transaction
from django.db.models import F
from django.core.exceptions import MultipleObjectsReturned

from . import models
from . import errors


def buy(team, day, seat, crew, athlete = None):
    """Transaction-wrapped buy action.
    
    Checks the team has sufficients funds and updates their balance, before creating the purchase.
    Rolls back both changes in the event either fails.
    
    Optimised when:
        select_related called when retrieving day
        purchase.crew.value(day) is cached
        team's budgets for day exist
    
    Specific possible errors:
        InsufficientFundsError (standard)
        NotRacingError (standard)
        DuplicateSeatError (severe)
    """
    
    with transaction.atomic():
        _buy_body(team, day, seat, crew, athlete)


def _buy_body(team, day, seat, crew, athlete = None):
    """INTERNAL METHOD allowing non-transaction access to buy action for query counting."""
    
    budgets = models.GameEntry.objects.select_for_update().get_or_create(
        team = team,
        event = day.event,
    )[0]
    
    balance_field = {
        'M': 'mens_balance',
        'W': 'womens_balance',
    }[crew.gender]
    
    crew_value = crew.value(day)
    if not crew_value:
        raise errors.NotRacingError
    
    new_balance = getattr(budgets, balance_field) - crew_value
    if new_balance < 0:
        raise errors.InsufficientFundsError
    
    setattr(budgets, balance_field, new_balance)
    budgets.save()
    
    # Explicitly load crew lists - In-memory checks reduce queries and allow locking
    crew_list = (
        team.get_crew(day, crew.gender)
        .select_for_update()
        .select_related('seat', 'athlete')
    )
    
    if any([purchase.seat == seat for purchase in crew_list]):
        raise errors.DuplicateSeatError
    
    if athlete and any([purchase.athlete == athlete for purchase in crew_list]):
        athlete = None
    
    team.purchases.create(day = day, seat = seat, crew = crew, athlete = athlete)


def sell(purchase):
    """Transaction-wrapped sell action.
    
    Adds the sale value to the purchased crew's gender's balance, and deletes the purchase object.
    Rolls back both changes in the event either fails.
    
    Optimised when:
        select_related called when retrieving purchase
        purchase.crew.value(day) is cached
    
    Specific possible errors:
        Purchase.DoesNotExist (standard)
        GameEntry.DoesNotExist (severe)
        MultipleObjectsReturned (severe)
    """
    
    with transaction.atomic():
        _sell_body(purchase)


def _sell_body(purchase):
    """INTERNAL METHOD allowing non-transaction access to sell action for query counting."""
    
    balance_field = {
        'M': 'mens_balance',
        'W': 'womens_balance',
    }[purchase.crew.gender]
    
    sale_value = purchase.crew.value(purchase.day)
    balance_update = {balance_field: F(balance_field) + sale_value}
    
    updated = purchase.team.entries.filter(event = purchase.day.event).update(**balance_update)
    if updated == 0:
        raise models.GameEntry.DoesNotExist
    elif updated > 1:  # Untested case - Should be blocked by database constraint.
        raise MultipleObjectsReturned
    
    deleted = purchase.delete()
    if deleted[0] != 1:
        raise purchase.DoesNotExist


def switch(purchase, athlete_id, seat_id):
    
    # Athlete switching
    purchase.athlete = models.Athlete.objects.get(
        event = purchase.day.event,
        crew = purchase.crew,
        seat__cox = False,
        id = athlete_id,
    ) if int(athlete_id) else None
    
    other_purchases = (
        purchase.team
        .get_crew(purchase.day, purchase.crew.gender)
        .exclude(id = purchase.id)
        .select_related('athlete')
    )
    if purchase.athlete and any(p.athlete == purchase.athlete for p in other_purchases):
        raise errors.DuplicateAthleteError
    
    # Seat switching
    old_seat = purchase.seat
    purchase.seat = models.Seat.objects.get(id = seat_id)
    
    if purchase.seat.cox:
        raise errors.NinthSeatError
    
    (  # Perform reverse seat-switch
        purchase.team
        .get_crew(purchase.day, purchase.crew.gender)
        .filter(seat = purchase.seat)
        .exclude(id = purchase.id)
        .update(seat = old_seat)
    )
    
    # Perform update
    purchase.save()

