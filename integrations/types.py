from typing import List, Tuple, Dict, TypedDict
from datetime import time

Crew = Tuple[str, str, int]
CrewList = Dict[int, str]
CrewListMap = Dict[Crew, CrewList]

PositionStatus = bool
Position = Tuple[int, PositionStatus]
PositionMap = Dict[Crew, Position]


class Division(TypedDict):
    gender: str
    number: int
    race_time: time
    size: int
    crews: List[Tuple[Crew, PositionStatus]]
    finalised: bool


StartOrder = List[Division]

