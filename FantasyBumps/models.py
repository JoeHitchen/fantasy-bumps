from django.db import models


class Purchase(models.Model):
    """A purchase for a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    crew = models.ForeignKey('external.Crew', models.PROTECT)
    seat = models.ForeignKey('external.Seat', models.PROTECT)

