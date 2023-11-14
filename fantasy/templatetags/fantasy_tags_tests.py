from datetime import time, timedelta
from xml.etree import ElementTree as ET
from typing import Iterable
from unittest.mock import Mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.db import models as db
from django import template

from core.tests import exists

from .. import models
from .. import patching
from ..constants import Genders
from . import fantasy_tags as tags, fantasy_tags_types as types



def parser(string: str) -> ET.Element:
    return ET.fromstring('''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
  [<!ENTITY nbsp ' '> <!ENTITY minus '-'> <!ENTITY plus '+'>]
>
''' + string)


class Test__Market_Status_Box(TestCase):
    fixtures = ['dev_event']

    event: models.Event

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())


    def setUp(self) -> None:
        self.day = self.event.days.create(
            name = 'Status 1',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        self.next_day = self.event.days.create(
            name = 'Status 2',
            date = timezone.localtime().date() + timedelta(2),  # Ensure market never opens today
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )


    @patching.market_opens(timezone.localtime() + timedelta(days = 2))
    def test__opens_in_two_days(self, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {0:%H:%M} on {0:%A}.'.format(
                opens_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() + timedelta(days = 1))
    def test__opens_tomorrow(self, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} tomorrow.'.format(
                opens_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() + timedelta(minutes = 5))
    def test__opens_later_today(self, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} today.'.format(
                opens_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(days = 2))
    def test__open_for_two_days(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a dismissable info alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'info')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {0:%H:%M} on {0:%A}.'.format(
                closes_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(days = 1))
    def test__open_until_tomorrow(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a dismissable info alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'info')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} tomorrow.'.format(
                closes_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 5))
    def test__open_until_later(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a dismissable info alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'warning')
        self.assertTrue(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} today.'.format(
                closes_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 5))
    def test__open_until_later_no_dismiss(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a non-dismissable info alert."""

        # Call and test method
        props = tags.market_status_box(self.day, False)

        self.assertEqual(props['style'], 'warning')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is open until {:%H:%M} today.'.format(
                closes_mock.return_value,
            ),
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() - timedelta(minutes = 2))
    def test__after_close(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is closed.',
        )


    @patching.market_opens(timezone.localtime() + timedelta(minutes = 500))  # Affects second day
    def test__after_close_with_next(self, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert with the open time for the next day.

        WARNING: Contains non-standard mocking. May not fail if other code changes.
        """

        # Non-standard mocking of first day market times
        self.day.market_opens = timezone.localtime() - timedelta(minutes = 5)
        self.day.market_closes = timezone.localtime() - timedelta(minutes = 2)

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])

        if opens_mock.return_value.date() == timezone.localtime().date():
            today_tomorrow = 'today'
        else:
            today_tomorrow = 'tomorrow'
        self.assertEqual(
            props['message'],
            'The market is closed, and will open at {:%H:%M} {}.'.format(
                opens_mock.return_value,
                today_tomorrow,
            ),
        )


    def test__last_day(self) -> None:
        """Returns a non-dismissable info alert."""

        # Alter test setup
        self.day.first_race_time = None
        self.day.last_race_time = None
        self.day.save()
        self.next_day.delete()

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'info')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'This event has concluded.',
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 5))
    def test__held_closed(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Alter test setup
        self.day.event.market_held_closed = True

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is being held closed for technical reasons.',
        )


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 5))
    def test__previous_no_advance(self, closes_mock: Mock, opens_mock: Mock) -> None:
        """Returns a non-dismissable danger alert."""

        # Alter test setup
        self.day.event.days.create(
            name = 'Previous',
            date = self.day.date - timedelta(1),
            first_race_time = self.day.first_race_time,
            last_race_time = self.day.last_race_time,
            advanced = False,
        )

        # Call and test method
        props = tags.market_status_box(self.day)

        self.assertEqual(props['style'], 'danger')
        self.assertFalse(props['dismissable'])
        self.assertEqual(
            props['message'],
            'The market is being held closed for technical reasons.',
        )



class Test__Avatar(TestCase):

    def test__string(self) -> None:
        """Puts the received text in the middle of a avatar span."""

        self.assertHTMLEqual(
            tags.avatar('C'),
            '<span class="avatar flex-shrink-0">C</span>',
        )


    def test__int(self) -> None:
        """Will accept an integer value."""

        self.assertHTMLEqual(
            tags.avatar(7),
            '<span class="avatar flex-shrink-0">7</span>',
        )


    def test__with_club(self) -> None:
        """Converts the second argument into an additional class."""

        self.assertHTMLEqual(
            tags.avatar(7, 'newc'),
            '<span class="avatar club-newc flex-shrink-0">7</span>',
        )



