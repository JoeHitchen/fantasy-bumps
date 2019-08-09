
class InsufficientFundsError(ValueError):
    """Raised if a team does not have sufficient funds for a purchase."""
    message = 'Insufficient funds for this purchase.'

