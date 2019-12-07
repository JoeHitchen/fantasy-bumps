from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, prefetch_related_objects
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404

from .constants import genders, money
from . import models
from . import utils
from . import transactions
from . import errors


class IndexView(TemplateView):
    template_name = 'fantasybumps/index.html'
    
    def get_context_data(self, **kwargs):
        return {'events': models.Event.objects.all()}



class EventView(DetailView):
    """A base view and index for event-specific pages."""
    
    # View settings
    model = models.Event
    slug_url_kwarg = 'event_tag'
    slug_field = 'tag'
    template_name = 'fantasybumps/event.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        self.event = self.object  # Provide friendly name for retrived event.
        self.day = self.event.active_day
        context['day'] = self.day
        
        if self.request.user.is_authenticated:
            self.team = self.request.user.team
            context['team'] = self.team
        
        return context



class MarketView(EventView):
    """Presents the market pages for an event."""
    
    # View settings
    template_name = 'fantasybumps/market.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        gender = self.kwargs['gender']
        context['gender_code'] = gender
        context['gender'] = {genders.MENS: 'Men', genders.WOMENS: 'Women'}[gender]
        
        context['start_order'] = self.day.start_order(gender)
        
        def position_prefetch(day, attr):
            return Prefetch('positions', models.Position.objects.filter(day = day), to_attr = attr)
        
        crews = [posn.crew for div in context['start_order'] for posn in div]
        prefetch_related_objects(
            crews,
            position_prefetch(self.day.event.days.first(), '_posn_start'),
            position_prefetch(self.day.prev, '_posn_yest'),
            position_prefetch(self.day, '_posn_today'),
        )
        
        user = self.request.user
        if user.is_authenticated:
            
            crew = user.team.get_crew(self.day, gender)
            context['crew'] = crew
            context['crew_valid'] = utils.has_all_seats(crew, models.Seat.objects.all())
            
            other_gender = utils.reverse_gender(gender)
            other_crew = user.team.get_crew(self.day, other_gender)
            context['other_crew_valid'] = utils.has_all_seats(
                other_crew,
                models.Seat.objects.all(),
            )
            
            finances = self.team.entries.extend_financials().filter(event = self.event)
            if finances:
                finances = finances[0]
                context['finances'] = {
                    genders.MENS: {
                        'budget': finances.mens_budget,
                        'crew_value': finances.mens_crew_value,
                        'balance': finances.mens_balance,
                    },
                    genders.WOMENS: {
                        'budget': finances.womens_budget,
                        'crew_value': finances.womens_crew_value,
                        'balance': finances.womens_balance,
                    },
                }[gender]
            else:
                context['finances'] = {
                    'budget': money.INITIAL_BALANCE,
                    'crew_value': 0,
                    'balance': money.INITIAL_BALANCE,
                }
        
        context['show_actions'] = user.is_authenticated and self.day.market_is_open
        return context



class LeaderboardView(EventView):
    """Presents the leaderboard for an event."""
    
    # View settings
    template_name = 'fantasybumps/leaderboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genders'] = genders
        
        ranking = self.kwargs.get('gender', genders.TOTALS)
        context['ranking'] = ranking
        context['fantasies'] = (
            self.event.fantasies
            .select_related('team', 'team__user')
            .extend_financials()
            .rank_by(ranking)
        )
        
        return context



class TeamView(EventView):
    """Presents a team's crews for an event."""
    
    # View settings
    template_name = 'fantasybumps/team.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        finances = get_object_or_404(
            models.GameEntry.objects.select_related().extend_financials(),
            team__user__username = self.kwargs['team_name'],
            event = self.event,
        )
        team = finances.team
        
        context['team'] = team
        context['finances'] = finances
        context['mens_crew'] = team.get_crew(self.day, genders.MENS)
        context['womens_crew'] = team.get_crew(self.day, genders.WOMENS)
        return context



