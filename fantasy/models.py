from datetime import datetime, timedelta
from typing import TypedDict, TYPE_CHECKING
from dataclasses import dataclass
from functools import lru_cache
import zoneinfo

from django.db import models
from django.contrib.auth import models as auth
from django.utils import timezone
from django.utils.functional import cached_property
from django.dispatch import receiver

from core.settings import TIME_ZONE
from core.tests import exists

from .constants import Series, Genders, GENDERS_OVERALL, timings, money, Clubs
from .utils import pricing


if TYPE_CHECKING:
    from django_stubs_ext import WithAnnotations

    class BunglineAnnotation(TypedDict):
        bungline: int

    class FinancialAnnotation(TypedDict):
        total_budget: int
        total_balance: int
        total_crew_value: int
        mens_crew_value: int
        womens_crew_value: int

    StartOrderPosition = WithAnnotations['Position', BunglineAnnotation]
    FinancialGameEntry = WithAnnotations['GameEntry', FinancialAnnotation]

else:
    StartOrderPosition = 'Position'
    FinancialGameEntry = 'GameEntry'


class Event(models.Model):
    """A bumps competition, with simple division information."""

    series = models.CharField(
        max_length = 1,
        choices = Series.choices,
        db_index = True,
    )
    year = models.PositiveSmallIntegerField(db_index = True)
    tag = models.SlugField(max_length = 15, unique = True)  # Implicit db index

    mens_division_sizes = models.JSONField(default = list)
    womens_division_sizes = models.JSONField(default = list)

    market_held_closed = models.BooleanField(default = False)
    initial_market_open = models.DateTimeField()

    _days: list['Day']

    def __str__(self) -> str:
        series_long = {
            Series.EIGHTS.value: 'Summer Eights',
            Series.LENTS.value: 'Lent Bumps',
            Series.MAYS.value: 'May Bumps',
        }.get(self.series, self.get_series_display())
        return '{} {}'.format(series_long, self.year)


    @cached_property
    def first_day(self) -> 'Day':
        if hasattr(self, '_days'):
            return self._days[0]
        return exists(self.days.first())


    @cached_property
    def last_racing_day(self) -> 'Day':
        if hasattr(self, '_days'):
            return [day for day in self._days if day.is_racing_day][-1]
        return exists(self.days.exclude(first_race_time = None, last_race_time = None).last())


    @cached_property
    def active_day(self) -> 'Day':
        """The active/most currently relevant day of the event.

        Before markets open -> The first day from today onwards.
        After markets open -> The first day from tomorrow onwards.
        After the event -> Last day of the event.
        """

        now = timezone.localtime()

        if hasattr(self, '_days'):
            not_past_days = [day for day in self._days if day.date >= now.date()]
        else:
            not_past_days = list(self.days.filter(date__gte = now.date()))

        if not not_past_days:
            return self._days[-1] if hasattr(self, '_days') else exists(self.days.last())

        current_day = not_past_days[0]
        if (current_day.last_race and now >= current_day.last_race + timings.MARKET_DELAY
                and len(not_past_days) > 1):
            return not_past_days[1]

        return current_day


    def num_crews(self, gender: Genders) -> int:
        """The number of crews of the given gender competing in the event."""

        num_crews_map: dict[Genders, int] = {
            Genders.MEN: sum(self.mens_division_sizes),
            Genders.WOMEN: sum(self.womens_division_sizes),
        }
        return num_crews_map[gender]



