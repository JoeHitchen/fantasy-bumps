from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, patch
import zoneinfo

from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError, models as db
from django.contrib.auth import models as auth

from core.settings import TIME_ZONE
from core.tests import exists

from .constants import Series, Genders, GENDERS_OVERALL, money, Clubs
from . import models
from . import patching
from . import utils


class Test__Event(TestCase):
    fixtures = ['dev_event']

    event: models.Event
    yesterday: models.Day
    today: models.Day
    tomorrow: models.Day
    future: models.Day

    ROLLOVER_TIME = time(19, 45)

    @classmethod
    def setUpTestData(cls) -> None:

        cls.event = exists(models.Event.objects.first())

        # Prepare days
        cls.yesterday = cls.event.days.create(
            name = 'Yesterday',
            date = timezone.localtime().date() - timedelta(1),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )
        cls.today = cls.event.days.create(
            name = 'Today',
            date = timezone.localtime().date(),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )
        cls.tomorrow = models.Day(
            event = cls.event,
            name = 'Tomorrow',
            date = timezone.localtime().date() + timedelta(1),
            first_race_time = time(12, 00),
            last_race_time = time(18, 45),
        )  # Saved per-test due to isolation conflict
        cls.future = models.Day(
            event = cls.event,
            name = 'Future',
            date = timezone.localtime().date() + timedelta(2),
        )  # Saved per-test due to isolation conflict


    def setUp(self) -> None:

        # Save future days for delete-safe test isolation
        self.tomorrow.save()
        self.future.save()

        # Clear event cache
        self.event.active_day
        del self.event.active_day


    def test__string(self) -> None:
        """Returns an event's name as its string representation."""

        self.assertEqual(str(self.event), 'Demo 2019')


    def test__first_day__standard(self) -> None:
        """Returns the first day associated with the event."""
        self.assertEqual(self.event.first_day, self.yesterday)


    def test__first_day__prefetched(self) -> None:
        """Returns the first day associated with the event from a prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(self.event.first_day, self.yesterday)


    def test__first_day__query_count(self) -> None:
        """Expect:
            (1) SELECT first day
        """
        with self.assertNumQueries(1):
            self.event.first_day


    def test__first_day__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            self.event.first_day


    def test__last_racing_day__standard(self) -> None:
        """Returns the last day of racing for the event."""
        self.assertEqual(self.event.last_racing_day, self.tomorrow)  # Future does not have races


    def test__last_racing_day__prefetched(self) -> None:
        """Returns the last day of racing for the event from a prefetched set of days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(self.event.last_racing_day, self.tomorrow)  # Future does not have races


    def test__last_racing_day__query_count(self) -> None:
        """Expect:
            (1) SELECT last day with a race time
        """

        with self.assertNumQueries(1):
            self.event.last_racing_day


    def test__last_racing_day__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            self.event.last_racing_day


    @patching.localtime_time(ROLLOVER_TIME, timedelta(minutes = -1))
    def test__active_day__before_rollover__standard(self, _: Mock) -> None:
        """Before rollover, returns first day from today onwards."""

        self.assertEqual(
            self.event.active_day,
            self.today,
        )


    @patching.localtime_time(ROLLOVER_TIME, timedelta(minutes = -1))
    def test__active_day__before_rollover__prefetched(self, _: Mock) -> None:
        """Before rollover, returns first day from today onwards from the prefetched days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(
            self.event.active_day,
            self.today,
        )


    @patching.localtime_time(ROLLOVER_TIME, timedelta(minutes = -1))
    def test__active_day__before_rollover__query_count(self, _: Mock) -> None:
        """Expect:
            (1) SELECT all days from today onwards
        """

        with self.assertNumQueries(1):
            self.event.active_day


    @patching.localtime_time(ROLLOVER_TIME, timedelta(minutes = -1))
    def test__active_day__before_rollover__prefetched_query_count(self, _: Mock) -> None:
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            self.event.active_day


    @patching.localtime_time(ROLLOVER_TIME)
    def test__active_day__after_rollover__standard(self, _: Mock) -> None:
        """After rollover, returns first day from tomorrow onwards."""

        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )


    @patching.localtime_time(ROLLOVER_TIME)
    def test__active_day__after_rollover__prefetched(self, _: Mock) -> None:
        """After rollover, returns first day from tomorrow onwards from the prefetched days."""
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(
            self.event.active_day,
            self.tomorrow,
        )


    @patching.localtime_time(ROLLOVER_TIME)
    def test__active_day__after_rollover__query_count(self, _: Mock) -> None:
        """Expect:
            (1) SELECT all days from today onwards
        """

        with self.assertNumQueries(1):
            self.event.active_day


    @patching.localtime_time(ROLLOVER_TIME)
    def test__active_day__after_rollover__prefetched_query_count(self, _: Mock) -> None:
        """Expect:
            No queries
        """
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            self.event.active_day


    def test__active_day__after_event__standard(self) -> None:
        """Returns last day of the event, if all have passed."""

        models.Day.objects.update(date = db.F('date') - timedelta(5))

        self.assertEqual(
            self.event.active_day,
            self.future,
        )


    def test__active_day__after_event__prefetched(self) -> None:
        """Returns last day of the event from a prefetched set of days, if all have passed."""

        models.Day.objects.update(date = db.F('date') - timedelta(5))
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(
            self.event.active_day,
            self.future,
        )


    def test__active_day__after_event__query_count(self) -> None:
        """Expect:
            (1) SELECT any days after today/tomorrow (depending on time)
            (1) SELECT the last day of the event
        """

        models.Day.objects.update(date = db.F('date') - timedelta(5))

        with self.assertNumQueries(2):
            self.event.active_day


    def test__active_day__after_event__prefetched_query_count(self) -> None:
        """Returns last day of the event from a prefetched set of days, if all have passed."""

        models.Day.objects.update(date = db.F('date') - timedelta(5))
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            self.event.active_day


    def test__num_crews__mens(self) -> None:
        """Adds up all the men's division sizes."""

        self.event.mens_division_sizes = [8, 9, 10, 11, 12, 13, 14]

        self.assertEqual(self.event.num_crews(Genders.MEN), 77)


    def test__num_crews__womens(self) -> None:
        """Adds up all the women's division sizes."""

        self.event.womens_division_sizes = [9, 10, 11, 12, 13]

        self.assertEqual(self.event.num_crews(Genders.WOMEN), 55)


    def test__num_crews__query_count(self) -> None:
        """NONE EXPECTED (but an important part of the crew valuation chain)"""

        with self.assertNumQueries(0):
            self.event.num_crews(Genders.WOMEN)



