from django.db import models


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
    
    class Meta:
        ordering = ['event', 'date']
    
    def __str__(self):
        return self.name

