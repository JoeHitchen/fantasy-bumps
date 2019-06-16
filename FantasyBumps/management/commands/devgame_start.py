from datetime import time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone

from ... import models


class Command(BaseCommand):
    def handle(self, *args, **kwags):
        """Prepares a dev game.
        
        Requires a database with no pre-existing events.
        """
        
        if models.Event.objects.exists():
            raise CommandError('An event already exists')
        
        call_command('loaddata', 'seats', 'dev_crews', 'dev_event')
        
        models.Day(
            id = 1,
            event = models.Event.objects.first(),
            name = 'Day One',
            date = timezone.now() + timedelta(5),
            first_race_time = time(12, 00),
        ).save()
        
        models.Day(
            id = 2,
            event = models.Event.objects.first(),
            name = 'Day Two',
            date = timezone.now() + timedelta(6),
            first_race_time = time(12, 00),
        ).save()
        
        models.Day(
            id = 3,
            event = models.Event.objects.first(),
            name = 'Day Three',
            date = timezone.now() + timedelta(7),
        ).save()
        
        call_command('loaddata', 'dev_start_day1')
        
        self.stdout.write('Successfully created a development game.')

