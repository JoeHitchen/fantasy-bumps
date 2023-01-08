from typing import List, Tuple, TypedDict
from datetime import datetime

from ..types import Crew, PositionStatus, PositionMap


class StartOrderDivision(TypedDict):
    gender: str
    number: int
    race_time: datetime
    size: int
    crews: List[Tuple[Crew, PositionStatus]]
    finalised: bool


StartOrder = List[StartOrderDivision]


def start_order_to_ranking(start_order: StartOrder) -> PositionMap:
    """Converts a start order to a bumps ranking."""
    
    rank = 0
    ranking = {}
    for division in start_order:
        for crew, status in division['crews']:
            rank += 1
            ranking[crew] = (rank, status)
    
    return ranking

