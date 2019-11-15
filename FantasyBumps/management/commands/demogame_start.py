from datetime import time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone

from parsing import ourcs

from ... import models


class Command(BaseCommand):
    def handle(self, *args, **kwags):
        """Prepares a demonstration game.
        
        Requires a database with no pre-existing events.
        """
        
        if models.Event.objects.exists():
            raise CommandError('An event already exists')
        
        call_command('loaddata', 'seats', 'demo_crews', 'demo_event')
        
        event = models.Event.objects.first()
        event.days.create(
            id = 1,
            name = 'Wednesday',
            date = timezone.now() + timedelta(5),
            first_race_time = time(12, 00),
        )
        
        event.days.create(
            id = 2,
            name = 'Thursday',
            date = timezone.now() + timedelta(6),
            first_race_time = time(12, 00),
        )
        
        event.days.create(
            id = 3,
            name = 'Friday',
            date = timezone.now() + timedelta(7),
            first_race_time = time(12, 00),
        )
        
        event.days.create(
            id = 4,
            name = 'Saturday',
            date = timezone.now() + timedelta(8),
            first_race_time = time(12, 00),
        )
        
        event.days.create(
            id = 5,
            name = 'Finish',
            date = timezone.now() + timedelta(9),
        )
        
        call_command('loaddata', 'demo_start_day1')
        
        seats = {seat.id: seat for seat in models.Seat.objects.all()}
        crews = {(crew.club, crew.gender, crew.rank): crew for crew in models.Crew.objects.all()}
        
        crew_lists = ourcs.get_crew_lists(event_id = 103)
        
        athlete_id = 0
        athletes = []
        crew_athletes = []
        for crew_id, crew in crews.items():
            for seat_id, seat in seats.items():
                athlete_id += 1
                athlete = models.Athlete(
                    id = athlete_id,
                    name = crew_lists[crew_id][seat_id],
                )
                athletes.append(athlete)
                crew_athletes.append(models.CrewEventAthlete(
                    event = event,
                    crew = crew,
                    seat = seat,
                    athlete_id = athlete_id,
                ))
        
        models.Athlete.objects.bulk_create(athletes)
        models.CrewEventAthlete.objects.bulk_create(crew_athletes)
        
        self.stdout.write('Successfully created a demonstration game.')

