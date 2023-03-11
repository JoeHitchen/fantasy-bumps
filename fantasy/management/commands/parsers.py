from typing import List, Dict, TypedDict
import enum
import logging

from django.core.management import call_command

from integrations import types as integrations
from integrations import live_bumps, anu_html, anu_dat, ourcs, camfm
from integrations.common import series_text_map

from ...constants import Locations, Series as EventSeries

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('integrations.misc')


class Sources(enum.Enum):
    DEMO = 'demo'
    LIVE = 'live'
    ANU_HTML = 'anu-html'
    ANU_DAT = 'anu-dat'
    OURCS = 'ourcs'
    CAMFM = 'camfm'
    NOOP = 'noop'
    
    def __str__(self) -> str:
        return self.value


series_location_map: Dict[EventSeries, Locations] = {
    EventSeries.DEMO: Locations.DEMO,
    EventSeries.TORPIDS: Locations.OXFORD,
    EventSeries.EIGHTS: Locations.OXFORD,
    EventSeries.LENTS: Locations.CAMBRIDGE,
    EventSeries.MAYS: Locations.CAMBRIDGE,
}


location_event_sources_map: Dict[Locations, List[Sources]] = {
    Locations.DEMO: [Sources.DEMO],
    Locations.OXFORD: [Sources.LIVE, Sources.ANU_HTML, Sources.ANU_DAT],
    Locations.CAMBRIDGE: [Sources.CAMFM],
}

location_crew_list_sources_map: Dict[Locations, List[Sources]] = {
    Locations.DEMO: [Sources.DEMO],
    Locations.OXFORD: [Sources.LIVE, Sources.OURCS],
    Locations.CAMBRIDGE: [Sources.NOOP],
}


def _demo_start_order(series: str, year: int, day_number: int) -> integrations.StartOrder:
    logger.info(f'Loading the demo start order for day {day_number}')
    call_command(
        'loaddata',
        'demo_event',
        'demo_days',
        'demo_crews',
        'demo_start_day{}'.format(day_number),
    )
    logger.info(f'Loaded the demo start order for day {day_number}')
    return []


def _demo_positions(series: str, year: int, day_number: int) -> integrations.PositionMap:
    logger.info(f'Loading the demo crew positions for day {day_number}')
    call_command(
        'loaddata',
        'demo_crews',
        'demo_start_day{}'.format(day_number),
    )
    logger.info(f'Loaded the demo crew positions for day {day_number}')
    return {}


def _demo_crew_lists(series: str, year: int) -> integrations.CrewListMap:
    logger.info('Retrieving demo crew lists from OURCs as Torpids 2013')
    crew_lists = ourcs.get_crew_lists(EventSeries.TORPIDS, 2013)
    logger.info('Retrieved demo crew lists from OURCs as Torpids 2013')
    return crew_lists


def _noop_crew_lists(series: str, year: int) -> integrations.CrewListMap:
    logger.info(f'Not performing a crew list lookup for {series_text_map[series]} {year}')
    return {}


_start_order_source_function_map: Dict[Sources, integrations.StartOrderFcn] = {
    Sources.DEMO: _demo_start_order,
    Sources.LIVE: live_bumps.get_start_order,
    Sources.ANU_HTML: anu_html.get_start_order,
    Sources.ANU_DAT: anu_dat.get_start_order,
    Sources.CAMFM: camfm.get_start_order,
}

_position_source_function_map: Dict[Sources, integrations.PositionFcn] = {
    Sources.DEMO: _demo_positions,
    Sources.LIVE: live_bumps.get_positions,
    Sources.ANU_HTML: anu_html.get_positions,
    Sources.ANU_DAT: anu_dat.get_positions,
    Sources.CAMFM: camfm.get_positions,
}

_crew_list_source_function_map: Dict[Sources, integrations.CrewListFcn] = {
    Sources.DEMO: _demo_crew_lists,
    Sources.LIVE: live_bumps.get_crew_lists,
    Sources.OURCS: ourcs.get_crew_lists,
    Sources.NOOP: _noop_crew_lists,
}


class StartOrderSource(TypedDict):
    source: Sources
    function: integrations.StartOrderFcn


class PositionSource(TypedDict):
    source: Sources
    function: integrations.PositionFcn


class CrewListSource(TypedDict):
    source: Sources
    function: integrations.CrewListFcn


def get_validated_start_order_source(location: Locations, source_request: str) -> StartOrderSource:
    
    valid_sources = location_event_sources_map[location]
    
    try:
        source = Sources(source_request)
    except ValueError:
        source = valid_sources[0]
    
    assert source in valid_sources, f'`{source_request}` invalid start order source for {location}'
    return {'source': source, 'function': _start_order_source_function_map[source]}


def get_validated_position_source(location: Locations, source_request: str) -> PositionSource:
    
    valid_sources = location_event_sources_map[location]
    
    try:
        source = Sources(source_request)
    except ValueError:
        source = valid_sources[0]
    
    assert source in valid_sources, f'`{source_request}` invalid event source for {location}'
    return {'source': source, 'function': _position_source_function_map[source]}


def get_validated_crew_list_source(location: Locations, source_request: str) -> CrewListSource:
    
    valid_sources = location_crew_list_sources_map[location]
    
    try:
        source = Sources(source_request)
    except ValueError:
        source = valid_sources[0]
    
    assert source in valid_sources, f'`{source_request}` invalid crew list source for {location}'
    return {'source': source, 'function': _crew_list_source_function_map[source]}

