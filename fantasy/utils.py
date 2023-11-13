from collections import Counter
from functools import lru_cache
from typing import TypedDict, Iterable, Callable
from math import log

from django.db import models as db

from .constants import Genders, money
from . import models
from . import errors


class Payout(TypedDict):
    value_change: int
    payout: int


def ordered_events() -> db.QuerySet['models.Event']:
    """Lists events in reverse chronological order."""
    return models.Event.objects.annotate(last_day = db.Max('days__date')).order_by('-last_day')


def has_all_seats(
    purchases: Iterable['models.Purchase'],
    expected_seats: Iterable['models.Seat'],
) -> bool:
    """Checks that a set of purchase objects has every seat filled exactly once."""

    seat_count = Counter(purchase.seat_id for purchase in purchases)
    seats_filled = [seat_count.get(seat.id, 0) for seat in expected_seats]

    if any(count > 1 for count in seats_filled):
        raise errors.DuplicateSeatError

    return all(seats_filled)


def reverse_gender(gender: Genders) -> Genders:
    """Return opposite gender constant to that provided."""
    return {
        Genders.MEN: Genders.WOMEN,
        Genders.WOMEN: Genders.MEN,
    }[gender]


@lru_cache(maxsize = 20)
def _pricing_gradient(num_crews: int) -> Callable[[int], int]:
    """Returns a function to calculate the rounded pricing gradient at a bungline."""

    def fudge_factor(num_crews: int) -> float:
        """Calculates a fudge-factor to counter error caused by gradient rounding."""

        num_crews_1 = 61  # Women's Torpids
        fudge_1 = 1.004
        num_crews_2 = 92  # Men's Eights
        fudge_2 = 1.002

        top = fudge_2 * (num_crews - num_crews_1) - fudge_1 * (num_crews - num_crews_2)
        return top / (num_crews_2 - num_crews_1)

    ratio = (money.PRICE_MIN / money.PRICE_MAX) ** (1 / (num_crews - 1))
    ratio *= fudge_factor(num_crews)

    def pricing_gradient(position: int) -> int:
        return int(round(money.PRICE_MAX * log(ratio) * ratio ** (position - 1)))

    return pricing_gradient


@lru_cache(maxsize = 2000)
def pricing(bungline: int, num_crews: int) -> int:
    """Iteratively calculates the price of a crew on a given bungline for a given event size."""

    if bungline == 1:
        return money.PRICE_MAX
    elif bungline == num_crews:
        return money.PRICE_MIN

    price_delta = _pricing_gradient(num_crews)(bungline)
    return pricing(bungline + 1, num_crews) - min(price_delta, -1)


def pricing_by_day_gender(bungline: int, day: 'models.Day', gender: Genders) -> int:
    """A shallow wrapper around the pricing function to expose a bungline/day/gender interface."""
    return pricing(bungline, day.event.num_crews(gender))


def payout_by_day_gender_positions(
    day: 'models.Day',
    gender: Genders,
    old_position: int,
    new_position: int,
) -> Payout:
    """Calculates the value change and payout for a given day, gender, and pair of positions.

    ToDo: Consider whether this function should accept Position instances.
    """

    position_change = old_position - new_position  # Sign reversed - Lower position is better

    crew_value_old = pricing_by_day_gender(old_position, day, gender)
    crew_value_new = pricing_by_day_gender(new_position, day, gender)

    payout = 0.
    if position_change >= 0:
        headship_bonus = 0.105 if new_position == old_position == 1 else 0
        payout = (0.14 * position_change + 0.07 + headship_bonus) * crew_value_old

    return {'value_change': crew_value_new - crew_value_old, 'payout': round(payout)}

