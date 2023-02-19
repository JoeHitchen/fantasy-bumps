import html
from typing import List, Tuple, Dict, TypedDict
import logging
import traceback
import os

import requests

from .types import Crew, CrewListMap, Position, PositionMap, StartOrder
from .common import MEN, WOMEN, gender_map, series_text_map
from .common import seat_parser, boat_code_parser, boat_code_map
from . import anu_dat

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


WriteOutcome = Tuple[int, int, int]


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


def get_all_positions(series: str, year: int) -> Dict[Crew, List[Position]]:
    
    # Load data
    response = requests.get(f'{BASE_URL}/data/{series_text_map[series].lower()}_{year}.json')
    if not response.ok:
        response.raise_for_status()
    
    # Extract crew positions
    positions = {}
    for boat_code, club_data in response.json().items():
        club = boat_code_parser(boat_code)
        
        for crew_rank, crew_data in enumerate(club_data['men']):
            positions[(club, MEN, crew_rank + 1)] = _moves_to_positions(crew_data)
        
        for crew_rank, crew_data in enumerate(club_data['women']):
            positions[(club, WOMEN, crew_rank + 1)] = _moves_to_positions(crew_data)
    
    return positions


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from the Live Bumps records."""
    
    series_text = series_text_map[series]
    logger.info('Retrieving crew positions for {} {} (day {}) from Live Bumps'.format(
        series_text,
        year,
        day_number,
    ))
    
    day_positions = {}
    for crew, positions in get_all_positions(series, year).items():
        try:
            day_positions[crew] = positions[day_number - 1]
        except IndexError:
            day_positions[crew] = positions[-1]
    
    logger.info('Retrieved {} crew positions for {} {} (day {}) from Live Bumps'.format(
        len(day_positions),
        series_text,
        year,
        day_number,
    ))
    return day_positions


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
) -> WriteOutcome:
    """Updates Live Bumps with the rankings for all crews."""
    logger.info('Updating Live Bumps results for {} {}'.format(series_text_map[series], year))
    
    # Convert input positions
    positions_by_crew: Dict[Crew, List[Position]] = {}
    for day_positions in positions_by_day:
        for crew, position in day_positions.items():
            if crew not in positions_by_crew:
                positions_by_crew[crew] = []
            positions_by_crew[crew].append(position)
    
    
    # Skip unchanged crews
    skip_list = []
    live_positions_by_crew = get_all_positions(series, year)
    for crew, positions in positions_by_crew.items():
        if positions == live_positions_by_crew.get(crew):
            skip_list.append(crew)
    
    for skip_crew in skip_list:
        positions_by_crew.pop(skip_crew)
    
    
    # Write updates
    error_count = 0
    for crew in positions_by_crew.keys():
        try:
            
            payload = {
                'club': boat_code_map.get(crew[0]),
                'gender': gender_map[crew[1]].lower(),
                'number': crew[2] - 1,  # Live Bumps is zero-indexed for crew numbers
                'moves': _positions_to_moves(positions_by_crew[crew])['moves'],
            }
            response = requests.post(
                f'{BASE_URL}/bump/{series_text_map[series].lower()}/{year}',
                headers = {'Authorization': AUTH_KEY, 'Content-Type': 'application/json'},
                json = payload,
            )
            if not response.ok:
                response.raise_for_status()
            
        except Exception:
            error_count += 1
            logger.error('Error during Live Bumps update for {} {}{}\n  {}'.format(
                crew[0].upper(),
                crew[1],
                crew[2],
                '\n  '.join(traceback.format_exc().split('\n')),
            ))
    
    logger.info('Updated {} results on Live Bumps for {} {} ({} errors, {} skipped)'.format(
        len(positions_by_day[0].keys()) - error_count,
        series_text_map[series],
        year,
        error_count,
        len(skip_list),
    ))
    return len(positions_by_crew), error_count, len(skip_list)


def wipe_positions(series: str, year: int) -> WriteOutcome:
    """A light wrapper to reset the positions for an event."""
    
    return write_positions(series, year, [get_positions(series, year, 1)])


def __make_event_creation_structures(
    start_order_men: StartOrder,
    start_order_women: StartOrder,
) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, List[CrewPosData]]]]:
    """Creates the two event data structures needed as JSON files to set up a new event."""
    
    # Create required division data structure
    division_data = {
        'men': [
            division['race_time'].strftime('%H:%M')
            for division in start_order_men
        ],
        'women': [
            division['race_time'].strftime('%H:%M')
            for division in start_order_women
        ],
    }
    
    # Convert start orders to positions
    rankings_raw = {
        **anu_dat.__start_order_to_positions(start_order_men),
        **anu_dat.__start_order_to_positions(start_order_women),
    }
    
    # Create required ranking data structure
    ranking_data: Dict[str, Dict[str, List[Tuple[Crew, Position]]]] = {}
    for crew, ranking in rankings_raw.items():
        
        club_code = boat_code_map[crew[0]]
        if club_code not in ranking_data:
            ranking_data[club_code] = {}
        
        gender = gender_map[crew[1]].lower()
        if gender not in ranking_data[club_code]:
            ranking_data[club_code][gender] = []
        
        ranking_data[club_code][gender].append((crew, ranking))
    
    ranking_out: Dict[str, Dict[str, List[CrewPosData]]] = {}
    for club_code, club_items in ranking_data.items():
        ranking_out[club_code] = {}
        for gender_code, gender_items in club_items.items():
            ranking_out[club_code][gender_code] = []
            
            gender_items.sort(key = lambda crew: crew[0][2])
            for number, crew_data in enumerate(gender_items):
                ranking_out[club_code][gender_code].append({
                    'start': crew_data[1][0],
                    'moves': [],
                })
    
    return division_data, ranking_out