class Day(models.Model):
    """A day of racing."""

    event = models.ForeignKey(Event, models.CASCADE, related_name = 'days')
    name = models.CharField(max_length = 10)
    date = models.DateField(db_index = True)
    first_race_time = models.TimeField(null = True, db_index = True)
    last_race_time = models.TimeField(null = True, db_index = True)

    advanced = models.BooleanField(default = False)

    mens_crew: models.QuerySet['Purchase']  # Needed for view event augmentation typing
    womens_crew: models.QuerySet['Purchase']  # Needed for view event augmentation typing

    class Meta:
        ordering = ['event', 'date']

    def __str__(self) -> str:
        return self.name

    @cached_property
    def next(self) -> 'Day | None':
        """The next day of the event."""
        if hasattr(self.event, '_days'):
            future_days = [day for day in self.event._days if day.date > self.date]
            return future_days[0] if future_days else None
        return self.event.days.filter(date__gt = self.date).first()


    @cached_property
    def prev(self) -> 'Day | None':
        """The previous day of the event."""
        if hasattr(self.event, '_days'):
            past_days = [day for day in self.event._days if day.date < self.date]
            return past_days[-1] if past_days else None
        return self.event.days.filter(date__lt = self.date).order_by('-date').first()


    @cached_property
    def is_racing_day(self) -> bool:
        """Indicates if racing occurs on this day."""
        return bool(self.first_race and self.last_race)


    @cached_property
    def first_race(self) -> datetime | None:
        """The datetime for the first race of the day, or None if not racing day."""

        if not self.first_race_time:
            return None

        return datetime.combine(
            self.date,
            self.first_race_time,
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        )

    @cached_property
    def last_race(self) -> datetime | None:
        """The datetime for the last race of the day, or None if not racing day."""

        if not self.last_race_time:
            return None

        return datetime.combine(
            self.date,
            self.last_race_time,
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        )


    @lru_cache(maxsize=2)
    def divisions(self, gender: Genders) -> list['Division']:
        """Generates the division structure for the day."""

        # Get correct division sizes
        division_sizes = {
            Genders.MEN: self.event.mens_division_sizes,
            Genders.WOMEN: self.event.womens_division_sizes,
        }[gender]

        # Generate division structure
        divisions = []
        prev_lowest_bungline = 0

        for division_number, division_size in enumerate(division_sizes):

            divisions.append(Division(
                day = self,
                gender = gender,
                number = division_number + 1,
                top_bungline = prev_lowest_bungline + 1,
                bottom_bungline = prev_lowest_bungline + division_size,
            ))

            prev_lowest_bungline = divisions[-1].bottom_bungline

        return divisions


    def start_order(self, gender: Genders) -> list[models.QuerySet[StartOrderPosition]]:
        """Builds the day and gender's start order from the start order of each division."""
        return [division.start_order() for division in self.divisions(gender)]


    @cached_property
    def market_opens(self) -> datetime | None:
        """Gives the time that markets open for trading, for racing days.

        Before racing, the markets open at 8pm, three days before the first racing day, and
        otherwise open one hour after the last race of the previous day."""

        if not self.is_racing_day:
            return None

        if self.prev and self.prev.last_race:
            return self.prev.last_race + timings.MARKET_DELAY

        return datetime.combine(
            self.date - timedelta(3),
            timings.MARKET_INITIAL,
            tzinfo = zoneinfo.ZoneInfo(TIME_ZONE),
        )


    @cached_property
    def market_closes(self) -> datetime | None:
        """Markets always close half an hour before the first race, if one occurs."""
        return self.first_race - timedelta(minutes = 30) if self.first_race else None


    @cached_property
    def market_is_open(self) -> bool:
        """Indicates whether the market is currently open for trading."""

        if not self.market_opens or not self.market_closes or self.event.market_held_closed:
            return False

        if self.prev and not self.prev.advanced:
            return False

        return self.market_opens <= timezone.localtime() < self.market_closes



@dataclass
class Division:
    """Temporary objects for storing division information and start orders."""

    day: Day
    gender: Genders
    number: int
    top_bungline: int
    bottom_bungline: int


    def start_order(self) -> models.QuerySet[StartOrderPosition]:
        """Generates start order and bungline numbers (excluding sandwich boat)."""

        return self.day.ranking.filter(
            crew__gender = self.gender,
            rank__gte = self.top_bungline,
            rank__lte = self.bottom_bungline,
        ).annotate(
            bungline = models.F('rank') - self.top_bungline + 1,
        ).order_by('rank').select_related('crew')



class Crew(models.Model):
    """Describes a crew (e.g. New College W1)"""
    Tuple = tuple[Clubs, Genders, int]

    club = models.CharField(
        max_length = 4,
        choices = Clubs.choices,
        db_index = True,
    )
    gender = models.CharField(
        max_length = 1,
        choices = Genders.choices,
        db_index = True,
    )
    rank = models.PositiveSmallIntegerField()

    posn_old: list['Position']  # List due to pre-fetch
    posn_new: list['Position']  # List due to pre-fetch

    def __str__(self) -> str:
        return '{} {}{}'.format(self.get_club_display(), self.gender, self.rank)


    @staticmethod
    def make_tuple(club: str, gender: str, rank: int) -> 'Crew.Tuple':
        return (Clubs(club), Genders(gender), rank)


    def as_tuple(self) -> 'Crew.Tuple':
        """Describes the crew in the tuple-form needed for parser interaction."""
        return self.make_tuple(self.club, self.gender, self.rank)


    def value(self, day: Day) -> int:
        """The price of the crew for a given day."""

        try:
            return pricing(
                self.positions.get(day = day).rank,
                day.event.num_crews(Genders(self.gender)),
            )
        except Position.DoesNotExist:
            return 0



