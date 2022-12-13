from ... import models


def create_crew_tuple_map(crews_for_map):
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


def load_crew_rankings(source_function, day):
    """Loads crew rankings from the source provided for a given day."""

    day_number = day.event.days.filter(date__lte = day.date).count()  # One-indexed
    ranking = source_function(day.event.series, day.event.year, day_number)
    
    day.ranking.bulk_create([
        models.Position(
            day = day,
            crew = crew,
            rank = ranking[crew_id],
        )
        for crew_id, crew in create_crew_tuple_map(ranking.keys()).items()
    ])