@require_POST
@login_required(redirect_field_name = None)
def buy(request):
    """Purchas a new athlete for the user's team, if they have sufficient funds.
    
    Inputs:
        POST 'day'  - ID of Day on which to conduct purchase.
                      Markets must be open for that day.
        POST 'crew' - ID of Crew to purchase.
                      Must be racing on said day.
    
    Requires 14 base queries. Caching crew values reduces this by two. Adding a team budget
    increases this by three.
    """
    
    # Process inputs
    try:
        team = request.user.team
        day = models.Day.objects.select_related().get(id = request.POST.get('day'))
        crew = models.Crew.objects.get(id = request.POST.get('crew'))
    
    except ObjectDoesNotExist:
        messages.error(request, 'An error occurred processing the request data.')
        return redirect('fantasybumps:index')
    
    
    # Check market status
    gender_string = {genders.MENS: 'men', genders.WOMENS: 'women'}[crew.gender]
    market_url_name = 'fantasybumps:' + gender_string
    market_redirect = redirect(market_url_name, event_tag = day.event.tag)
    
    if not day.market_is_open:
        messages.warning(request, 'Markets are not open for this sale.')
        return market_redirect
    
    
    # Get seat to fill
    filled_seats = team.get_crew(day, crew.gender).values_list('seat', flat = True)
    seat = models.Seat.objects.exclude(id__in = filled_seats).first()
    if not seat:
        messages.warning(request, "You have already filled your {}'s crew.".format(gender_string))
        return market_redirect
    
    
    # Get athlete
    try:
        athlete = crew.crew_lists.get(event = day.event, seat = seat)
    except models.Athlete.DoesNotExist:
        athlete = None
    
    
    # Perform transaction
    try:
        transactions.buy(team, day, seat, crew, athlete)
    
    except errors.NotRacingError:
        messages.warning(request, 'Cannot buy a crew on a day they are not racing.')
    
    except errors.InsufficientFundsError:
        messages.warning(request, 'You do not have sufficient funds to make this purchase.')
    
    # Generate success message
    else:
        athlete_string = '{} ({})'.format(athlete, crew) if athlete else crew
        
        if seat.cox:
            seat_string = 'cox'
        elif len(seat.name) == 1:
            seat_string = seat.name.lower() + '-seat'
        else:
            seat_string = seat.name.lower() + ' seat'
        
        success_text = "Bought {} as your {}'s {}.".format(
            athlete_string,
            gender_string,
            seat_string,
        )
        messages.success(request, success_text)
    
    return market_redirect



@require_POST
@login_required(redirect_field_name = None)
def sell(request):
    """Sell a previously bought athlete, to release the cash and seat.
    
    Inputs:
        POST 'purchase' - ID of the Purchase object to sell.
                          Must belong to user's team.
                          Must be for day that has currently open markets.
    
    Requires ten base queries. Caching crew values reduces this by two.
    """
    
    # Process input data
    try:
        purchase = models.Purchase.objects.select_related().get(
            id = request.POST.get('purchase'),
            team = request.user.team,
        )
    
    except models.Purchase.DoesNotExist:
        
        # Try elegent redirect back to market page using additional form data
        messages.error(request, 'You are not authorised to conduct this sale.')
        try:
            gender_code = request.POST.get('gender')
            gender_string = {genders.MENS: 'men', genders.WOMENS: 'women'}[gender_code]
            url_name = 'fantasybumps:{}'.format(gender_string)
            event = models.Event.objects.get(tag = request.POST.get('event'))
            return redirect(url_name, event_tag = event.tag)
        
        except (KeyError, models.Event.DoesNotExist):
            return redirect('fantasybumps:index')
    
    
    # Check market status
    gender_string = {genders.MENS: 'men', genders.WOMENS: 'women'}[purchase.crew.gender]
    market_url_name = 'fantasybumps:' + gender_string
    market_redirect = redirect(market_url_name, event_tag = purchase.day.event.tag)
    
    if not purchase.day.market_is_open:
        messages.warning(request, 'Markets are not open for this sale.')
        return market_redirect
    
    
    # Perform transaction
    try:
        transactions.sell(purchase)
    
    except models.Purchase.DoesNotExist:
        messages.warning(request, 'This sale has already been completed.')
    
    except (models.GameEntry.DoesNotExist, MultipleObjectsReturned):
        messages.error(request, 'An unknown error occurred processing this sale.')
    
    else:
        success_text = "Successfully sold your {}'s {}{}.".format(
            gender_string,
            str(purchase.seat).lower(),
            '' if purchase.seat.cox else ' seat',
        )
        messages.success(request, success_text)
    
    return market_redirect



