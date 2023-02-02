from typing import TypedDict
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.core.management import call_command
from typing_extensions import Unpack


class InitArgs(TypedDict):
    dev_team: bool


class Command(BaseCommand):
    help = 'Initialises the database and loads any fixed data.'

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('--dev-team', action = 'store_true', help = 'Load a development team')
    
    
    def handle(self, **kwargs: Unpack[InitArgs]) -> None:
        
        call_command('migrate')
        call_command('loaddata', 'seats')
        
        if kwargs['dev_team']:
            call_command('loaddata', 'dev_team')

