from typing import Tuple, Dict

Crew = Tuple[str, str, int]
CrewList = Dict[int, str]
CrewListMap = Dict[Crew, CrewList]

Position = Tuple[int, bool]
PositionMap = Dict[Crew, Position]

