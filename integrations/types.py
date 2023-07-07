from typing import TypedDict, Callable
from datetime import time

Crew = tuple[str, str, int]
CrewList = dict[int, str]
CrewListMap = dict[Crew, CrewList]
CrewListFcn = Callable[[str, int], CrewListMap]

PositionStatus = bool
Position = tuple[int, PositionStatus]
PositionMap = dict[Crew, Position]
PositionFcn = Callable[[str, int, int], PositionMap]


class Division(TypedDict):
    gender: str
    number: int
    race_time: time
    size: int
    crews: list[tuple[Crew, PositionStatus]]  # Implicitly top bungline first
    finalised: bool


StartOrder = list[Division]  # Implicitly first race first
StartOrderFcn = Callable[[str, int, int], StartOrder]

