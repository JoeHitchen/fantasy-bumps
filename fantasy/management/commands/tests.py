from unittest.mock import patch, Mock
import logging

from django.test import TestCase
from django.utils import timezone

from parsing import live_bumps, anu, camfm, ourcs

from ... import models
from ...constants import Series, Clubs, Sources
from .game_start import create_days
from .game_advance import Command as GameAdvance, _demo_wrapper
from .renumbered_crew import Command as RenumberedCrew

logging.disable(logging.CRITICAL)


def prepare_event(series, start_date):
    event = models.Event.objects.create(
        series = series,
        year = start_date.year,
        tag = f'{series.label.lower()}{start_date.year}',
    )
    create_days(event, start_date)
    return event


class Test__Game_Advance(TestCase):
    
    today = timezone.now().date()
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__oxford_default_source(self, perform_mock):
        """Live Bumps is the default source used for Oxford events."""
        
        event = prepare_event(Series.TORPIDS, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(live_bumps.get_positions, event)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__oxford_specified_source(self, perform_mock):
        """Alternative sources can be used for Oxford events."""
        
        event = prepare_event(Series.TORPIDS, self.today)
        
        GameAdvance().handle(oxf_source = 'anu')
        perform_mock.assert_called_once_with(anu.get_positions, event)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__cambridge_default_source(self, perform_mock):
        """CamFM is the default source used for Cambridge events."""
        
        event = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(camfm.get_positions, event)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__demo_default_source(self, perform_mock):
        """An internal method is the default source used for Demo events."""
        
        event = prepare_event(Series.DEMO, self.today)
        
        GameAdvance().handle()
        perform_mock.assert_called_once_with(_demo_wrapper, event)
    
    
    @patch.object(GameAdvance, 'perform_game_advance')
    def test__handle__two_events(self, perform_mock):
        """Two events can be updated simultaneously."""
        
        torpids = prepare_event(Series.TORPIDS, self.today)
        lents = prepare_event(Series.LENTS, self.today)
        
        GameAdvance().handle()
        self.assertEqual(perform_mock.call_count, 2)
        perform_mock.assert_any_call(live_bumps.get_positions, torpids)
        perform_mock.assert_any_call(camfm.get_positions, lents)


class Test__Renumbered_Crew(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'seats']
    
    crew_list = {
        1: 'Test 1',
        2: 'Test 2',
        3: 'Test 3',
        4: 'Test 4',
        5: 'Test 5',
        6: 'Test 6',
        7: 'Test 7',
        8: 'Test 8',
        9: 'Test 9',
        10: 'Test 10',
    }
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
        cls.target_crew = models.Crew.objects.filter(club = Clubs.HERT).first()
        cls.source_crew_rank = cls.target_crew.rank + 1
        cls.source_crew_tpl = (
            cls.target_crew.club,
            cls.target_crew.gender,
            cls.source_crew_rank,
        )
    
    
    def test__handle__event_missing(self):
        """Raises an error the event does not exist."""
        
        with self.assertRaises(models.Event.DoesNotExist):
            RenumberedCrew().handle(
                event_tag = 'other2022',
                club = self.target_crew.club,
                gender = self.target_crew.gender,
                new_rank = self.target_crew.rank,
                old_rank = self.source_crew_rank,
            )
    
    
    def test__handle__crew_not_in_event(self):
        """Raises an error if the target crew has no positions for the event."""
        
        with self.assertRaises(models.Crew.DoesNotExist):
            RenumberedCrew().handle(
                event_tag = self.event.tag,
                club = self.target_crew.club,
                gender = self.target_crew.gender,
                new_rank = self.source_crew_rank,
                old_rank = self.source_crew_rank + 1,
            )
    
    
    @patch.object(RenumberedCrew, 'perform_crew_list_update')
    def test__handle__valid(self, perform_mock):
        """Converts inputs to python objects for the `perform` function."""
        
        RenumberedCrew().handle(
            event_tag = self.event.tag,
            club = self.target_crew.club,
            gender = self.target_crew.gender,
            new_rank = self.target_crew.rank,
            old_rank = self.source_crew_rank,
        )
        
        perform_mock.assert_called_once_with(
            live_bumps.get_crew_lists,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
    
    
    @patch.object(RenumberedCrew, 'perform_crew_list_update')
    def test__handle__ourcs_source(self, perform_mock):
        """Can use the OURCs website as an alternative crew list source."""
        
        RenumberedCrew().handle(
            event_tag = self.event.tag,
            club = self.target_crew.club,
            gender = self.target_crew.gender,
            new_rank = self.target_crew.rank,
            old_rank = self.source_crew_rank,
            source = Sources.OURCS,
        )
        
        perform_mock.assert_called_once_with(
            ourcs.get_crew_lists,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
    
    
    def test__perform__source_call(self):
        """Calls the crew list source function with the event series and year."""
        
        source_mock = Mock(return_value = {self.source_crew_tpl: self.crew_list})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        source_mock.assert_called_once_with(self.event.series, self.event.year)
    
    
    def test__perform__no_crew_list_found(self):
        """Raises an error if no crew list is found for the source crew designation."""
        
        source_mock = Mock(return_value = {})
        
        with self.assertRaises(ValueError):
            RenumberedCrew.perform_crew_list_update(
                source_mock,
                self.event,
                self.target_crew,
                self.source_crew_tpl,
            )
    
    
    def test__perform__original_athletes_removed(self):
        """Athletes already recorded against the target crew should be removed."""
        
        for seat in range(1, 10):
            self.target_crew.crew_lists.create(
                event = self.event,
                seat_id = seat,
                name = f'Old {seat}',
            )
        
        source_mock = Mock(return_value = {self.source_crew_tpl: {}})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        self.assertFalse(list((
            self.target_crew.crew_lists
            .filter(event = self.event)
            .values_list('seat', 'name')
        )))
    
    
    def test__perform__new_athletes_added(self):
        """The crew list from the source crew should be loaded into the database."""
        
        source_mock = Mock(return_value = {self.source_crew_tpl: self.crew_list})
        
        RenumberedCrew.perform_crew_list_update(
            source_mock,
            self.event,
            self.target_crew,
            self.source_crew_tpl,
        )
        
        self.assertEqual(
            list((
                self.target_crew.crew_lists
                .filter(event = self.event)
                .values_list('seat', 'name')
            )),
            [(seat, name) for seat, name in self.crew_list.items() if seat < 10],
        )

