from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from .constants import genders


class Event(models.Model):
    """A bumps competition, with simple division information."""
    
    name = models.CharField(max_length = 20)
    
    mens_divisions = models.PositiveSmallIntegerField()
    womens_divisions = models.PositiveSmallIntegerField()
    boats_per_division = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return self.name



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
    
    
    def start_order(self, gender):
        """Return the day's start order for the given gender.
        
        The number of division and number of boats per division is taken from then parent event,
        and an extra boat is added to the last division.
        """
        
        # Get number of divisions
        number_of_divisions = {
            genders.MENS: self.event.mens_divisions,
            genders.WOMENS: self.event.womens_divisions,
        }[gender]
        
        # Create division slices
        slices = [
            slice(
                self.event.boats_per_division * (division - 1),
                self.event.boats_per_division * division,
            )
            for division in range(1, number_of_divisions)
        ]
        slices.append(slice(
            self.event.boats_per_division * (number_of_divisions - 1),
            self.event.boats_per_division * number_of_divisions + 1,
        ))
        
        # Create start order
        ranking = self.positions.filter(crew__gender = gender)
        return [ranking[slice] for slice in slices]
    
    
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



class Purchase(models.Model):
    """A purchase for a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    day = models.ForeignKey(Day, models.CASCADE)
    crew = models.ForeignKey(Crew, models.PROTECT)
    seat = models.ForeignKey('external.Seat', models.PROTECT)

