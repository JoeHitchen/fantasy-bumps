from django.db import models


class Seat(models.Model):
    """Describes a position within a boat."""
    
    name = models.CharField(max_length = 6)
    cox = models.BooleanField()
    
    @property
    def short(self):
        return self.name[0]