class Test__Misc(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']

    team: models.Team
    day: models.Day
    crew: models.Crew
    seat: models.Seat
    position: types.PositionWithPopularity

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())
        cls.crew = exists(models.Crew.objects.first())
        cls.seat = exists(models.Seat.objects.first())

        position_annotations = {'bungline': db.Value(1), 'popularity': db.Value(0.)}
        cls.position = cls.crew.positions.annotate(**position_annotations).get(day = cls.day)


    @staticmethod
    def buy_button(position: types.PositionWithPopularity, disabled: bool = False) -> str:
        """A helper function that renders a buy button."""
        return (
            template
            .Template('{% load fantasy_tags %}{% buy_button position disabled %}')
            .render(template.Context({'position': position, 'disabled': disabled}))
        )


    @staticmethod
    def market_row(
        position: types.PositionWithPopularity,
        balance: int,
        show_actions: bool = True,
    ) -> str:
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


    def test__currency_filter(self) -> None:
        """Renders the amount with currency symbol."""

        html = tags.currency(100)
        self.assertEqual(html, '100&nbsp;🦀')


    def test__buy_button__standard(self) -> None:
        """Renders a styled button with associated data."""

        html = self.buy_button(self.position, disabled = False)
        button = parser(html)

        self.assertEqual(button.tag, 'button')

        classes = button.get('class', '').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-buy', classes)
        self.assertNotIn('disabled', classes)

        self.assertEqual(button.get('data-day'), str(self.day.id))
        self.assertEqual(button.get('data-crew'), str(self.crew.id))

        self.assertInHTML('Buy ' + tags.currency(self.crew.value(self.day)), html)


    def test__buy_button__disabled(self) -> None:
        """Includes the disabled class and does not have any data."""

        html = self.buy_button(self.position, disabled = True)
        button = parser(html)

        self.assertEqual(button.tag, 'button')

        classes = button.get('class', '').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-buy', classes)
        self.assertIn('disabled', classes)

        self.assertFalse('data-day' in button.attrib)
        self.assertFalse('data-crew' in button.attrib)

        self.assertInHTML('Buy ' + tags.currency(self.crew.value(self.day)), html)


    def test__market_row__standard(self) -> None:
        """Renders a styled div, that contains an avatar, crew box, and buy button."""

        html = self.market_row(self.position, 675)

        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('market-row', row.get('class', '').split())

        # Test containments
        avatar = tags.avatar(self.position.bungline, self.crew.club)
        self.assertInHTML(avatar, html)

        crew = '<div class="flex-grow-1">{}</div>'.format(self.crew)
        self.assertInHTML(crew, html)

        buy_button = self.buy_button(self.position)
        self.assertInHTML(buy_button, html)


    def test__market_row__cant_afford(self) -> None:
        """Renders a styled div, that contains an avatar, crew box, and disabled buy button."""

        html = self.market_row(self.position, 1)

        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('market-row', row.get('class', '').split())

        # Test containments
        avatar = tags.avatar(self.position.bungline, self.crew.club)
        self.assertInHTML(avatar, html)

        crew = '<div class="flex-grow-1">{}</div>'.format(self.crew)
        self.assertInHTML(crew, html)

        buy_button = self.buy_button(self.position, disabled = True)
        self.assertInHTML(buy_button, html)


    def test__market_row__show_actions_false(self) -> None:
        """Renders a styled div, that contains an avatar and crew box, but not a buy button.

        N.B. View passes 'balance' is an empty string if missing.
        """

        html = self.market_row(self.position, 0, show_actions = False)

        # Test containments
        self.assertNotIn('btn-buy', html)