class Test__Day__Core(TestCase):
    fixtures = ['dev_event']

    event: models.Event
    today: date

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())
        cls.today = timezone.localtime().date()


    def test__string(self) -> None:
        """Returns a day's name as it's string representation."""

        day = self.event.days.create(
            name = 'Racing',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        day_str = str(day)
        self.assertEqual(day_str, day.name)


    def test__next__past_only__standard(self) -> None:
        """Returns None if there are no days in the future."""

        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertIsNone(curr.next)


    def test__next__past_only__prefetched(self) -> None:
        """Returns None if there are no days in the future, using a prefetched set of days."""

        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertIsNone(curr.next)


    def test__next__past_only__query_count(self) -> None:
        """Expect:
            (1) SELECT the next day in the event
        """

        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        with self.assertNumQueries(1):
            curr.next


    def test__next__past_only__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """

        self.event.days.create(
            name = 'Prev',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            curr.next


    def test__next__future__standard(self) -> None:
        """Returns the next day in the series if there are days in the future."""

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        future_1 = self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertEqual(curr.next, future_1)


    def test__next__future__prefetched(self) -> None:
        """Returns the next day if there are days in the future, from a prefetched set of days."""

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        future_1 = self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(curr.next, future_1)


    def test__next__future__query_count(self) -> None:
        """Expect:
            (1) SELECT the next day in the event
        """

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        with self.assertNumQueries(1):
            curr.next


    def test__next__future__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """

        curr = self.event.days.create(
            name = 'Next',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 1',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Future 2',
            date = self.today + timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            curr.next


    def test__prev__past__standard(self) -> None:
        """Returns the previous day in the series if there are days in the past."""

        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        prev_1 = self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertEqual(curr.prev, prev_1)


    def test__prev__past__prefetched(self) -> None:
        """Returns the previous day if there are days in the past from a prefetched set of days."""

        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        prev_1 = self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertEqual(curr.prev, prev_1)


    def test__prev__past__query_count(self) -> None:
        """Expect:
            (1) SELECT the previous day in the event
        """

        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        with self.assertNumQueries(1):
            curr.prev


    def test__prev__past__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """

        self.event.days.create(
            name = 'Prev 2',
            date = self.today - timedelta(2),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Prev 1',
            date = self.today - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            curr.prev


    def test__prev__future_only__standard(self) -> None:
        """Returns None if there are no days in the past."""

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertIsNone(curr.prev)


    def test__prev__future_only__prefetched(self) -> None:
        """Returns None if there are no days in the past."""

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        self.assertIsNone(curr.prev)


    def test__prev__future_only__query_count(self) -> None:
        """Expect:
            (1) SELECT the previous day in the event
        """

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        with self.assertNumQueries(1):
            curr.prev


    def test__prev__future_only__prefetched_query_count(self) -> None:
        """Expect:
            No queries
        """

        curr = self.event.days.create(
            name = 'Curr',
            date = self.today,
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.event.days.create(
            name = 'Next',
            date = self.today + timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )
        db.prefetch_related_objects([self.event], db.Prefetch('days', to_attr = '_days'))

        with self.assertNumQueries(0):
            curr.prev


    def test__first_race__winter(self) -> None:
        """Constructs a datetime object from the date, first race time, and system timezone."""

        race_date = date.fromisoformat('2021-01-05')
        race_time = time(11, 30)
        first_race = self.event.days.create(
            date = race_date,
            first_race_time = race_time,
            last_race_time = time(hour = 18, minute = 30),
        ).first_race

        assert first_race  # Needed for MyPy
        self.assertIsInstance(first_race, datetime)
        self.assertEqual(first_race.date(), race_date)
        self.assertEqual(first_race.time(), race_time)
        self.assertEqual(first_race.tzname(), 'GMT')


    def test__first_race__summer(self) -> None:
        """Constructs a datetime object from the date, first race time, and system timezone."""

        race_date = date.fromisoformat('2021-07-05')
        race_time = time(11, 30)
        first_race = self.event.days.create(
            date = race_date,
            first_race_time = race_time,
            last_race_time = time(hour = 18, minute = 30),
        ).first_race

        assert first_race  # Needed for MyPy
        self.assertIsInstance(first_race, datetime)
        self.assertEqual(first_race.date(), race_date)
        self.assertEqual(first_race.time(), race_time)
        self.assertEqual(first_race.tzname(), 'BST')


    def test__last_race__winter(self) -> None:
        """Constructs a datetime object from the date, last race time, and system timezone."""

        race_date = date.fromisoformat('2021-01-05')
        race_time = time(18, 45)
        last_race = self.event.days.create(
            date = race_date,
            first_race_time = time(hour = 12),
            last_race_time = race_time,
        ).last_race

        assert last_race  # Needed for MyPy
        self.assertIsInstance(last_race, datetime)
        self.assertEqual(last_race.date(), race_date)
        self.assertEqual(last_race.time(), race_time)
        self.assertEqual(last_race.tzname(), 'GMT')


    def test__last_race__summer(self) -> None:
        """Constructs a datetime object from the date, last race time, and system timezone."""

        race_date = date.fromisoformat('2021-07-05')
        race_time = time(18, 45)
        last_race = self.event.days.create(
            date = race_date,
            first_race_time = time(hour = 12),
            last_race_time = race_time,
        ).last_race

        assert last_race  # Needed for MyPy
        self.assertIsInstance(last_race, datetime)
        self.assertEqual(last_race.date(), race_date)
        self.assertEqual(last_race.time(), race_time)
        self.assertEqual(last_race.tzname(), 'BST')



class Test__Day__Start_Orders(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1']

    event: models.Event
    day: models.Day

    @classmethod
    def setUpTestData(cls) -> None:

        cls.event = exists(models.Event.objects.first())
        cls.event.mens_division_sizes = [2, 3]
        cls.event.womens_division_sizes = [2, 2, 3]
        cls.event.save()

        cls.day = exists(cls.event.days.first())


    def test__divisions__mens(self) -> None:
        """Has the division structure as described by the event."""

        # Get divisions
        divisions = self.day.divisions(Genders.MEN)

        # Test division structure
        self.assertEqual(len(divisions), 2)

        div1 = divisions[0]
        self.assertEqual(div1.top_bungline, 1)
        self.assertEqual(div1.bottom_bungline, 2)

        div2 = divisions[1]
        self.assertEqual(div2.top_bungline, 3)
        self.assertEqual(div2.bottom_bungline, 5)


    def test__divisions__womens(self) -> None:
        """Has the division structure as described by the event."""

        # Get divisions
        divisions = self.day.divisions(Genders.WOMEN)

        # Test division structure
        self.assertEqual(len(divisions), 3)

        div1 = divisions[0]
        self.assertEqual(div1.top_bungline, 1)
        self.assertEqual(div1.bottom_bungline, 2)

        div2 = divisions[1]
        self.assertEqual(div2.top_bungline, 3)
        self.assertEqual(div2.bottom_bungline, 4)

        div3 = divisions[2]
        self.assertEqual(div3.top_bungline, 5)
        self.assertEqual(div3.bottom_bungline, 7)


    @patch.object(models.Day, 'divisions', autospec = True)
    def test__start_order__mens(self, divisions_mock: Mock) -> None:
        """Passes the gender argument onto the divisions method."""

        # Get start orders
        self.day.start_order(Genders.MEN)
        divisions_mock.assert_called_once_with(Genders.MEN)


    @patch.object(models.Day, 'divisions', autospec = True)
    def test__start_order__womens(self, divisions_mock: Mock) -> None:
        """Passes the gender argument onto the divisions method."""

        # Get start orders
        self.day.start_order(Genders.WOMEN)
        divisions_mock.assert_called_once_with(Genders.WOMEN)


    @patch(
        'fantasy.models.Division.start_order',
        autospec = True,
        side_effect = lambda self: self,
    )
    def test__start_order__behaviour(self, start_order_mock: Mock) -> None:
        """Iteratively calls `start_order` on each division.

        A mocked Division.start_order returns the division instance it is called on.
        """

        # Get start orders
        day_divisions = self.day.divisions(Genders.WOMEN)
        day_start_order = self.day.start_order(Genders.WOMEN)

        self.assertEqual(start_order_mock.call_count, 3)
        for index, call in enumerate(start_order_mock.call_args_list):
            with self.subTest(call_index = index):
                self.assertEqual(call, ((day_divisions[index],),))

        self.assertEqual(day_start_order, day_divisions)



class Test__Day__Market_Status(TestCase):
    fixtures = ['dev_event']

    event: models.Event

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())


    def test__market_opens__non_race_day(self) -> None:
        """Market opening time is undefined if no racing is scheduled."""

        race_date = date.fromisoformat('2021-07-05')
        day = self.event.days.create(
            name = 'Main',
            date = race_date,
            first_race_time = None,
            last_race_time = None,
        )

        self.assertIsNone(day.market_opens)


    def test__market_opens__first_race_day__winter(self) -> None:
        """The first day's markets opening is taken from the event property."""

        self.event.initial_market_open = datetime.combine(
            date.fromisoformat('2021-01-02'),
            time.fromisoformat('20:00:00'),
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        )
        self.event.save()

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )

        assert day.market_opens
        self.assertEqual(day.market_opens, self.event.initial_market_open)


    def test__market_opens__first_race_day__summer(self) -> None:
        """The first day's markets opening is taken from the event property."""

        self.event.initial_market_open = datetime.combine(
            date.fromisoformat('2021-07-02'),
            time.fromisoformat('20:00:00'),
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        )
        self.event.save()

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )

        assert day.market_opens
        self.assertEqual(day.market_opens, self.event.initial_market_open)


    def test__market_opens__later_race_day__winter(self) -> None:
        """Later day markets open after racing the previous day."""

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        prev = self.event.days.create(
            name = 'Prior',
            date = day.date - timedelta(2),  # Demonstrates linked to previous day, not yesterday
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('17:45:00'),
        )

        assert day.market_opens
        self.assertEqual(day.market_opens.date(), prev.date)
        self.assertEqual(day.market_opens.time(), time.fromisoformat('18:45:00'))
        self.assertEqual(day.market_opens.tzname(), 'GMT')


    def test__market_opens__later_race_day__summer(self) -> None:
        """Later day markets open after racing the previous day."""

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )
        prev = self.event.days.create(
            name = 'Prior',
            date = day.date - timedelta(2),  # Demonstrates linked to previous day, not yesterday
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('17:45:00'),
        )

        assert day.market_opens
        self.assertEqual(day.market_opens.date(), prev.date)
        self.assertEqual(day.market_opens.time(), time.fromisoformat('18:45:00'))
        self.assertEqual(day.market_opens.tzname(), 'BST')


    def test__market_closes__without_race(self) -> None:
        """Market closing time is undefined if no racing is scheduled."""

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = None,
            last_race_time = None,
        )

        self.assertIsNone(day.market_closes)


    def test__market_closes__with_winter_race(self) -> None:
        """Markets close half an hour before the first race."""

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-01-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )

        assert day.market_closes
        self.assertEqual(day.market_closes.date(), day.date)
        self.assertEqual(day.market_closes.time().isoformat(), '11:30:00')
        self.assertEqual(day.market_closes.tzname(), 'GMT')


    def test__market_closes__with_summer_race(self) -> None:
        """Markets close half an hour before the first race."""

        day = self.event.days.create(
            name = 'Main',
            date = date.fromisoformat('2021-07-05'),
            first_race_time = time.fromisoformat('12:00:00'),
            last_race_time = time.fromisoformat('18:30:00'),
        )

        assert day.market_closes
        self.assertEqual(day.market_closes.date(), day.date)
        self.assertEqual(day.market_closes.time().isoformat(), '11:30:00')
        self.assertEqual(day.market_closes.tzname(), 'BST')


    @patching.market_opens(timezone.localtime() + timedelta(minutes = 5))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__before_open(self, _: Mock, __: Mock) -> None:
        """Returns False if before opening time."""

        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertFalse(day.market_is_open)


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__between(self, _: Mock, __: Mock) -> None:
        """Returns True if between opening time and closing time."""

        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertTrue(day.market_is_open)


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() - timedelta(minutes = 5))
    def test__market_is_open__after_close(self, _: Mock, __: Mock) -> None:
        """Returns False if after closing time."""

        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertFalse(day.market_is_open)


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__held_closed(self, _: Mock, __: Mock) -> None:
        """Returns False if the event has markets held closed."""

        self.event.market_held_closed = True
        self.event.save()

        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertFalse(day.market_is_open)


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__previous_day_not_advanced(self, _: Mock, __: Mock) -> None:
        """Previous days which have not advanced will hold the market closed."""

        self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date() - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
            advanced = False,
        )
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertFalse(day.market_is_open)


    @patching.market_opens(timezone.localtime() - timedelta(minutes = 10))
    @patching.market_closes(timezone.localtime() + timedelta(minutes = 10))
    def test__market_is_open__previous_day_advanced(self, _: Mock, __: Mock) -> None:
        """Previous days which have advanced do not hold the markets closed."""

        self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date() - timedelta(1),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
            advanced = True,
        )
        day = self.event.days.create(
            name = 'Markets',
            date = timezone.localtime().date(),
            first_race_time = time(hour = 12),
            last_race_time = time(hour = 18, minute = 30),
        )

        self.assertTrue(day.market_is_open)



