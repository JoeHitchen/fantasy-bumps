from django.db import transaction
from django.db.models import F


def buy(team, day, seat, crew):
    """Transaction-wrapped buy action.
    
    Checks the team has sufficients funds and updates their balance, before creating the purchase.
    Rolls back both changes in the event either fails.
    """
    
    with transaction.atomic():
        _buy_body(team, day, seat, crew)


def _buy_body(team, day, seat, crew):
    """INTERNAL METHOD allowing non-transaction access to buy action for query counting."""
    
    budgets = team.entries.select_for_update().get(event = day.event)
    
    balance_field = {
        'M': 'mens_balance',
        'W': 'womens_balance',
    }[crew.gender]
    
    new_balance = getattr(budgets, balance_field) - crew.value(day)
    assert new_balance >= 0, 'Insufficient funds for this purchase.'
    setattr(budgets, balance_field, new_balance)
    budgets.save()
    
    team.purchases.create(day = day, seat = seat, crew = crew)


def sell(purchase, sale_value):
    """Transaction-wrapped sell action.
    
    Adds the sale value to the purchased crew's gender's balance, and deletes the purchase object.
    Rolls back both changes in the event either fails.
    
    Completes in two db operations, if select_related() called when fetching purchase object.
    """
    
    with transaction.atomic():
        _sell_body(purchase, sale_value)


def _sell_body(purchase, sale_value):
    """INTERNAL METHOD allowing non-transaction access to sell action for query counting."""
    
    balance_field = {
        'M': 'mens_balance',
        'W': 'womens_balance',
    }[purchase.crew.gender]
    
    balance_update = {balance_field: F(balance_field) + sale_value}
    updated = purchase.team.entries.filter(event = purchase.day.event).update(**balance_update)
    assert updated == 1, 'Sell failed - Did not update singular row.'
    
    deleted = purchase.delete()
    assert deleted[0] == 1, 'Sell failed - Did not delete singular row.'

