from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Initialises the database and loads any fixed data.'

    def add_arguments(self, parser):
        parser.add_argument('--dev-team', action = 'store_true', help = 'Load a development team')
    
    
    def handle(self, *args, **kwargs):
        
        call_command('migrate')
        call_command('loaddata', 'seats')
        
        if kwargs['dev_team']:
            call_command('loaddata', 'dev_team')

