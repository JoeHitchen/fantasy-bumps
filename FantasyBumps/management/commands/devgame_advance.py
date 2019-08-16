from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone

from ... import models
from ...utils import evaluate_all_investments


class Command(BaseCommand):
    def handle(self, *args, **kwags):
        """Advances the dev game 24 hours.
        
        Should only be used after calling `devgame_start`.
        Requires days to have IDs 1-3.
        """
        
        event = models.Event.objects.first()
        if not event:
            raise CommandError('No event found!')
        
        first_race = event.active_day.first_race
        
        if first_race and first_race - timezone.now() < timedelta(1):
            call_command(
                'loaddata',
                'dev_start_day{}'.format(event.active_day.id + 1),
            )
            event.active_day.advance_purchases_to_next()
            evaluate_all_investments(event.active_day)
        
        event.days.update(date = F('date') - timedelta(1))
        
        self.stdout.write('Successfully advanced the development game by 24 hours.')

