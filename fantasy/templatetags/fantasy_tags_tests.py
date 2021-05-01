from datetime import time, timedelta
from xml.etree import ElementTree as ET

from django.test import TestCase, tag
from django.utils import timezone
from django import template

from .. import models
from .. import patching
from ..constants import timings
from . import fantasy_tags as tags


def parser(string):
    return ET.fromstring('''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
  [<!ENTITY nbsp ' '> <!ENTITY minus '-'> <!ENTITY plus '+'>]
>
''' + string)


@tag('market-status')
class Test__Market_Status_Box(TestCase):
    fixtures = ['dev_event']
    
    @classmethod
    def setUpTestData(cls):
        cls.event = models.Event.objects.first()
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 2))
    def test__open_two_days(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {0:%H:%M} {0:%d/%m/%Y}.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() + timedelta(days = 1))
    def test__open_tomorrow(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} tomorrow.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() + timedelta(minutes = 5))
    def test__open_later_today(self, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} today.'.format(
                opens_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(days = 1))
    def test__open_until_tomorrow(self, closes_mock, opens_mock):
        """Returns a dismissable info alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'info')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} tomorrow.'.format(
                closes_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__open_until_later(self, closes_mock, opens_mock):
        """Returns a dismissable info alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'warning')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} today.'.format(
                closes_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() + timedelta(minutes = 5))
    def test__open_until_later_no_dismiss(self, closes_mock, opens_mock):
        """Returns a non-dismissable info alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day, False)
        
        self.assertEqual(props['style'], 'warning')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} today.'.format(
                closes_mock.return_value,
            ),
        )
    
    
    @patching.market_opens(timezone.now() - timedelta(minutes = 5))
    @patching.market_closes(timezone.now() - timedelta(minutes = 2))
    def test__after_close(self, closes_mock, opens_mock):
        """Returns a non-dismissable danger alert."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed.',
        )
    
    
    def test__after_close_with_next(self):
        """Returns a non-dismissable danger alert with the open time for the next day.
        
        WARNING: Contains non-standard mocking. May not fail if other code changes.
        """
        
        # Create first day and fix return values
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = time(hour = 12),
        )
        day.market_opens = timezone.now() - timedelta(minutes = 5)  # Non-standard mocking
        day.market_closes = timezone.now() - timedelta(minutes = 2)  # Non-standard mocking
        
        # Create later day
        self.event.days.create(
            name = 'Market Status 2',
            date = timezone.now() + timedelta(2),  # Ensure market never opens today
            first_race_time = time(hour = 12),
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} tomorrow.'.format(
                timings.MARKET_OPENS,
            ),
        )
    
    
    def test__non_racing_day(self):
        """Returns a non-dismissable danger alert.
        
        A special case of test__after_close since markets are always closed for non-racing days,
        but market_opens and market_closes do not return datetime objects."""
        
        # Create day
        day = self.event.days.create(
            name = 'Market Status',
            date = timezone.now(),
            first_race_time = None,
        )
        
        # Call and test method
        props = tags.market_status_box(day)
        
        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed.',
        )



@tag('frontend')
class Test__Avatar(TestCase):
    
    def test__string(self):
        """Puts the received text in the middle of a avatar span."""
        
        self.assertHTMLEqual(
            tags.avatar('C'),
            '<span class="avatar">C</span>',
        )
    
    
    def test__int(self):
        """Will accept an integer value."""
        
        self.assertHTMLEqual(
            tags.avatar(7),
            '<span class="avatar">7</span>',
        )
    
    
    def test__with_club(self):
        """Converts the second argument into an additional class."""
        
        self.assertHTMLEqual(
            tags.avatar(7, 'newc'),
            '<span class="avatar club-newc">7</span>',
        )



