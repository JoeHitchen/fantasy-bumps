from typing import List, cast
from datetime import time
import logging
import re

import requests
from bs4 import BeautifulSoup, Tag

from .types import Crew, PositionMap, Division, StartOrder
from .common import series_text_map, MEN, WOMEN, race_time_parser, add_crews_by_gender
from . import magic

logger = logging.getLogger(__name__)


def _cambridge_club_parser(club_str: str) -> str:
    
    if club_str.lower() == 'clare hall':
        return 'clah'
    
    return {
        'chris': 'chrc',
        'clare': 'clar',
        'corpu': 'cocc',
        'first': 'fatt',
        'jesus': 'jesc',
        'lady ': 'ladc',
        'magda': 'magc',
        'pembr': 'pemc',
        'queen': 'quec',
        'st. c': 'scac',
        'st. e': 'sedc',
        'trini': 'trih',
        'wolfs': 'wolc',
        'vet s': 'vets',
    }.get(club_str[0:5].lower(), club_str[0:4].lower())


def _get_crews_for_division(division_soup: Tag) -> List[Crew]:
    
    start_div = division_soup.findChildren('div', {'class': 'division_boats_start'})[0]
    boat_divs = start_div.findChildren('div', {'class': 'boat_container'})
    
    crews = []
    for boat_div in boat_divs:
        
        crew_name = boat_div.findChildren('p')
        if not crew_name:
            continue
        
        crew_match = re.match(r'(?P<club>.*) (?P<gender>[MW])(?P<number>\d)', crew_name[0].text)
        if not crew_match:
            continue
        
        crews.append((
            _cambridge_club_parser(crew_match.group('club')),
            crew_match.group('gender'),
            int(crew_match.group('number')),
        ))
    
    return crews


def _get_moves_from_results_url(results_url: str) -> List[int]:
    positions_strs = results_url.split('/')[-1].split('.')[0].split('_')[:-1]
    return [int(new) - old for new, old in zip(positions_strs, range(0, 18))]


def _get_positions_for_gender(division_soups: List[Tag], day_number: int) -> PositionMap:
    """Generates the crew-position map for one gender from a parsed set of divisions."""
    
    # Get starting positions map
    ranking = []
    for division_soup in division_soups:
        ranking.extend(_get_crews_for_division(division_soup))
    
    positions = {crew: (rank0 + 1, True) for rank0, crew in enumerate(ranking)}
    
    # Modify positions for racing
    for day_class in ['race_1', 'race_2', 'race_3', 'race_4'][0:day_number - 1]:
        
        # Generate position-move maps for each division
        offset = 0
        moves_maps = []
        for division_soup in division_soups:
            
            selector = f'div.{day_class}>img'
            results_url = cast(str, division_soup.select_one(selector)['src'])  # type: ignore
            moves = _get_moves_from_results_url(results_url)
            
            moves_maps.append({
                offset + bungline0 + 1: move
                for bungline0, move in enumerate(moves)
            })
            offset += len(moves) - 1
        
        # Apply position-move maps in reverse division order
        for moves_map in moves_maps[::-1]:
            for crew, position in positions.items():
                if position[0] in moves_map:
                    positions[crew] = (position[0] + moves_map[position[0]], True)
    
    return positions


def get_positions(series: str, year: int, day_number: int) -> PositionMap:
    """Generates a crew/position map from the CamFM records."""
    
    series_text = series_text_map[series]
    logger.info('Retrieving crew positions for {} {} (day {}) from CamFM'.format(
        series_text,
        year,
        day_number,
    ))
    
    # Get CamFM event ID
    event_id = magic.camfm_event_id(series, year)
    event_id_log = f'Using CamFM event #{event_id}' if event_id else 'Using latest CamFM event'
    logger.info(event_id_log + f' for {series_text} {year}')
    event_string = f'&bumps_id={event_id}' if event_id else ''
    
    # Load page into parser
    response = requests.get(f'https://bumps.camfm.co.uk/?allboats=true{event_string}')
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    
    # Extract crew positions
    charts = soup.find_all('div', {'class': 'bumps_container'})
    mens_divisions = charts[0].findChildren('div', {'class': 'bumps_division_container'})
    womens_divisions = charts[1].findChildren('div', {'class': 'bumps_division_container'})
    
    positions = {
        **_get_positions_for_gender(mens_divisions, day_number),
        **_get_positions_for_gender(womens_divisions, day_number),
    }
    logger.info('Retrieved {} crew positions for {} {} (day {}) from CamFM'.format(
        len(positions),
        series_text,
        year,
        day_number,
    ))
    return positions


def get_start_order(series: str, year: int, day_number: int) -> StartOrder:
    """Recreates the start order from the CamFM records."""
    
    def gun_time(time_str: str, split: bool) -> time:
        """The time the start gun fires, accounting for split divisions."""
        if not split:
            return race_time_parser(time_str)
        return race_time_parser(time_str[:-1] + str(int(time_str[-1]) + 4))
    
    # Get CamFM event ID
    event_id = magic.camfm_event_id(series, year)
    event_id_log = f'Using CamFM event #{event_id}' if event_id else 'Using latest CamFM event'
    logger.info(event_id_log + f' for {series_text_map[series]} {year}')
    event_string = f'&bumps_id={event_id}' if event_id else ''
    
    # Load page into parser
    response = requests.get(f'https://bumps.camfm.co.uk/?{event_string}')
    if not response.ok:
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    race_time_table = soup.select_one('table.racetimes')
    assert race_time_table
    
    # Get division structure
    divisions = []
    for row in race_time_table.findChildren('tr'):
        
        if 'racetimesheader' in row.get_attribute_list('class'):
            continue
        
        cells = row.findChildren('td')
        div_ids = next(cells[0].children).text.split('/')
        race_time_string = next(cells[1].children).text
        
        for div_id in div_ids:
            divisions.append(Division(
                gender = div_id[0],
                number = int(div_id[1]),
                race_time = gun_time(race_time_string, div_id != div_ids[-1]),
                size = 17,
                crews = [],
                finalised = True,
            ))
    divisions.sort(key = lambda div: div['race_time'])
    divisions[0]['size'] += 1  # Add footship crews
    divisions[1]['size'] += 1
    
    positions = get_positions(series, year, day_number)
    add_crews_by_gender(divisions, positions, MEN)
    add_crews_by_gender(divisions, positions, WOMEN)
    return divisions

