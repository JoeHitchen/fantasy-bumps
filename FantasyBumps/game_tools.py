from django.db.models import Prefetch

from .constants import genders
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


def roll_over_purchases(day):
    """Creates a copy of all purchase records for today on the next day.
    
    MAX four queries. Recommend fetching day with select_related.
    """
    
    models.Purchase.objects.bulk_create([
        models.Purchase(
            team = purchase.team,
            day = day.next,
            crew = purchase.crew,
            seat = purchase.seat,
        )
        for purchase in day.purchases.select_related().all()
    ])


def evaluate_all_investments(day):
    """Update entered teams budgets for changes in crew value from places gained/lost on day."""
    
    def purchases_prefetch(day, gender, target):
        """Prefetch a gendered crew list for day, and set to target attribute on Team model."""
        return Prefetch(
            'team__purchases',
            (
                models.Purchase.objects
                .filter(day = day, crew__gender = gender)
                .select_related('day', 'crew')
            ),
            to_attr = target,
        )
    
    def return_on_investment(purchases, target_day):
        """Calculate the net change in value for a set of purchases advancing to the target day."""
        return sum(
            purchase.crew.value(target_day)
            - purchase.crew.value(purchase.day)
            for purchase in purchases
        )
    
    # Main function body
    entries = (
        models.GameEntry.objects
        .select_related('team')
        .filter(event = day.event)
        .prefetch_related(
            purchases_prefetch(day, genders.MENS, 'mens_crew'),
            purchases_prefetch(day, genders.WOMENS, 'womens_crew'),
        )
    )
    
    for entry in entries:
        entry.mens_budget += return_on_investment(entry.team.mens_crew, day.next)
        entry.womens_budget += return_on_investment(entry.team.womens_crew, day.next)
    
    models.GameEntry.objects.bulk_update(entries, ['mens_budget', 'womens_budget'])