@tag('frontend')
class Test__Misc(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.first()
        cls.seat = models.Seat.objects.first()
        cls.position = cls.crew.positions.get(day = cls.day)
        cls.position.bungline = 1  # Expected to be set
        cls.position.popularity = 0  # Expected to be set
    
    
    @staticmethod
    def buy_button(position, disabled = False):
        """A helper function that renders a buy button."""
        return (
            template
            .Template('{% load fantasy_tags %}{% buy_button position disabled %}')
            .render(template.Context({'position': position, 'disabled': disabled}))
        )
    
    
    @staticmethod
    def market_row(position, balance, show_actions = True):
        """A helper function that renders a market row."""
        return (
            template
            .Template('{% load fantasy_tags %}{% market_row position balance show_actions %}')
            .render(template.Context({
                'position': position,
                'balance': balance,
                'show_actions': show_actions,
            }))
        )
    
    
    def test__currency_filter(self):
        """Renders the amount with currency symbol."""
        
        html = tags.currency(100)
        self.assertEqual(html, '100&nbsp;🦀')
    
    
    def test__buy_button__standard(self):
        """Renders a styled button with an attached function call."""
        
        html = self.buy_button(self.position, disabled = False)
        button = parser(html)
        
        self.assertEqual(button.tag, 'button')
        
        classes = button.get('class').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-buy', classes)
        self.assertNotIn('disabled', classes)
        
        self.assertEqual(button.get('data-day'), str(self.day.id))
        self.assertEqual(button.get('data-crew'), str(self.crew.id))
        
        self.assertInHTML('Buy ' + tags.currency(self.crew.value(self.day)), html)
    
    
    def test__buy_button__disabled(self):
        """Includes the disabled class and does not have a function call."""
        
        html = self.buy_button(self.position, disabled = True)
        button = parser(html)
        
        self.assertEqual(button.tag, 'button')
        
        classes = button.get('class').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-buy', classes)
        self.assertIn('disabled', classes)
        
        self.assertFalse('data-day' in button.attrib)
        self.assertFalse('data-crew' in button.attrib)
        
        self.assertInHTML('Buy ' + tags.currency(self.crew.value(self.day)), html)
    
    
    def test__market_row__standard(self):
        """Renders a styled div, that contains an avatar, crew box, and buy button."""
        
        html = self.market_row(self.position, 675)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('market-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.position.bungline, self.crew.club)
        self.assertInHTML(avatar, html)
        
        crew = '<div class="flex-grow-1">{}</div>'.format(self.crew)
        self.assertInHTML(crew, html)
        
        buy_button = self.buy_button(self.position)
        self.assertInHTML(buy_button, html)
    
    
    def test__market_row__cant_afford(self):
        """Renders a styled div, that contains an avatar, crew box, and disabled buy button."""
        
        html = self.market_row(self.position, 1)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('market-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.position.bungline, self.crew.club)
        self.assertInHTML(avatar, html)
        
        crew = '<div class="flex-grow-1">{}</div>'.format(self.crew)
        self.assertInHTML(crew, html)
        
        buy_button = self.buy_button(self.position, disabled = True)
        self.assertInHTML(buy_button, html)
    
    
    def test__market_row__show_actions_false(self):
        """Renders a styled div, that contains an avatar and crew box, but not a buy button.
        
        N.B. View passes 'balance' is an empty string if missing.
        """
        
        position = models.Position.objects.first()
        position.bungline = 1  # Expected to be set
        position.popularity = 0  # Expected to be set
        html = self.market_row(position, '', show_actions = False)
        
        # Test containments
        self.assertNotIn('btn-buy', html)



@tag('frontend')
class Test__Crew_List(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']
    
    @classmethod
    def setUpTestData(cls):
        cls.team = models.Team.objects.first()
        cls.day = models.Day.objects.first()
        cls.crew = models.Crew.objects.first()
        cls.seat = models.Seat.objects.first()
    
    
    @staticmethod
    def sell_button(purchase):
        """A helper function that renders a sell button."""
        return (
            template
            .Template('{% load fantasy_tags %}{% sell_button purchase %}')
            .render(template.Context({'purchase': purchase}))
        )
    
    
    @staticmethod
    def crew_list_header(finances):
        """A helper function that renders a crew list header."""
        return (
            template
            .Template('{% load fantasy_tags %}{% crew_list_header finances %}')
            .render(template.Context({'finances': finances}))
        )
    
    
    @staticmethod
    def crew_list_row(seat, purchase, show_actions = True):
        """A helper function that renders a crew row."""
        return (
            template
            .Template('{% load fantasy_tags %}{% crew_list_row seat purchase show_actions %}')
            .render(template.Context({
                'seat': seat,
                'purchase': purchase,
                'show_actions': show_actions,
            }))
        )
    
    
    @staticmethod
    def crew_list_box(crew_list, finances = {}, show_actions = False):
        """A helper function that renders a crew list."""
        return (
            template
            .Template('{% load fantasy_tags %}{% crew_list_box crew_list finances show_actions %}')
            .render(template.Context({
                'crew_list': crew_list,
                'finances': finances,
                'show_actions': show_actions,
            }))
        )
    
    
    def test__sell_button(self):
        """Renders a styled button."""
        
        purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        )
        html = self.sell_button(purchase)
        button = parser(html)
        
        self.assertEqual(button.tag, 'button')
        
        classes = button.get('class').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-sell', classes)
        
        self.assertEqual(button.get('data-purchase'), str(purchase.id))
        
        self.assertInHTML('Sell ' + tags.currency(self.crew.value(self.day)), html)
    
    
    def test__crew_list_row__no_purchase(self):
        """Renders a styled div, that contains an avatar."""
        
        html = self.crew_list_row(self.seat, None)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('crew-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.seat.short)
        self.assertInHTML(avatar, html)
        
        self.assertNotIn('<div class="flex-grow-1">', html)
        self.assertNotIn('btn', html)
    
    
    def test__crew_list_row__with_purchase(self):
        """Renders a styled div, that contains an avatar, crew box, and a sell button."""
        
        purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        )
        html = self.crew_list_row(self.seat, purchase)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('crew-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.seat.short, self.crew.club)
        self.assertInHTML(avatar, html)
        
        crew = '<div class="flex-grow-1"><div>{}</div></div>'.format(self.crew)
        self.assertInHTML(crew, html)
        
        sell_button = self.sell_button(purchase)
        self.assertInHTML(sell_button, html)
    
    
    def test__crew_list_row__with_athlete(self):
        """Renders a styled div, that contains an avatar, crew & athlete box, and a sell button."""
        
        athlete = self.crew.crew_lists.create(
            event = self.day.event,
            seat = self.seat,
            name = 'Test Athlete',
        )
        
        purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew,
            athlete = athlete,
        )
        html = self.crew_list_row(self.seat, purchase)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('crew-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.seat.short, self.crew.club)
        self.assertInHTML(avatar, html)
        
        crew = '''
          <div class="flex-grow-1 crew-row-athlete">
            <div>{}</div>
            <div>{}</div>
          </div>'''.format(athlete.name, self.crew)
        self.assertInHTML(crew, html)
        
        sell_button = self.sell_button(purchase)
        self.assertInHTML(sell_button, html)
    
    
    def test__crew_list_row__show_actions_false(self):
        """Renders a styled div, that contains an avatar and crew box, but not a sell button."""
        
        purchase = self.team.purchases.create(
            day = self.day,
            seat = self.seat,
            crew = self.crew,
        )
        html = self.crew_list_row(self.seat, purchase, show_actions = False)
        
        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('crew-row', row.get('class').split())
        
        # Test containments
        avatar = tags.avatar(self.seat.short, self.crew.club)
        self.assertInHTML(avatar, html)
        
        crew = '<div class="flex-grow-1"><div>{}</div></div>'.format(self.crew)
        self.assertInHTML(crew, html)
        
        self.assertNotIn('btn', html)
    
    
    def test__crew_list_box__empty_list(self):
        """Renders a styled div that always has all seats."""
        
        html = self.crew_list_box([])
        
        # Test root
        crew_list = parser(html)
        self.assertEqual(crew_list.tag, 'div')
        
        # Test containments
        for seat in models.Seat.objects.all():
            with self.subTest(seat = seat.name):
                self.assertInHTML(
                    self.crew_list_row(seat, None),
                    html,
                )
    
    
    def test__crew_list_box__with_purchase(self):
        """Renders a styled div that includes any purchases provided."""
        
        purchase = self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        html = self.crew_list_box([purchase])
        
        # Test root
        crew_list = parser(html)
        self.assertEqual(crew_list.tag, 'div')
        
        # Test containments
        self.assertInHTML(
            self.crew_list_row(purchase.seat, purchase, show_actions = False),
            html,
        )
        
        for seat in models.Seat.objects.exclude(id = purchase.seat.id):
            with self.subTest(seat = seat.name):
                self.assertInHTML(
                    self.crew_list_row(seat, None),
                    html,
                )
    
    
    def test__crew_list_box__finances(self):
        """Includes financial information if provided."""
        
        finances = {'budget': 1079, 'crew_value': 856, 'balance': 223}
        html = self.crew_list_box([], finances)
        
        # Test containments
        self.assertInHTML(self.crew_list_header(finances), html)
        
    
    
    def test__crew_list_box__show_actions(self):
        """Propagates the show_actions flag."""
        
        purchase = self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        html = self.crew_list_box([purchase], show_actions = True)
        
        # Test root
        crew_list = parser(html)
        self.assertEqual(crew_list.tag, 'div')
        
        # Test containments
        self.assertInHTML(
            self.crew_list_row(purchase.seat, purchase, show_actions = True),
            html,
        )
        
        for seat in models.Seat.objects.exclude(id = purchase.seat.id):
            with self.subTest(seat = seat.name):
                self.assertInHTML(
                    self.crew_list_row(seat, None),
                    html,
                )

