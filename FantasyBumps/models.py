from datetime import datetime, time, timedelta
from functools import lru_cache

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from .constants import genders


class Event(models.Model):
    """A bumps competition, with simple division information."""
    
    name = models.CharField(max_length = 20)
    tag = models.SlugField(max_length = 15, unique = True)
    
    mens_divisions = models.PositiveSmallIntegerField()
    womens_divisions = models.PositiveSmallIntegerField()
    boats_per_division = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return self.name
    
    
    @cached_property
    def active_day(self):
        """The active/most currently relevant day of the event.
        
        Before 8pm -> The first day from today onwards.
        After 8pm -> The first day from tomorrow onwards.
        After the event -> Last day of the event.
        """
        
        now = timezone.now()
        day_shift = timedelta(1) if now.time() >= time(20, 00) else timedelta(0)
        date = now.date() + day_shift
        
        day = self.day_set.filter(date__gte = date).first()
        return day if day else self.day_set.last()



class Day(models.Model):
    """A day of racing."""
    
    event = models.ForeignKey(Event, models.CASCADE)
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
        return self.event.day_set.filter(date__gt = self.date).first()
    
    
    @lru_cache(maxsize=2)
    def divisions(self, gender):
        """Generates the division structure for the day."""
        
        # Get number of divisions
        number_of_divisions = {
            genders.MENS: self.event.mens_divisions,
            genders.WOMENS: self.event.womens_divisions,
        }[gender]
        
        # Create division structure
        return [
            Division(
                day = self,
                gender = gender,
                top_bungline = (division_number - 1) * self.event.boats_per_division + 1,
                bottom_bungline = division_number * self.event.boats_per_division
                + int(division_number == number_of_divisions),
            )
            for division_number in range(1, number_of_divisions + 1)
        ]
    
    
    def start_order(self, gender):
        """Builds the day and gender's start order from the start order of each division."""
        return [division.start_order for division in self.divisions(gender)]
    
    
    @cached_property
    def market_opens(self):
        """Gives the time that markets open for trading, for racing days.
        
        Markets always open at 8:00PM. On the first day, they open four days before racing. For
        later days they open the day before racing."""
        
        if not self.first_race_time:
            return
        
        earlier_days = self.event.day_set.exclude(date__gte = self.date).exists()
        
        return datetime.combine(
            self.date - timedelta(1 if earlier_days else 4),
            time(hour = 20),
            timezone.now().tzinfo,
        )
    
    
    @cached_property
    def market_closes(self):
        """Markets always close half an hour before the first race, if one occurs."""
        
        if not self.first_race_time:
            return
        
        return datetime.combine(
            self.date,
            self.first_race_time,
            timezone.now().tzinfo,
        ) - timedelta(minutes = 30)
    
    
    @cached_property
    def market_is_open(self):
        """Indicates whether the market is currently open for trading."""
        if not self.first_race_time:
            return False
        return self.market_opens <= timezone.now() < self.market_closes



class Division:
    """Temporary objects for storing division information and start orders."""
    
    def __init__(self, day, gender, top_bungline, bottom_bungline):
        """Sets provided arguments as properties."""
        
        self.day = day
        self.gender = gender
        self.top_bungline = top_bungline
        self.bottom_bungline = bottom_bungline
    
    
    @cached_property
    def start_order(self):
        """Generates start order and bungline numbers (excluding sandwich boat)."""
        
        return self.day.positions.filter(
            crew__gender = self.gender,
            rank__gte = self.top_bungline,
            rank__lte = self.bottom_bungline,
        ).annotate(
            bungline = models.F('rank') - self.top_bungline + 1,
        )



class Crew(models.Model):
    """Describes a crew (e.g. New College W1)"""
    
    name = models.CharField(max_length = 40)
    gender = models.CharField(
        max_length = 1,
        choices = [
            (genders.MENS, "Men's"),
            (genders.WOMENS, "Women's"),
        ],
    )
    
    def __str__(self):
        return self.name



class Position(models.Model):
    """A crew's position on the river for a given day."""
    
    day = models.ForeignKey(Day, models.CASCADE, related_name = 'positions')
    crew = models.ForeignKey(Crew, models.PROTECT)
    rank = models.PositiveSmallIntegerField()
    
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



class Purchase(models.Model):
    """A purchase for a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    day = models.ForeignKey(Day, models.CASCADE)
    crew = models.ForeignKey(Crew, models.PROTECT)
    seat = models.ForeignKey(Seat, models.PROTECT)
    
    class Meta:
        unique_together = ['team', 'day', 'seat']