class Test__Division(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'dev_start_day1']

    day: models.Day

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())

    def test__start_order__full(self) -> None:
        """Generates a list of crews for the division with bungline numbers."""

        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = Genders.WOMEN,
            number = 2,
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order()

        self.assertEqual(start_order.count(), 6)

        # Iterate over start order objects
        for idx, position in enumerate(start_order):
            with self.subTest(idx = idx):

                # Test individual bungline
                self.assertEqual(position.bungline, idx + 1)
                self.assertEqual(position.crew.gender, Genders.WOMEN)
                self.assertTrue(position.rank >= 3)
                self.assertTrue(position.rank <= 8)


    def test__start_order__partial(self) -> None:
        """Safely excludes missing bunglines from the returned data."""

        # Leave position 7 (Bungline 5) empty
        models.Position.objects.filter(crew__gender = Genders.WOMEN, rank = 7).delete()

        # Generate start order
        start_order = models.Division(
            day = self.day,
            gender = Genders.WOMEN,
            number = 2,
            top_bungline = 3,
            bottom_bungline = 8,
        ).start_order()

        # Check for missing bungline
        self.assertEqual(start_order.count(), 5)
        bunglines = start_order.values_list('bungline', flat = True)
        self.assertNotIn(5, bunglines)



class Test__Crew(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews']

    day1: models.Day
    crew_top: models.Crew
    crew_middle: models.Crew
    crew_bottom: models.Crew
    crew_unranked: models.Crew

    @classmethod
    def setUpTestData(cls) -> None:
        event = exists(models.Event.objects.first())
        event.womens_division_sizes = [3]

        days = event.days.all()
        cls.day1 = days[0]

        crews = models.Crew.objects.filter(gender = Genders.WOMEN)

        cls.crew_top = crews[0]
        cls.crew_top.positions.create(day = cls.day1, rank = 1)

        cls.crew_middle = crews[1]
        cls.crew_middle.positions.create(day = cls.day1, rank = 2)

        cls.crew_bottom = crews[2]
        cls.crew_bottom.positions.create(day = cls.day1, rank = 3)

        cls.crew_unranked = crews[3]

        crew_mens = exists(models.Crew.objects.filter(gender = Genders.MEN).first())
        crew_mens.positions.create(day = cls.day1, rank = 4)  # Added to ensure gender isolation


    def test__string__womens_first(self) -> None:
        """Displays a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College W1')


    def test__string__mens_first(self) -> None:
        """Displays a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.MEN,
            rank = 1,
        )
        self.assertEqual(str(crew), 'New College M1')


    def test__string__lower_boat(self) -> None:
        """Displays a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 2,
        )
        self.assertEqual(str(crew), 'New College W2')


    def test__tuple__womens_first(self) -> None:
        """Contains a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 1,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.WOMEN, 1))

        self.assertEqual(
            models.Crew.make_tuple(Clubs.NEWC.value, Genders.MEN, 1),
            (Clubs.NEWC, Genders.MEN, 1),
        )


    def test__tuple__mens_first(self) -> None:
        """Contains a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.MEN,
            rank = 1,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.MEN, 1))

        self.assertEqual(
            models.Crew.make_tuple(Clubs.NEWC.value, Genders.WOMEN, 1),
            (Clubs.NEWC, Genders.WOMEN, 1),
        )


    def test__tuple__lower_boat(self) -> None:
        """Contains a crew's club, gender, and rank."""

        crew = models.Crew(
            club = Clubs.NEWC,
            gender = Genders.WOMEN,
            rank = 2,
        )
        self.assertEqual(crew.as_tuple(), (Clubs.NEWC, Genders.WOMEN, 2))

        self.assertEqual(
            models.Crew.make_tuple(Clubs.NEWC.value, Genders.WOMEN, 2),
            (Clubs.NEWC, Genders.WOMEN, 2),
        )


    def test__value__no_ranking(self) -> None:
        """Returns zero if the crew has no position for that day."""
        self.assertEqual(self.crew_unranked.value(self.day1), 0)


    def test__value__top_crew(self) -> None:
        """Returns the maximum price."""
        self.assertEqual(self.crew_top.value(self.day1), money.PRICE_MAX)


    def test__value__bottom_crew(self) -> None:
        """Returns the minimum price."""
        self.assertEqual(self.crew_bottom.value(self.day1), money.PRICE_MIN)


    def test__value__middle_crew(self) -> None:
        """Returns the price from the pricing algorithm."""
        self.assertEqual(self.crew_middle.value(self.day1), utils.pricing(2, 3))


    def test__value__query_count(self) -> None:
        """Expect:
            (1) SELECT crew's position
        """

        with self.assertNumQueries(1):
            self.crew_top.value(self.day1)



