from datetime import datetime, timedelta
from functools import lru_cache

from django.db import models
from django.contrib.auth import models as auth
from django.utils import timezone
from django.utils.functional import cached_property
from django.dispatch import receiver
import pytz

from core.settings import TIME_ZONE

from .constants import Series, Genders, GENDERS_OVERALL, timings, money, Clubs
from .utils import pricing


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
    
    def __str__(self):
        return '{} {}'.format(self.get_series_display(), self.year)
    
    
    @cached_property
    def first_day(self):
        if hasattr(self, '_days'):
            return self._days[0]
        return self.days.first()
    
    
    @cached_property
    def last_racing_day(self):
        if hasattr(self, '_days'):
            return [day for day in self._days if day.first_race_time][-1]
        return self.days.exclude(first_race_time = None).last()
    
    
    @cached_property
    def active_day(self):
        """The active/most currently relevant day of the event.
        
        Before markets open -> The first day from today onwards.
        After markets open -> The first day from tomorrow onwards.
        After the event -> Last day of the event.
        """
        
        now = timezone.localtime()
        day_shift = timedelta(1) if now.time() >= timings.MARKET_OPENS else timedelta(0)
        date = now.date() + day_shift
        
        if hasattr(self, '_days'):
            future_days = [day for day in self._days if day.date >= date]
            return future_days[0] if future_days else self._days[-1]
        
        day = self.days.filter(date__gte = date).first()
        return day if day else self.days.last()
    
    
    def num_crews(self, gender):
        """The number of crews of the given gender competing in the event."""
        return {
            Genders.MEN: sum(self.mens_division_sizes),
            Genders.WOMEN: sum(self.womens_division_sizes),
        }[gender]



class Day(models.Model):
    """A day of racing."""
    
    event = models.ForeignKey(Event, models.CASCADE, related_name = 'days')
    name = models.CharField(max_length = 10)
    date = models.DateField(db_index = True)
    first_race_time = models.TimeField(null = True, db_index = True)
    
    class Meta:
        ordering = ['event', 'date']
    
    def __str__(self):
        return self.name
    
    @cached_property
    def next(self):
        """The next day of the event."""
        if hasattr(self.event, '_days'):
            future_days = [day for day in self.event._days if day.date > self.date]
            return future_days[0] if future_days else None
        return self.event.days.filter(date__gt = self.date).first()
    
    
    @cached_property
    def prev(self):
        """The previous day of the event."""
        if hasattr(self.event, '_days'):
            past_days = [day for day in self.event._days if day.date < self.date]
            return past_days[-1] if past_days else None
        return self.event.days.filter(date__lt = self.date).order_by('-date').first()
    
    
    @cached_property
    def first_race(self):
        """The datetime for the first race of the day, or None if not racing day."""
        
        if not self.first_race_time:
            return None
        
        naive = datetime.combine(self.date, self.first_race_time)
        return pytz.timezone(TIME_ZONE).localize(naive)
    
    
    @lru_cache(maxsize=2)
    def divisions(self, gender):
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
    
    
    def start_order(self, gender, extend = lambda so: so):
        """Builds the day and gender's start order from the start order of each division."""
        return [extend(division.start_order()) for division in self.divisions(gender)]
    
    
    @cached_property
    def market_opens(self):
        """Gives the time that markets open for trading, for racing days.
        
        Markets always open at 8:00PM. On the first day, they open four days before racing. For
        later days they open the day before racing."""
        
        if not self.first_race:
            return
        
        naive = datetime.combine(
            self.prev.date if self.prev else self.date - timedelta(3),
            timings.MARKET_OPENS,
        )
        return pytz.timezone(TIME_ZONE).localize(naive)
    
    
    @cached_property
    def market_closes(self):
        """Markets always close half an hour before the first race, if one occurs."""
        return self.first_race - timedelta(minutes = 30) if self.first_race else None
    
    
    @cached_property
    def market_is_open(self):
        """Indicates whether the market is currently open for trading."""
        if not self.first_race:
            return False
        return self.market_opens <= timezone.localtime() < self.market_closes



class Division:
    """Temporary objects for storing division information and start orders."""
    
    def __init__(self, day, gender, number, top_bungline, bottom_bungline):
        """Sets provided arguments as properties."""
        
        self.day = day
        self.gender = gender
        self.number = number
        self.top_bungline = top_bungline
        self.bottom_bungline = bottom_bungline
    
    
    def start_order(self):
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
    
    def __str__(self):
        return '{} {}{}'.format(self.get_club_display(), self.gender, self.rank)
    
    
    def as_tuple(self):
        """Describes the crew in the tuple-form needed for parser interaction."""
        return (self.club, self.gender, self.rank)
    
    
    def value(self, day):
        """The price of the crew for a given day."""
        
        try:
            return pricing(
                self.positions.get(day = day).rank,
                day.event.num_crews(self.gender),
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
    def short(self):
        return self.name[0]
    
    def __str__(self):
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
    
    def __str__(self):
        return self.name



class Team(models.Model):
    """Extends auth.User functionality for the Fantasy Bumps game."""
    
    user = models.OneToOneField('auth.User', models.CASCADE)
    
    def __str__(self):
        return self.user.username
    
    
    def get_crew(self, day, gender):
        """Return all purchases for a day, and gender."""
        return self.purchases.filter(day = day, crew__gender = gender)


@receiver(models.signals.post_save, sender = auth.User)
def create_team(sender, instance, created, **kwargs):
    if created and not kwargs['raw']:
        Team.objects.create(user = instance)



class GameEntryQuerySet(models.QuerySet):
    """Additional queryset methods related to finances and scores."""
    
    def extend_financials(self):
        """Add crew values and non-gendered totals to the queried data."""
        return self.annotate(
            mens_crew_value = models.F('mens_budget') - models.F('mens_balance'),
            womens_crew_value = models.F('womens_budget') - models.F('womens_balance'),
        ).annotate(
            total_budget = models.F('mens_budget') + models.F('womens_budget'),
            total_crew_value = models.F('mens_crew_value') + models.F('womens_crew_value'),
        )
    
    def rank_by(self, gender = GENDERS_OVERALL):
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

