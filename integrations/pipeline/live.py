from typing import List, Tuple, Dict
import logging

from . import utils
from ..types import Crew, Position, StartOrder
from ..common import gender_map, boat_code_map
from ..live_bumps import CrewPosData


logger = logging.getLogger('LiveBumps')
logger.setLevel('INFO')


def make_event_creation_structures(
    start_order_men: StartOrder,
    start_order_women: StartOrder,
) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, List[CrewPosData]]]]:
    """Creates the two event data structures needed as JSON files to set up a new event."""

    # Create required division data structure
    division_data = {
        'men': [
            division['race_time'].time().strftime('%H:%M')
            for division in start_order_men
        ],
        'women': [
            division['race_time'].time().strftime('%H:%M')
            for division in start_order_women
        ],
    }
    
    # Convert start orders to ranking
    rankings_raw = {
        **utils.start_order_to_ranking(start_order_men),
        **utils.start_order_to_ranking(start_order_women),
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