class Test__Position(TestCase):
    fixtures = ['dev_event', 'dev_days']

    day: models.Day
    crew: models.Crew

    @classmethod
    def setUpTestData(cls) -> None:
        cls.day = exists(models.Day.objects.first())
        cls.crew = models.Crew(club = Clubs.HERT, gender = Genders.WOMEN, rank = 1)
        cls.crew.save()


    def test__unique_pair(self) -> None:
        """Raises a DB IntegrityError if a duplicate day/crew pairing created."""

        self.day.ranking.create(crew = self.crew, rank = 1)

        with self.assertRaises(IntegrityError):
            self.day.ranking.create(crew = self.crew, rank = 2)



class Test__Seat(TestCase):

    def test__short__empty(self) -> None:
        """Raises expected error when Seat.name empty."""

        seat = models.Seat(name = '')

        with self.assertRaises(IndexError):
            seat.short


    def test__short__one_char(self) -> None:
        """Gives first character of Seat.name."""

        seat = models.Seat(name = 'S')
        self.assertEqual(seat.short, 'S')


    def test__short__multi_char(self) -> None:
        """Gives first character of Seat.name."""

        seat = models.Seat(name = 'Seat')
        self.assertEqual(seat.short, 'S')


    def test__string(self) -> None:
        """Returns a seat's name as it's string representation."""

        seat = models.Seat(name = 'Name')
        self.assertEqual(str(seat), 'Name')