class Test__Crew_List(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1', 'dev_team', 'seats']

    day: models.Day
    crew: models.Crew
    seat: models.Seat
    seats: db.QuerySet[models.Seat]

    team: models.Team
    purchase: models.Purchase

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())
        cls.crew = exists(models.Crew.objects.first())
        cls.seat = exists(models.Seat.objects.first())
        cls.seats = models.Seat.objects.all()

        cls.purchase = cls.team.purchases.create(
            day = cls.day,
            seat = cls.seat,
            crew = cls.crew,
        )


    @staticmethod
    def sell_button(purchase: models.Purchase) -> str:
        """A helper function that renders a sell button."""
        return (
            template
            .Template('{% load fantasy_tags %}{% sell_button purchase %}')
            .render(template.Context({'purchase': purchase}))
        )


    @staticmethod
    def crew_list_header(finances: types.GenderFinances) -> str:
        """A helper function that renders a crew list header."""
        return (
            template
            .Template('{% load fantasy_tags %}{% crew_list_header finances %}')
            .render(template.Context({'finances': finances}))
        )


    @staticmethod
    def crew_list_row(
        seat: models.Seat,
        purchase: models.Purchase | None,
        show_actions: bool = True,
    ) -> str:
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
    def crew_list_box(
        crew_list: Iterable[models.Purchase],
        seats: db.QuerySet[models.Seat],
        finances: types.GenderFinances = {'budget': 0, 'crew_value': 0, 'balance': 0},
        show_actions: bool = False,
    ) -> str:
        """A helper function that renders a crew list."""
        component_string = '<div>{% crew_list_box crew_list seats finances show_actions %}</div>'
        return (
            template
            .Template('{% load fantasy_tags %}' + component_string)
            .render(template.Context({
                'crew_list': crew_list,
                'seats': seats,
                'finances': finances,
                'show_actions': show_actions,
            }))
        )


    def test__sell_button__standard(self) -> None:
        """Renders a styled button with associated data."""

        html = self.sell_button(self.purchase)
        button = parser(html)

        self.assertEqual(button.tag, 'button')

        classes = button.get('class', '').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-sell', classes)

        self.assertEqual(button.get('data-purchase'), str(self.purchase.id))

        self.assertInHTML('Sell ' + tags.currency(self.crew.value(self.day)), html)


    def test__sell_button__preset_price(self) -> None:
        """Uses the preset purchase.price attribute if available."""

        self.purchase.price = 999
        html = self.sell_button(self.purchase)
        button = parser(html)

        self.assertEqual(button.tag, 'button')

        classes = button.get('class', '').split()
        self.assertIn('btn', classes)
        self.assertIn('btn-sm', classes)
        self.assertIn('btn-sell', classes)

        self.assertEqual(button.get('data-purchase'), str(self.purchase.id))

        self.assertInHTML('Sell ' + tags.currency(999), html)


    def test__sell_button__query_count__standard(self) -> None:
        """Expect:
            (1) Purchased crew's position
            (1) Event details (for total number of crews)
        """

        with self.assertNumQueries(2):
            self.sell_button(self.purchase)


    def test__sell_button__preset_price__query_count(self) -> None:
        """Expect:
            No queries
        """

        self.purchase.price = 999
        with self.assertNumQueries(0):
            self.sell_button(self.purchase)


    def test__crew_list_row__no_purchase(self) -> None:
        """Renders a styled div, that contains an avatar."""

        html = self.crew_list_row(self.seat, None)

        # Test root
        row = parser(html)
        self.assertEqual(row.tag, 'div')
        self.assertIn('crew-row', row.get('class', '').split())

        # Test containments
        avatar = tags.avatar(self.seat.short)
        self.assertInHTML(avatar, html)

        self.assertNotIn('<div class="flex-grow-1">', html)
        self.assertNotIn('btn', html)


    def test__crew_list_row__with_purchase(self) -> None:
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
        self.assertIn('crew-row', row.get('class', '').split())

        # Test containments
        avatar = tags.avatar(self.seat.short, self.crew.club)
        self.assertInHTML(avatar, html)

        crew = '<div class="flex-grow-1"><div>{}</div></div>'.format(self.crew)
        self.assertInHTML(crew, html)

        sell_button = self.sell_button(purchase)
        self.assertInHTML(sell_button, html)


    def test__crew_list_row__with_athlete(self) -> None:
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
        self.assertIn('crew-row', row.get('class', '').split())

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


    def test__crew_list_row__show_actions_false(self) -> None:
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
        self.assertIn('crew-row', row.get('class', '').split())

        # Test containments
        avatar = tags.avatar(self.seat.short, self.crew.club)
        self.assertInHTML(avatar, html)

        crew = '<div class="flex-grow-1"><div>{}</div></div>'.format(self.crew)
        self.assertInHTML(crew, html)

        self.assertNotIn('btn', html)


    def test__crew_list_box__empty_list(self) -> None:
        """Renders a styled div that always has all seats."""

        html = self.crew_list_box([], self.seats)

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


    def test__crew_list_box__with_purchase(self) -> None:
        """Renders a styled div that includes any purchases provided."""

        purchase = self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        html = self.crew_list_box([purchase], self.seats)

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


    def test__crew_list_box__finances(self) -> None:
        """Includes financial information if provided."""

        finances: types.GenderFinances = {'budget': 1079, 'crew_value': 856, 'balance': 223}
        html = self.crew_list_box([], self.seats, finances)

        # Test containments
        self.assertInHTML(self.crew_list_header(finances), html)



    def test__crew_list_box__show_actions(self) -> None:
        """Propagates the show_actions flag."""

        purchase = self.team.purchases.create(day = self.day, seat = self.seat, crew = self.crew)
        html = self.crew_list_box([purchase], self.seats, show_actions = True)

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



