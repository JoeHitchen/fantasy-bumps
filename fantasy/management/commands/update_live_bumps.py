from datetime import timedelta
from typing import TypedDict
from argparse import ArgumentParser
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from typing_extensions import Unpack

from integrations import anu_dat, live_bumps

from ...constants import Series, Genders
from ... import models

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger('fantasy.live_pipeline')

series_reverser = {series.label.lower(): series for series in Series}
gender_reverser = {gender.label.lower(): gender for gender in Genders}


class UpdateArgs(TypedDict):
    series: str
    year: int
    gender: str


class Command(BaseCommand):
    help = 'Updates the results on Live Bumps for one gender.'
    
    def add_arguments(self, parser: ArgumentParser) -> None:
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
    
    @staticmethod
    def perform_update(event: models.Event, gender: Genders) -> live_bumps.WriteOutcome:
        """Loads crew positions from Anu's data files and pushes them to Live Bumps."""
        
        active_days = list(event.days.filter(date__lte = timezone.now() + timedelta(1)))
        if len(active_days) < 2:
            return (0, 0, 0)
        
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
        if active_days[-1].date > now.date():
            
            start_order = anu_dat.get_start_order_by_gender(
                event.series,
                event.year,
                gender,
                len(active_days) - 1,
            )
            unraced_crews = [
                crew for division in start_order for crew, _ in division['crews']
                if division['race_time'] >= now.time()
            ]
            for crew in unraced_crews:
                del positions_by_day[-1][crew]
        
        return live_bumps.write_positions(event.series, event.year, positions_by_day)
    
    
    def handle(self, **kwargs: Unpack[UpdateArgs]) -> None:
        """A wrapper to parse the inputs for the main `perform_update` routine."""
        
        series = series_reverser[kwargs['series']]
        year = kwargs['year']
        gender = gender_reverser[kwargs['gender']]
        logger.info('Updating Live Bumps for {} {} ({})'.format(series.label, year, gender.label))
        
        event = models.Event.objects.get(series = series, year = year)
        self.perform_update(event, gender)
        logger.info('Updated Live Bumps for {} {} ({})'.format(series.label, year, gender.label))