class Test__Athlete(TestCase):
    fixtures = ['dev_event', 'dev_crews', 'seats']

    event: models.Event
    crew: models.Crew
    seat: models.Seat

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())
        cls.crew = exists(models.Crew.objects.first())
        cls.seat = exists(models.Seat.objects.first())


    def test__string(self) -> None:
        """Returns a athlete's name as their string representation."""

        athlete = models.Athlete(name = 'Test Athlete')
        athlete_str = str(athlete)
        self.assertEqual(athlete_str, athlete.name)


    def test__unique_pair(self) -> None:
        """Raises a DB IntegrityError if a duplicate event/crew/seat pairing created."""

        self.event.crew_lists.create(crew = self.crew, seat = self.seat, name = 'Test Athlete')

        with self.assertRaises(IntegrityError):
            self.event.crew_lists.create(
                crew = self.crew,
                seat = self.seat,
                name = 'Test Athlete',
            )



class Test__Team(TestCase):
    fixtures = ['dev_event', 'dev_days', 'seats', 'dev_team']

    team: models.Team
    day: models.Day
    crew: models.Crew
    bow: models.Seat

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.day = exists(models.Day.objects.first())

        cls.crew = models.Crew.objects.create(club = Clubs.NEWC, gender = Genders.WOMEN, rank = 1)
        cls.bow = models.Seat.objects.get(name = 'Bow')


    def test__auto_create(self) -> None:
        """Is auto created every time a User instance is created."""

        user = auth.User.objects.create_user('A User', '', '')
        self.assertTrue(hasattr(user, 'team'))


    def test__string(self) -> None:
        """Returns the related username as it's string representation."""

        user = auth.User.objects.create_user('A User', '', '')
        team = user.team

        self.assertEqual(str(team), 'A User')


    def test__get_crew__empty_crew(self) -> None:
        """Returns an empty crew list if no rowers have been purchased."""

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 0)


    def test__get_crew__other_team(self) -> None:
        """Does not include rowers purchased by another team."""

        other_team = auth.User.objects.create_user('Other').team

        other_team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 0)


    def test__get_crew__other_day(self) -> None:
        """Does not include rowers purchased on another day."""

        other_day = exists(models.Day.objects.last())
        self.assertNotEqual(other_day, self.day)

        self.team.purchases.create(
            day = other_day,
            crew = self.crew,
            seat = self.bow,
        )

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 0)


    def test__get_crew__wrong_gender(self) -> None:
        """Does not include purchases of the wrong gender."""

        self.team.purchases.create(
            day = self.day,
            crew = self.crew,  # Is a women's crew
            seat = self.bow,
        )

        crew = self.team.get_crew(self.day, Genders.MEN)
        self.assertEqual(crew.count(), 0)


    def test__get_crew__partial_team(self) -> None:
        """Returns any purchases matching the criteria."""

        self.team.purchases.create(
            day = self.day,
            crew = self.crew,
            seat = self.bow,
        )

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 1)


    def test__get_crew__full_team(self) -> None:
        """Returns any purchases matching the criteria."""

        for seat in models.Seat.objects.all():
            self.team.purchases.create(
                day = self.day,
                crew = self.crew,
                seat = seat,
            )

        crew = self.team.get_crew(self.day, Genders.WOMEN)
        self.assertEqual(crew.count(), 9)


