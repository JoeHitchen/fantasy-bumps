from unittest.mock import patch, Mock

from django.test import TestCase

from parsing import ourcs

from ... import models
from ...constants import Clubs
from .renumbered_crew import Command as RenumberedCrew


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

