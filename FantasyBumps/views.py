from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from .constants import genders
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
        context['gender'] = {genders.MENS: 'Men', genders.WOMENS: 'Women'}[gender]
        
        context['start_order'] = self.day.start_order(gender)
        
        user = self.request.user
        if user.is_authenticated:
            
            crew = user.team.get_crew(self.day, gender)
            context['crew'] = crew
            context['crew_valid'] = utils.has_all_seats(crew)
            
            other_gender = utils.reverse_gender(gender)
            other_crew = user.team.get_crew(self.day, other_gender)
            context['other_crew_valid'] = utils.has_all_seats(other_crew)
        
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
    
    
    # Perform transaction
    try:
        transactions.buy(team, day, seat, crew)
    
    except errors.InsufficientFundsError:
        messages.warning(request, 'You do not have sufficient funds to make this purchase.')
    
    else:
        success_text = "Successfully bought {} as your {}'s {}{}.".format(
            crew,
            gender_string,
            str(seat).lower(),
            '' if seat.cox else ' seat',
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
        messages.error(request, 'You are not authorised to conduct this sale.')
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