class Test__Team__Trophies(TestCase):
    fixtures = ['dev_event', 'dev_team']

    team: models.Team
    event_1: models.Event
    event_2: models.Event
    event_3: models.Event

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = exists(models.Team.objects.first())
        cls.event_1 = models.Event.objects.create(
            series = Series.DEMO,
            year = 2023,
            tag = 'demo2023',
            initial_market_open = '2023-02-25T18:00:00Z',
        )
        cls.event_2 = models.Event.objects.create(
            series = Series.DEMO,
            year = 2024,
            tag = 'demo2024',
            initial_market_open = '2024-02-25T18:00:00Z',
        )
        cls.event_3 = models.Event.objects.create(
            series = Series.DEMO,
            year = 2025,
            tag = 'demo2025',
            initial_market_open = '2025-02-25T18:00:00Z',
        )


    def test__no_trophies(self) -> None:
        """An empty list should be returned if the player has not won any trophies."""

        self.assertEqual(self.team.get_leaderboard_trophies(), [])


    def test__one_per_event(self) -> None:
        """Only the most prestigious trophy from each event is shown."""

        trophy_1 = self.team.trophies.create(
            event = self.event_1,
            type = models.Trophy.Types.GOLDEN_SWAN,  # Out-ranks Golden Cob this event
        )
        self.team.trophies.create(event = self.event_1, type = models.Trophy.Types.GOLDEN_COB)

        trophy_2 = self.team.trophies.create(
            event = self.event_2,
            type = models.Trophy.Types.BRONZE_SWAN,  # Out-ranks Golden Pen this event
        )
        self.team.trophies.create(event = self.event_2, type = models.Trophy.Types.GOLDEN_PEN)

        self.team.trophies.create(event = self.event_3, type = models.Trophy.Types.GOLDEN_PEN)
        trophy_3 = self.team.trophies.create(
            event = self.event_3,
            type = models.Trophy.Types.SILVER_SWAN,  # Out-ranks Golden Pen from this event
        )

        self.assertEqual(self.team.get_leaderboard_trophies(), [trophy_1, trophy_3, trophy_2])



