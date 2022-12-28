import enum

from django.core.management import call_command

from parsing import live_bumps, anu, ourcs, camfm

from ...constants import Locations, Series as EventSeries


class Sources(enum.Enum):
    DEMO = 'demo'
    LIVE = 'live'
    ANU = 'anu'
    OURCS = 'ourcs'
    CAMFM = 'camfm'
    NOOP = 'noop'
    
    def __str__(self):
        return self.value

    
series_location_map = {
    EventSeries.DEMO: Locations.DEMO,
    EventSeries.TORPIDS: Locations.OXFORD,
    EventSeries.EIGHTS: Locations.OXFORD,
    EventSeries.LENTS: Locations.CAMBRIDGE,
    EventSeries.MAYS: Locations.CAMBRIDGE,
}


location_event_sources_map = {
    Locations.DEMO: [Sources.DEMO],
    Locations.OXFORD: [Sources.LIVE, Sources.ANU],
    Locations.CAMBRIDGE: [Sources.CAMFM],
}
location_crew_list_sources_map = {
    Locations.DEMO: [Sources.DEMO],
    Locations.OXFORD: [Sources.LIVE, Sources.OURCS],
    Locations.CAMBRIDGE: [Sources.NOOP],
}


def _demo_positions(series, year, day_number):
    call_command(
        'loaddata',
        'demo_crews',
        'demo_start_day{}'.format(day_number),
    )
    return {}


def _demo_crew_lists(series, year):
    return ourcs.get_crew_lists(EventSeries.TORPIDS, 2013)


def _noop_crew_lists(series, year):
    return {}


_event_source_function_map = {
    Sources.DEMO: _demo_positions,
    Sources.LIVE: live_bumps.get_positions,
    Sources.ANU: anu.get_positions,
    Sources.CAMFM: camfm.get_positions,
}
_crew_list_source_function_map = {
    Sources.DEMO: _demo_crew_lists,
    Sources.LIVE: live_bumps.get_crew_lists,
    Sources.OURCS: ourcs.get_crew_lists,
    Sources.NOOP: _noop_crew_lists,
}


def get_validated_event_source(location, source_request):
    
    valid_sources = location_event_sources_map[location]
    source = Sources(source_request) if source_request else valid_sources[0]
    assert source in valid_sources, f'`{source_request}` invalid event source for {location}'
    
    return {'source': source, 'function': _event_source_function_map[source]}


def get_validated_crew_list_source(location, source_request):
    
    valid_sources = location_crew_list_sources_map[location]
    source = Sources(source_request) if source_request else valid_sources[0]
    assert source in valid_sources, f'`{source_request}` invalid crew list source for {location}'
    
    return {'source': source, 'function': _crew_list_source_function_map[source]}

