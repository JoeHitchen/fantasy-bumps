from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from integrations import anu_dat, live_bumps

from ...constants import Series, Genders
from ... import models

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.live_pipeline')

series_reverser = {series.label.lower(): series for series in Series}
gender_reverser = {gender.label.lower(): gender for gender in Genders}


class Command(BaseCommand):
    help = 'Updates the results on Live Bumps for one gender.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'series',
            choices = series_reverser.keys(),
            help = "The target event's series",
        )
        parser.add_argument(
            'year',
            type = int,
            help = "The target event's year.",
        )
        parser.add_argument(
            'gender',
            choices = gender_reverser.keys(),
            help = 'The gender to update',
        )
    
    
    def handle(self, *args, **kwargs):
        """Loads crew positions from Anu's data files and pushes them to Live Bumps."""
        
        series = Series(series_reverser[kwargs['series']])
        year = kwargs['year']
        gender = Genders(gender_reverser[kwargs['gender']])
        logger.info('Updating Live Bumps for {} {} ({})'.format(series.label, year, gender.label))
        
        event = models.Event.objects.get(series = series, year = year)
        active_days = event.days.filter(date__lte = timezone.now() + timedelta(1))
        if active_days.count() < 2:
            return
        
        # Load positions
        positions_by_day = []
        for day_number, day in enumerate(active_days, 1):
            positions_by_day.append(anu_dat.get_positions_by_gender(
                event.series,
                event.year,
                gender,
                day_number,
            ))
        
        # Prune unraced crews
        now = timezone.now()
        if active_days.last().date > now.date():
            
            start_order = anu_dat.load_start_order_by_gender(
                event.series,
                event.year,
                gender,
                active_days.count() - 1,
            )
            unraced_crews = [
                crew for division in start_order for crew, _ in division['crews']
                if division['race_time'] >= now.time()
            ]
            for crew in unraced_crews:
                del positions_by_day[-1][crew]
        
        live_bumps.write_positions(event.series, event.year, positions_by_day)
        logger.info('Updated Live Bumps for {} {} ({})'.format(series.label, year, gender.label))

