import html
from typing import List, Dict, TypedDict
import logging
import traceback
import os

import requests

from .types import CrewListMap, Position, PositionMap
from .common import MEN, WOMEN, gender_map, series_text_map
from .common import seat_parser, boat_code_parser, boat_code_map

logger = logging.getLogger(__name__)

BASE_URL = 'https://{}'.format(os.environ.get('LIVE_BUMPS_HOST', 'bumps.live'))
AUTH_KEY = os.environ.get('LIVE_BUMPS_KEY', '')


class CrewMove(TypedDict):
    moves: int
    status: bool


class CrewPosData(TypedDict):
    start: int
    moves: List[CrewMove]


class CrewSeatData(TypedDict):
    pos: str
    name: str


def _moves_to_positions(crew_data: CrewPosData) -> List[Position]:
    """Converts a set of moves in the Live Bumps format to standardised positions."""
    
    positions = [(crew_data['start'], True)]
    
    for move in crew_data['moves']:
        positions.append((positions[-1][0] - move['moves'], move['status']))  # Sign reversed
    
    return positions


def _positions_to_moves(positions: List[Position]) -> CrewPosData:
    """Converts a set of positions into the format needed for Live Bumps."""
    
    moves: List[CrewMove] = []
    start = positions.pop(0)[0]
    for position in positions:
        previous_moves = sum([move['moves'] for move in moves])
        moves.append({
            'moves': start - previous_moves - position[0],  # Signs reversed
            'status': position[1],
        })
    
    return {'start': start, 'moves': moves}


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
    response = requests.get(f'{BASE_URL}/data/{series_text.lower()}_{year}.json')
    if not response.ok:
        response.raise_for_status()
    
    # Extract crew positions
    positions = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in enumerate(club_data['men']):
            crew_results = _moves_to_positions(crew_data)
            index = min(day_number, len(crew_results)) - 1
            positions[(club, MEN, crew_rank + 1)] = crew_results[index]
        
        for crew_rank, crew_data in enumerate(club_data['women']):
            crew_results = _moves_to_positions(crew_data)
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
    response = requests.get(f'{BASE_URL}/data/{series_text.lower()}_{year}_crews.json')
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


def write_positions(
    series: str,
    year: int,
    positions_by_day: List[PositionMap],
) -> None:
    """Updates Live Bumps with the rankings for all crews."""
    logging.info('Updating LiveBumps results for {} {}...'.format(series, year))
    
    for crew in positions_by_day[0].keys():
        try:
            
            crew_positions = [
                day_positions[crew]
                for day_positions in positions_by_day
                if crew in day_positions
            ]
            payload = {
                'club': boat_code_map.get(crew[0]),
                'gender': gender_map[crew[1]].lower(),
                'number': crew[2] - 1,  # Live Bumps is zero-indexed for crew numbers
                'moves': _positions_to_moves(crew_positions)['moves'],
            }
            response = requests.post(
                f'{BASE_URL}/bump/{series_text_map[series].lower()}/{year}',
                headers = {'Authorization': AUTH_KEY, 'Content-Type': 'application/json'},
                json = payload,
            )
            if not response.ok:
                response.raise_for_status()
            
        except Exception:
            logger.error('Error during LiveBumps update for {} {}{}\n  {}'.format(
                crew[0].upper(),
                crew[1],
                crew[2],
                '\n  '.join(traceback.format_exc().split('\n')),
            ))

