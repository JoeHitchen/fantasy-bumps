from typing import Tuple, Dict

Crew = Tuple[str, str, int]
CrewList = Dict[int, str]
CrewListMap = Dict[Crew, CrewList]

PositionStatus = bool
Position = Tuple[int, PositionStatus]
PositionMap = Dict[Crew, Position]

