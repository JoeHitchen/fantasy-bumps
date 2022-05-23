from collections import Counter
from functools import lru_cache
from math import log

from django.db.models import Prefetch, Max

from .constants import Genders, money
from . import models
from . import errors


def ordered_events():
    """Lists events in reverse chronological order."""
    return models.Event.objects.annotate(last_day = Max('days__date')).order_by('-last_day')


def has_all_seats(purchases, expected_seats):
    """Checks that a set of purchase objects has every seat filled exactly once."""
    
    seat_count = Counter(purchase.seat_id for purchase in purchases)
    seats_filled = [seat_count.get(seat.id, 0) for seat in expected_seats]
    
    if any([count > 1 for count in seats_filled]):
        raise errors.DuplicateSeatError
    
    return all(seats_filled)


def reverse_gender(gender):
    """Return opposite gender constant to that provided."""
    return {
        Genders.MEN: Genders.WOMEN,
        Genders.WOMEN: Genders.MEN,
    }[gender]


@lru_cache(maxsize = 20)
def _pricing_gradient(num_crews):
    """Returns a function to calculate the rounded pricing gradient at a bungline."""
    
    def fudge_factor(num_crews):
        """Calculates a fudge-factor to counter error caused by gradient rounding."""
        
        num_crews_1 = 61  # Women's Torpids
        fudge_1 = 1.004
        num_crews_2 = 92  # Men's Eights
        fudge_2 = 1.002
        
        top = fudge_2 * (num_crews - num_crews_1) - fudge_1 * (num_crews - num_crews_2)
        return top / (num_crews_2 - num_crews_1)
    
    ratio = (money.PRICE_MIN / money.PRICE_MAX) ** (1 / (num_crews - 1))
    ratio *= fudge_factor(num_crews)
    return lambda position: round(money.PRICE_MAX * log(ratio) * ratio ** (position - 1))


@lru_cache(maxsize = 2000)
def pricing(bungline, num_crews):
    """Iteratively calculates the price of a crew on a given bungline for a given event size."""
    
    if bungline == 1:
        return money.PRICE_MAX
    elif bungline == num_crews:
        return money.PRICE_MIN
    
    price_delta = _pricing_gradient(num_crews)(bungline)
    return pricing(bungline + 1, num_crews) - min(price_delta, -1)


def pricing_by_day_gender(bungline, day, gender):
    """A shallow wrapper around the pricing function to expose a bungline/day/gender interface."""
    return pricing(bungline, day.event.num_crews(gender))


def payout_by_day_gender_positions(day, gender, old_position, new_position):
    """Calculates the value change and payout for a given day, gender, and pair of positions."""
    
    position_change = old_position - new_position  # Sign reversed - Lower position is better
    
    crew_value_old = pricing_by_day_gender(old_position, day, gender)
    crew_value_new = pricing_by_day_gender(new_position, day, gender)
    
    payout = 0
    if position_change >= 0:
        headship_bonus = 0.105 if new_position == old_position == 1 else 0
        payout = (0.14 * position_change + 0.07 + headship_bonus) * crew_value_old
        payout = round(payout)
    
    return {'value_change': crew_value_new - crew_value_old, 'payout': payout}


def create_payout_matrix(day):
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
            Prefetch(
                'positions',
                models.Position.objects.filter(day = day),
                to_attr='posn_old',
            ),
            Prefetch(
                'positions',
                models.Position.objects.filter(day = day.next),
                to_attr='posn_new',
            ),
        )
    )
    
    # Generate payout matrix
    return {
        crew: payout_by_day_gender_positions(
            day,
            crew.gender,
            crew.posn_old[0].rank,
            crew.posn_new[0].rank,
        ) for crew in crews
    }