class Test__GameEntry(TestCase):
    fixtures = ['dev_event']

    event: models.Event
    team_1: models.Team
    team_2: models.Team
    team_3: models.Team
    team_4: models.Team
    game_entry_1: models.GameEntry
    game_entry_2: models.GameEntry
    game_entry_3: models.GameEntry
    game_entry_4: models.GameEntry

    @classmethod
    def setUpTestData(cls) -> None:
        cls.event = exists(models.Event.objects.first())

        cls.team_1 = auth.User.objects.create_user('One', '', '').team
        cls.team_2 = auth.User.objects.create_user('Two', '', '').team
        cls.team_3 = auth.User.objects.create_user('Three', '', '').team
        cls.team_4 = auth.User.objects.create_user('Four', '', '').team

        cls.game_entry_1 = cls.event.fantasies.create(
            team = cls.team_1,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 110,
            womens_balance = 103,
        )
        cls.game_entry_2 = cls.event.fantasies.create(
            team = cls.team_2,
            mens_budget = 754,
            womens_budget = 456,
            mens_balance = 120,
            womens_balance = 105,
        )
        cls.game_entry_3 = cls.event.fantasies.create(
            team = cls.team_3,
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 117,
            womens_balance = 112,
        )
        cls.game_entry_4 = cls.event.fantasies.create(
            team = cls.team_4,  # Alphabetically before but otherwise identical to 'Three'
            mens_budget = 701,
            womens_budget = 713,
            mens_balance = 117,
            womens_balance = 112,
        )


    def test__unique_group(self) -> None:
        """Raises a DB IntegrityError if a duplicate team/event group created."""

        with self.assertRaises(IntegrityError):
            self.event.fantasies.create(team = self.team_1)  # Already exists


    def test__query__extend_financials__total_budget(self) -> None:
        """Totals the gendered budgets."""

        entry = exists(models.GameEntry.objects.extend_financials().first())
        self.assertEqual(entry.total_budget, 701 + 713)


    def test__query__extend_financials__mens_crew(self) -> None:
        """Calculates the value of men's crews."""

        entry = exists(models.GameEntry.objects.extend_financials().first())
        self.assertEqual(entry.mens_crew_value, 701 - 110)


    def test__query__extend_financials__womens_crew(self) -> None:
        """Calculates the value of women's crews."""

        entry = exists(models.GameEntry.objects.extend_financials().first())
        self.assertEqual(entry.womens_crew_value, 713 - 103)


    def test__query__extend_financials__total_crew(self) -> None:
        """Calculates the value of both crews."""

        entry = exists(models.GameEntry.objects.extend_financials().first())
        self.assertEqual(entry.total_crew_value, 701 + 713 - 103 - 110)


    def test__query__rank_by__total(self) -> None:
        """Ranks teams by the total budget."""

        self.assertQuerySetEqual(
            self.event.fantasies.extend_financials().rank_by(GENDERS_OVERALL),
            [self.game_entry_1, self.game_entry_4, self.game_entry_3, self.game_entry_2],
        )


    def test__query__rank_by__mens(self) -> None:
        """Ranks teams by the men's budget."""

        self.assertQuerySetEqual(
            self.event.fantasies.extend_financials().rank_by(Genders.MEN),
            [self.game_entry_2, self.game_entry_1, self.game_entry_4, self.game_entry_3],
        )


    def test__query__rank_by__womens(self) -> None:
        """Ranks teams by the women's budget."""

        self.assertQuerySetEqual(
            self.event.fantasies.extend_financials().rank_by(Genders.WOMEN),
            [self.game_entry_1, self.game_entry_4, self.game_entry_3, self.game_entry_2],
        )



