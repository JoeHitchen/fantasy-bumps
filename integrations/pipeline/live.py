import traceback
import logging
import os

import requests

from . import common


logger = logging.getLogger('LiveBumps')
logger.setLevel('INFO')


boatcode_map = {
    'ball': 'BAL', 'bras': 'BRC', 'chri': 'CHB', 'corp': 'COO',
    'exet': 'EXC', 'grte': 'GTM', 'hert': 'HEC', 'jesu': 'JEO',
    'kebl': 'KEB', 'lady': 'LMH', 'lina': 'LIN', 'linc': 'LIC',
    'magd': 'MAG', 'mans': 'MAN', 'mert': 'MER', 'newc': 'NEC',
    'orie': 'ORO', 'osle': 'OSG', 'pemb': 'PMB', 'quee': 'QCO',
    'rege': 'RPC', 'some': 'SOM', 'sann': 'SAC', 'sant': 'SAY',
    'sben': 'SBH', 'scat': 'SCO', 'sedm': 'SEH', 'shil': 'SHI',
    'shug': 'SHG', 'sjoh': 'SJO', 'spet': 'SPC', 'trin': 'TRO',
    'univ': 'UCO', 'wadh': 'WAD', 'wolf': 'WOO', 'worc': 'WRO',
}


def _rankings_to_moves(rankings):
    """Converts a set of rankings into the format needed for Live Bumps."""
    
    moves = []
    start = rankings.pop(0)[0]
    for ranking in rankings:
        previous_moves = sum([move['moves'] for move in moves])
        moves.append({
            'moves': start - previous_moves - ranking[0],  # Signs reversed
            'status': ranking[1],
        })
    
    return moves


def post_single_crew_rankings(event, year, crew, rankings):
    """Updates a single crew's rankings for the week on Live Bumps."""
    
    response = requests.post(
        'https://{}/bump/{}/{}'.format(
            os.environ.get('LIVE_BUMPS_HOST'),
            common.event_map[event].lower(),
            year,
        ),
        json = {
            'club': boatcode_map.get(crew[0]),
            'gender': common.gender_map[crew[1]].lower(),
            'number': crew[2] - 1,
            'moves': _rankings_to_moves(rankings),
        },
        headers = {
            'Authorization': os.environ.get('LIVE_BUMPS_KEY'),
            'Content-Type': 'application/json',
        },
    )
    if not response.ok:
        response.raise_for_status()


def post_all_rankings(event, year, rankings_by_day):
    """Updates Live Bumps with the rankings for all crews."""
    logging.info('Updating LiveBumps results for {} {} {}...'.format(
        event,
        year,
        list(rankings_by_day[0].keys())[0][1],
    ))
    
    for crew in rankings_by_day[0].keys():
        try:
            post_single_crew_rankings(
                event,
                year,
                crew,
                [ranking[crew] for ranking in rankings_by_day if crew in ranking],
            )
        except Exception:
            logger.error('Error during LiveBumps update for {} {}{}\n  {}'.format(
                crew[0].upper(),
                crew[1],
                crew[2],
                '\n  '.join(traceback.format_exc().split('\n')),
            ))


def make_event_creation_structures(start_order_men, start_order_women):
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
        **common.start_order_to_ranking(start_order_men),
        **common.start_order_to_ranking(start_order_women),
    }
    
    # Create required ranking data structure
    ranking_data = {}
    for crew, ranking in rankings_raw.items():
        
        club_code = boatcode_map[crew[0]]
        if club_code not in ranking_data:
            ranking_data[club_code] = {}
        
        gender = common.gender_map[crew[1]].lower()
        if gender not in ranking_data[club_code]:
            ranking_data[club_code][gender] = []
        
        ranking_data[club_code][gender].append((crew, ranking))
    
    for club_code, club_items in ranking_data.items():
        for gender_code, gender_items in club_items.items():
            
            gender_items.sort(key = lambda crew: crew[0][2])
            for number, crew in enumerate(gender_items):
                ranking_data[club_code][gender_code][number] = {
                    'start': crew[1][0],
                    'moves': [],
                }
    
    return division_data, ranking_data

