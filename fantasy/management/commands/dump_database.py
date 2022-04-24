from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Dumps all database tables used into a file, for backup purposes.'
    
    suppressed_base_arguments = [
        '--version',
        '-v',
        '--settings',
        '--pythonpath',
        '--traceback',
        '--no-color',
        '--force-color',
        '--skip-checks',
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            help = 'The filename for the generated data. `.json` is added if missing.',
        )
    
    
    def handle(self, *args, **kwargs):
        
        filename = kwargs['filename']
        if len(filename.split('.')) == 1 or not filename.split('.')[-1] == 'json':
            filename += '.json'
        
        self.stdout.write('Dumping database to {}...'.format(filename))
        call_command('dumpdata', 'auth.user', 'fantasy', indent = 2, output = filename)
        self.stdout.write('Completed!')

