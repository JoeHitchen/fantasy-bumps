from datetime import datetime, timedelta
from functools import lru_cache

from django.db import models
from django.contrib.auth import models as auth
from django.utils import timezone
from django.utils.functional import cached_property
from django.dispatch import receiver

from .constants import genders, timings, money, clubs


class Event(models.Model):
    """A bumps competition, with simple division information."""
    
    name = models.CharField(max_length = 20)
    tag = models.SlugField(max_length = 15, unique = True)  # Implicit db index
    
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
        day_shift = timedelta(1) if now.time() >= timings.MARKET_OPENS else timedelta(0)
        date = now.date() + day_shift
        
        day = self.days.filter(date__gte = date).first()
        return day if day else self.days.last()



class Day(models.Model):
    """A day of racing."""
    
    event = models.ForeignKey(Event, models.CASCADE, related_name = 'days')
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
        return self.event.days.filter(date__gt = self.date).first()
    
    
    @cached_property
    def first_race(self):
        """The datetime for the first race of the day, or None if not racing day."""
        return datetime.combine(
            self.date,
            self.first_race_time,
            timezone.now().tzinfo,
        ) if self.first_race_time else None
    
    
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
        
        if not self.first_race:
            return
        
        earlier_days = self.event.days.exclude(date__gte = self.date).exists()
        
        return datetime.combine(
            self.date - timedelta(1 if earlier_days else 4),
            timings.MARKET_OPENS,
            timezone.now().tzinfo,
        )
    
    
    @cached_property
    def market_closes(self):
        """Markets always close half an hour before the first race, if one occurs."""
        return self.first_race - timedelta(minutes = 30) if self.first_race else None
    
    
    @cached_property
    def market_is_open(self):
        """Indicates whether the market is currently open for trading."""
        if not self.first_race:
            return False
        return self.market_opens <= timezone.now() < self.market_closes
    
    
    def advance_purchases_to_next(self):
        """Creates a copy of all purchase records for today on the next day.
        
        MAX four queries. Recommend fetching day with select_related.
        """
        
        Purchase.objects.bulk_create([
            Purchase(
                team = purchase.team,
                day = self.next,
                crew = purchase.crew,
                seat = purchase.seat,
            )
            for purchase in self.purchases.select_related().all()
        ])



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
        
        return self.day.ranking.filter(
            crew__gender = self.gender,
            rank__gte = self.top_bungline,
            rank__lte = self.bottom_bungline,
        ).annotate(
            bungline = models.F('rank') - self.top_bungline + 1,
        )



class Crew(models.Model):
    """Describes a crew (e.g. New College W1)"""
    
    club = models.CharField(
        max_length = 4,
        choices = clubs,
        db_index = True,
    )
    gender = models.CharField(
        max_length = 1,
        choices = [
            (genders.MENS, "Men's"),
            (genders.WOMENS, "Women's"),
        ],
        db_index = True,
    )
    rank = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return '{} {}{}'.format(self.get_club_display(), self.gender, self.rank)
    
    
    @lru_cache(maxsize = 10)
    def value(self, day):
        """The price of the crew for a given day."""
        
        total_crews = (
            day.ranking
            .filter(crew__gender = self.gender)
            .aggregate(models.Max('rank'))
            ['rank__max']
        )
        
        try:
            rank = self.positions.get(day = day).rank
        except Position.DoesNotExist:
            return 0
        
        ratio = (money.PRICE_MIN / money.PRICE_MAX) ** (1 / (total_crews - 1))
        return round(money.PRICE_MAX * ratio ** (rank - 1))



class Position(models.Model):
    """A crew's position on the river for a given day."""
    
    day = models.ForeignKey(Day, models.CASCADE, related_name = 'ranking')
    crew = models.ForeignKey(Crew, models.PROTECT, related_name = 'positions')
    rank = models.PositiveSmallIntegerField(db_index = True)
    
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



class Team(models.Model):
    """Extends auth.User functionality for the Fantasy Bumps game."""
    
    user = models.OneToOneField('auth.User', models.CASCADE)
    
    def __str__(self):
        return self.user.username
    
    
    def get_crew(self, day, gender):
        """Return all purchases for a day, and gender."""
        return self.purchases.filter(day = day, crew__gender = gender)


@receiver(models.signals.post_save, sender = auth.User)
def create_team(sender, instance, created, **kwargs):
    if created:
        Team.objects.create(user = instance)



class GameEntryQuerySet(models.QuerySet):
    """Additional queryset methods related to finances and scores."""
    
    def extend_financials(self):
        """Add crew values and non-gendered totals to the queried data."""
        return self.annotate(
            mens_crew_value = models.F('mens_budget') - models.F('mens_balance'),
            womens_crew_value = models.F('womens_budget') - models.F('womens_balance'),
        ).annotate(
            total_budget = models.F('mens_budget') + models.F('womens_budget'),
            total_crew_value = models.F('mens_crew_value') + models.F('womens_crew_value'),
        )
    
    def rank_by(self, gender = genders.TOTALS):
        """Retrieve team ranking for the gender provided.
        
        Requires .extend_financials() to have been called.
        """
        ordering = {
            genders.TOTALS: ['-total_budget', '-total_crew_value'],
            genders.MENS: ['-mens_budget', '-mens_crew_value'],
            genders.WOMENS: ['-womens_budget', '-womens_crew_value'],
        }[gender]
        return self.order_by(*ordering)



class GameEntry(models.Model):
    """Describes a team's finances (and by extension, score) for an event."""
    
    # Fields
    team = models.ForeignKey(Team, models.CASCADE, related_name='entries')
    event = models.ForeignKey(Event, models.CASCADE, related_name='fantasies')
    mens_budget = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    womens_budget = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    mens_balance = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    womens_balance = models.PositiveSmallIntegerField(default = money.INITIAL_BALANCE)
    
    objects = GameEntryQuerySet.as_manager()
    
    class Meta:
        unique_together = ['team', 'event']



class Purchase(models.Model):
    """A purchase for a fantasy team."""
    
    team = models.ForeignKey(Team, models.CASCADE, related_name = 'purchases')
    day = models.ForeignKey(Day, models.CASCADE, related_name = 'purchases')
    crew = models.ForeignKey(Crew, models.PROTECT)
    seat = models.ForeignKey(Seat, models.PROTECT)

