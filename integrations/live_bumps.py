import html
from typing import List, Dict, TypedDict
import logging

import requests

from .types import CrewListMap, PositionMap
from .common import MEN, WOMEN, series_text_map, seat_parser, boat_code_parser

logger = logging.getLogger(__name__)


class CrewMoves(TypedDict):
    moves: int


class CrewPosData(TypedDict):
    start: int
    moves: List[CrewMoves]


class CrewSeatData(TypedDict):
    pos: str
    name: str


def _crew_results(crew_data: CrewPosData) -> List[int]:
    positions = [crew_data['start']]
    
    for move in crew_data['moves']:
        positions.append(positions[-1] - move['moves'])  # Sign reversed
    
    return positions


def _parse_crew_list(crew_data: List[CrewSeatData]) -> Dict[int, str]:
    return {
        seat_parser(person['pos']): html.unescape(person['name'])
        for person in crew_data
    }


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from the Live Bumps records."""
    
    series_text = series_text_map[series]
    logger.info('Retrieving crew positions for {} {} (day {}) from Live Bumps'.format(
        series_text,
        year,
        day_number,
    ))
    
    # Load data
    response = requests.get(f'https://bumps.live/data/{series_text.lower()}_{year}.json')
    if not response.ok:
        response.raise_for_status()
    
    # Extract crew positions
    positions = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in enumerate(club_data['men']):
            crew_results = _crew_results(crew_data)
            index = min(day_number, len(crew_results)) - 1
            positions[(club, MEN, crew_rank + 1)] = crew_results[index]
        
        for crew_rank, crew_data in enumerate(club_data['women']):
            crew_results = _crew_results(crew_data)
            index = min(day_number, len(crew_results)) - 1
            positions[(club, WOMEN, crew_rank + 1)] = crew_results[index]
    
    logger.info('Retrieved {} crew positions for {} {} (day {}) from Live Bumps'.format(
        len(positions),
        series_text,
        year,
        day_number,
    ))
    return positions


def get_crew_lists(series: str, year: int) -> CrewListMap:
    """Generates a crew/crew-list map from the Live Bumps records."""
    
    series_text = series_text_map[series]
    logger.info(f'Retrieving crew lists for {series_text} {year} from Live Bumps')
    
    # Load data
    response = requests.get(f'https://bumps.live/data/{series_text.lower()}_{year}_crews.json')
    if not response.ok:
        response.raise_for_status()
    
    # Extract crew lists
    crew_lists = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in club_data['men'].items():
            crew_lists[(club, MEN, int(crew_rank))] = _parse_crew_list(crew_data)
        
        for crew_rank, crew_data in club_data['women'].items():
            crew_lists[(club, WOMEN, int(crew_rank))] = _parse_crew_list(crew_data)
    
    logger.info(f'Retrieved {len(crew_lists)} crews for {series_text} {year} from Live Bumps')
    return crew_lists

