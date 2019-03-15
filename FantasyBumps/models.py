from django.db import models


class Rower(models.Model):
    """Describes a rower on a fantasy team."""
    
    team = models.ForeignKey('auth.User', models.CASCADE)
    seat = models.ForeignKey('external.Seat', models.PROTECT)

