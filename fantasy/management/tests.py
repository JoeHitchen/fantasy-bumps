from django.test import TestCase
from django.utils import timezone
from django_q.tasks import Schedule

from . import tasks
from ..constants import Series
from .commands.tests import prepare_event


class Test__Schedule(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.event = prepare_event(Series.DEMO, timezone.now().date())
    
    
    def test__repeats(self):
        """Enough minutely repeats must be set to cover the event."""
        
        tasks.schedule_live_bumps_updates(self.event)
        
        schedules = Schedule.objects.all()
        self.assertTrue(3 * 24 * 60 < schedules[0].repeats < 4 * 24 * 60)
        self.assertTrue(3 * 24 * 60 < schedules[1].repeats < 4 * 24 * 60)

