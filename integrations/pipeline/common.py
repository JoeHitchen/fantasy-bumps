from typing import List, Tuple, Dict, TypedDict
from datetime import datetime

from ..types import Crew


StartOrderCrew = Tuple[str, str, int, bool]
ProvisionalRanking = Tuple[int, bool]


class StartOrderDivision(TypedDict):
    gender: str
    number: int
    race_time: datetime
    size: int
    crews: List[StartOrderCrew]
    finalised: bool


StartOrder = List[StartOrderDivision]
RankingMap = Dict[Crew, ProvisionalRanking]


def start_order_to_ranking(start_order: StartOrder) -> RankingMap:
    """Converts a start order to a bumps ranking."""
    
    rank = 0
    ranking = {}
    for division in start_order:
        for club, gender, crew_rank, finalised in division['crews']:
            rank += 1
            ranking[(club, gender, crew_rank)] = (rank, finalised)
    
    return ranking

