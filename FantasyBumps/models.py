from django.db import models

from external.constants import genders


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


class Position(models.Model):
    """A crew's position on the river for a given day."""
    
    day = models.ForeignKey(Day, models.CASCADE, related_name = 'positions')
    crew = models.ForeignKey('external.Crew', models.PROTECT)
    rank = models.PositiveSmallIntegerField()
    
    class Meta:
        ordering = ['day', 'rank']



class Purchase(models.Model):
    """A purchase for a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    day = models.ForeignKey(Day, models.CASCADE)
    crew = models.ForeignKey('external.Crew', models.PROTECT)
    seat = models.ForeignKey('external.Seat', models.PROTECT)

