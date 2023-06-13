from typing import TypedDict
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from typing_extensions import Unpack

from ...constants import Series, Genders
from ... import models
from .. import actions

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
    
    
    def handle(self, **kwargs: Unpack[UpdateArgs]) -> None:
        """A wrapper to parse the inputs for the main `perform_update` routine."""
        
        event = models.Event.objects.get(
            series = series_reverser[kwargs['series']],
            year = kwargs['year'],
        )
        actions.update_live_bumps(event, gender_reverser[kwargs['gender']])