class Test__Purchase(TestCase):
    fixtures = ['dev_event', 'dev_days', 'dev_crews', 'seats', 'dev_team']

    def test__athlete_delete(self) -> None:
        """Athlete references should be nulled if the athlete is deleted.

        This is important for not dropping purchases when honouring an athlete deletion request.
        """

        # Create athlete
        day = exists(models.Day.objects.select_related('event').first())
        crew = exists(models.Crew.objects.first())
        seat = exists(models.Seat.objects.first())
        athlete = crew.crew_lists.create(event = day.event, seat = seat, name = 'Deletion')

        # Create purchase
        team = exists(models.Team.objects.first())
        purchase = team.purchases.create(day = day, crew = crew, seat = seat, athlete = athlete)

        # Delete athlete
        athlete.delete()
        with self.assertRaises(models.Athlete.DoesNotExist):
            athlete.refresh_from_db()  # Verify deletion completed
        purchase.refresh_from_db()
        self.assertIsNone(purchase.athlete)


class Test__Trophy(TestCase):
    fixtures = ['dev_event', 'dev_team']

    def test__string(self) -> None:
        """Returns the trophy type and event."""

        trophy = models.Trophy(
            event = exists(models.Event.objects.first()),
            team = exists(models.Team.objects.first()),
            type = models.Trophy.Types.GOLDEN_SWAN,
        )

        self.assertEqual(str(trophy), 'Golden Swan (Demo 2019)')

