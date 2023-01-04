from typing import List, Tuple, Dict, TypedDict
from datetime import datetime


Crew = Tuple[str, str, int]
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


TORPIDS = 'T'
EIGHTS = 'E'
event_map = {TORPIDS: 'Torpids', EIGHTS: 'Eights'}

MEN = 'M'
WOMEN = 'W'
gender_map = {MEN: 'Men', WOMEN: 'Women'}



def start_order_to_ranking(start_order: StartOrder) -> RankingMap:
    """Converts a start order to a bumps ranking."""
    
    rank = 0
    ranking = {}
    for division in start_order:
        for club, gender, crew_rank, finalised in division['crews']:
            rank += 1
            ranking[(club, gender, crew_rank)] = (rank, finalised)
    
    return ranking

