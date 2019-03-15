from django.db import models


class Rower(models.Model):
    """Describes a rower on a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    crew = models.ForeignKey('external.Crew', models.PROTECT)
    seat = models.ForeignKey('external.Seat', models.PROTECT)