class Switch(TemplateView):
    """Presents athlete and seat selectors for a purchase to alter it.
    
    Additionally, has a POST action to perform the switch.
    """
    template_name = 'fantasybumps/switch.html'
    
    @method_decorator(login_required(redirect_field_name = None))
    def dispatch(self, request, *args, **kwargs):
        
        # Look for purchase
        self.purchase = get_object_or_404(
            models.Purchase.objects.select_related(),  # Misses purchase.athlete, but simplier code
            id = kwargs.get('purchase_id', None),
            team = request.user.team,
        )
        
        # Check market status
        gender_string = {genders.MENS: 'men', genders.WOMENS: 'women'}[self.purchase.crew.gender]
        market_url_name = 'fantasybumps:' + gender_string
        self.market_redirect = redirect(market_url_name, event_tag = self.purchase.day.event.tag)
        
        if not self.purchase.day.market_is_open:
            messages.warning(request, 'Markets are not open to alter this purchase.')
            return self.market_redirect
        
        # Cannot switch coxes
        if self.purchase.seat.cox:
            messages.warning(request, 'Coxes must stay in their place.')
            return self.market_redirect
        
        return super().dispatch(request, *args, **kwargs)
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['purchase'] = self.purchase
        
        context['rowers'] = models.Athlete.objects.filter(
            event = self.purchase.day.event,
            crew = self.purchase.crew,
            seat__cox = False,
        ).select_related('seat')
        
        
        other_purchases = self.purchase.team.get_crew(
            day = self.purchase.day,
            gender = self.purchase.crew.gender,
        ).exclude(id = self.purchase.id)
        
        context['other_purchased_athletes'] = models.Athlete.objects.filter(
            id__in = other_purchases.values_list('athlete', flat = True),
        )
        
        context['seats'] = models.Seat.objects.all()
        
        return context
    
    
    def post(self, request, purchase_id):
        """Move a purchase between rowing seats and select named athlete.
        
        Inputs:
            POST 'athlete_id': ID of Athlete to occupy Seat (or '0' for unnamed athlete)
            POST 'seat_id':    ID of Seat for Athlete to occupy
        
        Requires 12 queries.
        """
        
        old_athlete_id = self.purchase.athlete.id if self.purchase.athlete else 0
        
        # Perform action
        try:
            updated_purchase = transactions.switch(
                self.purchase,
                request.POST.get('athlete', old_athlete_id),
                request.POST.get('seat', '0'),
            )
        
        except models.Athlete.DoesNotExist:
            messages.warning(request, 'Must pick a rower from the purchased crew.')
        
        except errors.DuplicateAthleteError:
            messages.warning(request, 'Cannot pick the same rower twice.')
        
        except models.Seat.DoesNotExist:
            messages.warning(request, 'Target seat does not exist.')
        
        except errors.NinthSeatError:
            messages.warning(request, "Rowers can't cox.")
        
        # Generate success message
        else:
            
            if updated_purchase.athlete:
                crew_string = '{} ({})'.format(updated_purchase.athlete, updated_purchase.crew)
            else:
                crew_string = updated_purchase.crew
            
            gender_string = {
                genders.MENS: 'men',
                genders.WOMENS: 'women',
            }[self.purchase.crew.gender]
            
            seat_string = updated_purchase.seat.name.lower()
            seat_string = seat_string + ('-' if len(seat_string) == 1 else ' ') + 'seat'
            
            messages.success(request, "Selected {} for your {}'s {}.".format(
                crew_string,
                gender_string,
                seat_string,
            ))
        
        
        return self.market_redirect

