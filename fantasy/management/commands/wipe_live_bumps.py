from django.core.management.base import BaseCommand

from integrations import live_bumps

from ...constants import Series

series_reverser = {series.label.lower(): series for series in Series}


class Command(BaseCommand):
    help = 'Wipes an event on Live Bumps.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'series',
            choices = [label.lower() for label in Series.labels],
            help = "The target event's series",
        )
        parser.add_argument(
            'year',
            type = int,
            help = "The target event's year.",
        )
    
    
    def handle(self, *args, **kwargs):
        live_bumps.wipe_positions(series_reverser[kwargs['series']], kwargs['year'])

