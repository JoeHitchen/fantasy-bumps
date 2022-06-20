import logging

from django.core.management.base import BaseCommand

from parsing import live_bumps, ourcs

from ... import models, game_tools as tools
from ...constants import Clubs, Genders, Sources

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.renumbered')


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
            help = 'The club of the crew',
        )
        parser.add_argument(
            'gender',
            choices = Genders.values,
            help = 'The gender of the crew',
        )
        parser.add_argument(
            'new_rank',
            type = int,
            help = 'The rank of the crew after renumbering',
        )
        parser.add_argument(
            'old_rank',
            type = int,
            help = 'The rank of the crew prior to renumbering',
        )
        
        parser.add_argument(
            '--source',
            default = Sources.LIVE_BUMPS,
            choices = [Sources.LIVE_BUMPS, Sources.OURCS],
            help = f'The source of start order data (default: {Sources.LIVE_BUMPS})',
        )
    
    @staticmethod
    def perform_crew_list_update(source_function, event, target_crew, source_crew_tuple):
        """Retrieves the source crew's crew list and stores it for the target crew."""
        
        crew_lists = source_function(event.series, event.year)
        if source_crew_tuple not in crew_lists:
            raise ValueError('Source crew designation not found in the retrieved crew lists')
        
        target_crew.crew_lists.filter(event = event).delete()
        # ^Linked purchases set to anon athlete
        
        tools.add_athletes(
            event,
            {target_crew.as_tuple(): target_crew},
            {target_crew.as_tuple(): crew_lists[source_crew_tuple]},
        )
    
    
    def handle(self, *args, **kwargs):
        """Validates and converts the inputs for the `perform` function."""
        
        event = models.Event.objects.get(tag = kwargs['event_tag'])
        
        target_crew = models.Crew.objects.get(
            club = kwargs['club'],
            gender = kwargs['gender'],
            rank = kwargs['new_rank'],
        )
        if not models.Position.objects.filter(day__event = event, crew = target_crew).count():
            raise models.Position.DoesNotExist('This crew is not entered into this event.')
        
        source_crew_tpl = (target_crew.club, target_crew.gender, kwargs['old_rank'])
        logger.info('Correcting crew list for {} as their original {}{}'.format(
            target_crew,
            target_crew.gender,
            source_crew_tpl[2],
        ))
        
        crew_list_fcn = {
            Sources.LIVE_BUMPS: live_bumps.get_crew_lists,
            Sources.OURCS: ourcs.get_crew_lists,
        }[kwargs.get('source', Sources.LIVE_BUMPS)]
        
        self.perform_crew_list_update(crew_list_fcn, event, target_crew, source_crew_tpl)
        logger.info(f'Corrected crew list for {target_crew}')

