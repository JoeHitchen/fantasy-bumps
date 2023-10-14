from dataclasses import dataclass

from ..constants import Genders, money
from .. import models
from .game_advance import create_payout_matrix


@dataclass
class Selection:
    cost: int
    reward: int
    crews: list[models.Crew]

    def __add__(self, other: 'Selection') -> 'Selection':
        """Performs addition per property."""

        return Selection(
            cost = self.cost + other.cost,
            reward = self.reward + other.reward,
            crews = self.crews + other.crews,
        )


def filter_optimal_selections(selections: list[Selection]) -> list[Selection]:
    """The set of crews selections that:
        * Reward more than anything cheaper
        * Cost less than anything which rewards more.

        Ordered by increasing cost.
    """

    def sort_key(selection: Selection) -> tuple[int, int]:
        """Increasing cost then decreasing reward

        This ensures that the first selection reached at a given price-point is the one that gives
        the highest payout.
        """
        return (selection.cost, -selection.reward)

    selections.sort(key = sort_key)

    filtered_selections: list[Selection] = []
    for selection in selections:
        if not filtered_selections or selection.reward > filtered_selections[-1].reward:
            filtered_selections.append(selection)

    return filtered_selections


def double_selection_size(selections: list[Selection], budget: int) -> list[Selection]:
    """The set of combinations of the selections provided with themselves.

        Filtered to remove:
          * Duplicate combinations
          * Combinations that leave insufficient budget remaining to complete the crew
    """

    max_crabs = budget - 2 * money.PRICE_MIN * len(selections[0].crews)

    merged_selections = []
    for index, bow_selection in enumerate(selections):
        for stern_selection in selections[index:]:
            if bow_selection.cost + stern_selection.cost > max_crabs:
                continue
            merged_selections.append(bow_selection + stern_selection)

    return merged_selections


def get_optimal_crew(day: models.Day, gender: Genders, budget: int) -> Selection:
    """Picks the best crew for the given day & gender, constrained by the budget provided."""

    # Determine best picks for a single seat
    matrix = create_payout_matrix(day)

    single_seat = [
        Selection(
            crew.value(day),
            payout['value_change'] + payout['payout'],
            [crew],
        ) for crew, payout in matrix.items() if crew.gender == gender
    ]
    best_singles = filter_optimal_selections(single_seat)

    # Determine the best set of eight rowers
    best_rowers = best_singles
    for _ in range(0, 3):
        best_rowers = double_selection_size(best_rowers, budget)
        best_rowers = filter_optimal_selections(best_rowers)

    # Complete the crew by finding the best cox still affordable
    best_crew = None
    for rowers in best_rowers:
        for cox in best_singles[::-1]:
            if rowers.cost + cox.cost > budget:
                continue

            crew = rowers + cox
            if not best_crew or crew.reward > best_crew.reward:
                best_crew = crew

            break

    assert best_crew
    return best_crew


def get_optimal_campaign(event: models.Event, gender: Genders) -> list[Selection]:
    """Picks the best crew each day of an event, based on the previous days' best performance."""

    optimal_crews = []
    budget = money.INITIAL_BALANCE
    for day in event.days.filter(first_race_time__isnull = False):
        optimal_crews.append(get_optimal_crew(day, gender, budget))
        budget += optimal_crews[-1].reward

    return optimal_crews

