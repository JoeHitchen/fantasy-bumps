
class DuplicateSeatError(ValueError):
    """Raised if a crew list has a seat filled twice or that action is being attempted.
    
    Cannot rely on table-level database constraints, due to lack of gender information in table.
    """
    message = 'Cannot fill a seat twice.'


class InsufficientFundsError(ValueError):
    """Raised if a team does not have sufficient funds for a purchase."""
    message = 'Insufficient funds for this purchase.'


class NotRacingError(ValueError):
    """Raised if an action is attempted involving a crew on a day they are not racing."""
    message = 'Invalid crew/day combination.'