class Test__Event_Box(TestCase):
    fixtures = ['dev_event']

    event: types.AugmentedEvent

    @classmethod
    def setUpTestData(cls) -> None:

        crews_ready = {'mens_crew_ready': db.Value(False), 'womens_crew_ready': db.Value(False)}
        cls.event = exists(models.Event.objects.annotate(**crews_ready).first())
        cls.event.days.create(
            name = 'Day One',
            date = timezone.now().date(),
            first_race_time = time(12, 00),
            last_race_time = time(hour = 18, minute = 30),
        )
        cls.event.days.create(
            name = 'Day Two',
            date = timezone.now().date() + timedelta(1),
            first_race_time = time(12, 00),
            last_race_time = time(hour = 18, minute = 30),
        )
        cls.event.days.create(name = 'Finish', date = timezone.now().date() + timedelta(2))

    @staticmethod
    def crew_ready_button(event: types.AugmentedEvent, gender: Genders) -> str:
        """A helper function that renders a crew row."""
        return (
            template
            .Template('{% load fantasy_tags %}{% crew_ready_button event gender %}')
            .render(template.Context({'event': event, 'gender': gender}))
        )


    def test__crew_ready_button__no_crew_valid_flags(self) -> None:
        """Renders a standard button that directs the user to the sign in page."""

        # Remove crew-ready flags
        del self.event.mens_crew_ready
        del self.event.womens_crew_ready

        # Generate button
        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(button.get('href'), reverse('login'))
        self.assertIn('btn-primary', button.get('class', '').split())

        # Test containment
        self.assertInHTML('Sign in to compete', html)


    def test__crew_ready_button__no_crew_valid_flags_after_racing(self) -> None:
        """Renders a standard button that directs the user to the sign in page."""

        # Remove crew-ready flags
        del self.event.mens_crew_ready
        del self.event.womens_crew_ready

        # Generate button
        self.event.days.update(date = db.F('date') - timedelta(2))
        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(button.get('href'), reverse('login'))
        self.assertIn('btn-primary', button.get('class', '').split())

        # Test containment
        self.assertInHTML('Sign in for your team', html)


    def test__crew_ready_button__crew_ready(self) -> None:
        """Renders a success message & button that directs the user to the correct market page."""

        # Generate button
        self.event.mens_crew_ready = True
        self.event.womens_crew_ready = True
        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(
            button.get('href'),
            reverse('fantasy:women', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertIn('btn-success', button.get('class', '').split())

        # Test containment
        self.assertInHTML('Ready to race', html)


    def test__crew_ready_button__crew_not_ready_day_one(self) -> None:
        """Renders a danger message & button that directs the user to the correct market page."""

        # Generate button
        self.event.mens_crew_ready = True
        self.event.womens_crew_ready = False
        date_shift = timezone.localtime().date() - self.event.first_day.date + timedelta(days = 1)
        self.event.days.update(date = db.F('date') + date_shift)
        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(
            button.get('href'),
            reverse('fantasy:women', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertIn('btn-danger', button.get('class', '').split())

        # Test containment
        self.assertInHTML('Entry incomplete', html)


    @patching.localtime_time(time(18, 30), timedelta(minutes = -1))
    def test__crew_ready_button__crew_not_ready_day_two(self, timezone_mock: Mock) -> None:
        """Renders a danger message & button that directs the user to the correct market page.

        Test is possibly fragile and time-dependent, due to changing market status.
        """

        # Generate button
        self.event.mens_crew_ready = True
        self.event.womens_crew_ready = False

        date_shift = timezone.localtime().date() - self.event.first_day.date - timedelta(1)
        self.event.days.update(date = db.F('date') + date_shift)

        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(
            button.get('href'),
            reverse('fantasy:women', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertIn('btn-danger', button.get('class', '').split())

        # Test containment
        self.assertInHTML('Subs required', html)


    def test__crew_ready_button__event_finished(self) -> None:
        """Renders a standard button that directs the user to the correct market page."""

        # Generate button
        self.event.days.update(date = db.F('date') - timedelta(2))
        self.event.mens_crew_ready = True
        self.event.womens_crew_ready = False
        html = self.crew_ready_button(self.event, Genders.WOMEN)

        # Test root
        button = parser(html)
        self.assertEqual(button.tag, 'a')
        self.assertEqual(
            button.get('href'),
            reverse('fantasy:women', kwargs = {'event_tag': self.event.tag}),
        )
        self.assertIn('btn-primary', button.get('class', '').split())

        # Test containment
        self.assertInHTML('View final crew', html)

