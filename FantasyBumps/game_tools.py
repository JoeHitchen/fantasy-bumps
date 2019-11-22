from . import models


def get_all_crews(crews_in_event):
    
    crews_in_db = [(crew.club, crew.gender, crew.rank) for crew in models.Crew.objects.all()]
    
    crews_in_event_not_db = [
        crew for crew in crews_in_event
        if crew not in crews_in_db
    ]
    
    models.Crew.objects.bulk_create([
        models.Crew(club = club, gender = gender, rank = rank)
        for club, gender, rank in crews_in_event_not_db
    ])
    
    return {
        (crew.club, crew.gender, crew.rank): crew
        for crew in models.Crew.objects.all()
        if (crew.club, crew.gender, crew.rank) in crews_in_event
    }


def add_rankings(day, crews, results):
    
    day_index = day.event.days.filter(date__lt = day.date).count()
    
    day.ranking.bulk_create([
        models.Position(
            day = day,
            crew = crew,
            rank = results[crew_id][day_index],
        )
        for crew_id, crew in crews.items()
    ])


def add_athletes(event, crews, crew_lists):
    
    seats = {seat.id: seat for seat in models.Seat.objects.all()}
    
    athletes = []
    for crew_id, crew in crews.items():
        for seat_id, seat in seats.items():
            if crew_id in crew_lists and seat_id in crew_lists[crew_id]:
                athletes.append(models.Athlete(
                    event = event,
                    crew = crew,
                    seat = seat,
                    name = crew_lists[crew_id][seat_id],
                ))
    
    models.Athlete.objects.bulk_create(athletes)

