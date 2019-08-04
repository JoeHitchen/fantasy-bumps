from django.db import transaction
from django.db.models import F


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

