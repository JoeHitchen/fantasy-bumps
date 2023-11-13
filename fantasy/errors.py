
class DuplicateSeatError(ValueError):
    """Raised if a crew list has a seat filled twice or that action is being attempted.

    Cannot rely on table-level database constraints, due to lack of gender information in table.
    """
    message = 'Cannot fill a seat twice.'


class DuplicateAthleteError(ValueError):
    """Raised if a crew list has an athlete twice or that action is being attempted.

    Cannot rely on table-level database constraints, due to lack of gender information in table.
    """
    message = 'Cannot use an athlete twice.'


class NinthSeatError(ValueError):
    """Raised if a rower is found in the coxing seat or that action is being attempted."""
    message = 'Cannot put a rower in a coxing seat'


class ReverseNinthSeatError(ValueError):
    """Raised if a cox is found rowing or that action is being attempted."""
    message = 'Cannot allow coxes to row'


class WrongCrewError(ValueError):
    """Raised if an athlete is found in the wrong crew or that action is being attempted."""
    message = 'Athletes must stay with their crew'


class InsufficientFundsError(ValueError):
    """Raised if a team does not have sufficient funds for a purchase."""
    message = 'Insufficient funds for this purchase.'


class NotRacingError(ValueError):
    """Raised if an action is attempted involving a crew on a day they are not racing."""
    message = 'Invalid crew/day combination.'

