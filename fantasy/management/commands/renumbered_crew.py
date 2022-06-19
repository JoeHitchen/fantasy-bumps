from django.core.management.base import BaseCommand

from parsing import ourcs

from ... import models, game_tools as tools
from ...constants import Clubs, Genders


class Command(BaseCommand):
    help = 'Corrects the crew list for a renumbered crew.'
        
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            'event_tag',
            help = 'The event in which the crew has been renumbered',
        )
        parser.add_argument(
            'club',
            choices = Clubs.values,
            help = 'The club of the renumbered crew',
        )
        parser.add_argument(
            'gender',
            choices = Genders.values,
            help = 'The gender of the renumbered crew',
        )
        parser.add_argument(
            'new_rank',
            type = int,
            help = 'The rank of the renumbered crew',
        )
        parser.add_argument(
            'old_rank',
            type = int,
            help = 'The rank the renumbered crew originally held',
        )
    
    
    def handle(self, *args, **kwargs):
        
        # Process crew details
        crew = models.Crew.objects.get(
            club = kwargs['club'],
            gender = kwargs['gender'],
            rank = kwargs['new_rank'],
        )
        new_crew = (crew.club, crew.gender, crew.rank)
        old_crew = (crew.club, crew.gender, kwargs['old_rank'])
        self.stdout.write('Correcting crew list for {0} {1}{2} as their original {1}{3}'.format(
            Clubs(crew.club).label,
            crew.gender,
            crew.rank,
            old_crew[2],
        ))
        
        
        # Check event and crew entry
        event = models.Event.objects.get(tag = kwargs['event_tag'])
        if not models.Position.objects.filter(day__event = event, crew = crew).count():
            raise models.Position.DoesNotExist('This crew is not entered into this event.')
        
        # Retrieve and check new crew list
        crew_lists = ourcs.get_crew_lists(event.series, event.year)
        if old_crew not in crew_lists:
            raise ValueError('Old crew designation not found on OURCs crew lists page')
        
        # Perform crew list switch
        crew.crew_lists.filter(event = event).delete()  # Referencing purchases set to anon athlete
        tools.add_athletes(
            event,
            {(crew.club, crew.gender, crew.rank): crew},
            {new_crew: crew_lists[old_crew]},
        )
        self.stdout.write('Completed crew list correction for {} {}{}!'.format(
            Clubs(crew.club).label,
            crew.gender,
            crew.rank,
        ))

