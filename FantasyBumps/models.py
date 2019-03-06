from django.db import models


class Rower(models.Model):
    """Describes a rower on a fantasy team."""
    
    seat = models.ForeignKey('external.Seat', models.PROTECT)