class Position(models.Model):
    """A crew's position on the river for a given day."""

    day = models.ForeignKey(Day, models.CASCADE, related_name = 'ranking')
    crew = models.ForeignKey(Crew, models.PROTECT, related_name = 'positions')
    rank = models.PositiveSmallIntegerField(db_index = True)

    class Meta:
        ordering = ['day', 'rank']
        unique_together = ['day', 'crew']



class Seat(models.Model):
    """Describes a position within a boat."""

    name = models.CharField(max_length = 6)
    cox = models.BooleanField()

    @property
    def short(self) -> str:
        return self.name[0]

    def __str__(self) -> str:
        return self.name



class Athlete(models.Model):
    """Describes an athlete competing in a event."""

    event = models.ForeignKey(Event, models.PROTECT, related_name = 'crew_lists')
    crew = models.ForeignKey(Crew, models.PROTECT, related_name = 'crew_lists')
    seat = models.ForeignKey(Seat, models.PROTECT)
    name = models.CharField(max_length = 100)

    class Meta:
        ordering = ['event', 'crew', 'seat']
        unique_together = ['event', 'crew', 'seat']

    def __str__(self) -> str:
        return self.name



class Team(models.Model):
    """Extends auth.User functionality for the Fantasy Bumps game."""

    user = models.OneToOneField('auth.User', models.CASCADE)

    mens_crew: list['Purchase']
    womens_crew: list['Purchase']

    def __str__(self) -> str:
        return self.user.username


    def get_crew(self, day: Day, gender: str) -> models.QuerySet['Purchase']:
        """Return all purchases for a day, and gender."""
        return self.purchases.filter(day = day, crew__gender = gender)


@receiver(models.signals.post_save, sender = auth.User)
def create_team(instance: auth.User, created: bool, raw: bool, **_: dict[None, None]) -> None:
    """Creates a linked team for every user."""

    if created and not raw:
        Team.objects.create(user = instance)



class GameEntryQuerySet(models.QuerySet[FinancialGameEntry]):
    """Additional queryset methods related to finances and scores."""

    def extend_financials(self) -> 'GameEntryQuerySet':
        """Add crew values and non-gendered totals to the queried data."""
        return self.annotate(
            mens_crew_value = models.F('mens_budget') - models.F('mens_balance'),
            womens_crew_value = models.F('womens_budget') - models.F('womens_balance'),
        ).annotate(
            total_budget = models.F('mens_budget') + models.F('womens_budget'),
            total_crew_value = models.F('mens_crew_value') + models.F('womens_crew_value'),
        )

    def rank_by(self, gender: str = GENDERS_OVERALL) -> 'GameEntryQuerySet':
        """Retrieve team ranking for the gender provided.

        Requires .extend_financials() to have been called.
        """
        ordering = {
            GENDERS_OVERALL: ['-total_budget', '-total_crew_value', 'team__user__username'],
            Genders.MEN: ['-mens_budget', '-mens_crew_value', 'team__user__username'],
            Genders.WOMEN: ['-womens_budget', '-womens_crew_value', 'team__user__username'],
        }[gender]
        return self.order_by(*ordering)



class GameEntry(models.Model):
    """Describes a team's finances (and by extension, score) for an event."""

    # Fields
    team = models.ForeignKey(Team, models.CASCADE, related_name='entries')
    event = models.ForeignKey(Event, models.CASCADE, related_name='fantasies')
    mens_budget = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    womens_budget = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    mens_balance = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    womens_balance = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)

    objects = GameEntryQuerySet.as_manager()

    class Meta:
        unique_together = ['team', 'event']



class Purchase(models.Model):
    """A purchase for a fantasy team."""

    team = models.ForeignKey(Team, models.CASCADE, related_name = 'purchases')
    day = models.ForeignKey(Day, models.CASCADE, related_name = 'purchases')
    crew = models.ForeignKey(Crew, models.PROTECT, related_name = 'purchases')
    seat = models.ForeignKey(Seat, models.PROTECT)
    athlete = models.ForeignKey(Athlete, models.SET_NULL, related_name = 'purchases', null = True)

    price: int

