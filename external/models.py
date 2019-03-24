from django.db import models

from .constants import genders


class Seat(models.Model):
    """Describes a position within a boat."""
    
    name = models.CharField(max_length = 6)
    cox = models.BooleanField()
    
    @property
    def short(self):
        return self.name[0]



class Crew(models.Model):
    """Describes a crew (e.g. New College W1)"""
    
    name = models.CharField(max_length = 40)
    gender = models.CharField(
        max_length = 1,
        choices = [
            (genders.MENS, 'Men\'s'),
            (genders.WOMENS, 'Women\'s'),
        ],
    )
    
    def __str__(self):
        return self.name

