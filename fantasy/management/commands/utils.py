from typing import Dict, Iterable

from integrations import types

from ... import models


CrewTupleMap = Dict[models.Crew.Tuple, models.Crew.Tuple]


def create_crew_tuple_map(crews_for_map: Iterable[models.Crew.Tuple]) -> CrewTupleMap:
    """Creates a mapping from crew tuples to crew objects for a given set of crews."""
    
    crews_in_db = [crew.as_tuple() for crew in models.Crew.objects.all()]
    
    models.Crew.objects.bulk_create([
        models.Crew(club = club, gender = gender, rank = rank)
        for club, gender, rank in crews_for_map
        if (club, gender, rank) not in crews_in_db
    ])
    
    return {
        crew.as_tuple(): crew
        for crew in models.Crew.objects.all()
        if crew.as_tuple() in crews_for_map
    }


def load_crew_rankings(source_function: types.PositionFcn, day: models.Day) -> None:
    """Loads crew rankings from the source provided for a given day."""

    day_number = day.event.days.filter(date__lte = day.date).count()  # One-indexed
    ranking = source_function(day.event.series, day.event.year, day_number)
    
    day.ranking.bulk_create([
        models.Position(
            day = day,
            crew = crew,
            rank = ranking[crew_id][0],
        )
        for crew_id, crew in create_crew_tuple_map(ranking.keys()).items()
    ])


def load_crew_lists(source_function: types.CrewListFcn, event: models.Event) -> None:
    """Loads crew lists from the source provided for the given event, and optionally crew."""
    
    crew_lists = source_function(event.series, event.year)
    
    crew_tuple_map = create_crew_tuple_map(crew_lists.keys())
    seats_map = {seat.id: seat for seat in models.Seat.objects.all()}
    
    athletes = []
    for crew_tuple, crew in crew_tuple_map.items():
        for seat_id, seat in seats_map.items():
            if crew_tuple in crew_lists and seat_id in crew_lists[crew_tuple]:
                athletes.append(models.Athlete(
                    event = event,
                    crew = crew,
                    seat = seat,
                    name = crew_lists[crew_tuple][seat_id],
                ))
    
    models.Athlete.objects.bulk_create(athletes)

