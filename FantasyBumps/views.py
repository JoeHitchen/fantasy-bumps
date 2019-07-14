from django.views.generic.detail import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse

from .constants import genders
from . import models
from . import forms
from . import utils


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
        context['fantasies'] = self.event.fantasies.add_totals().rank_by(ranking)
        
        return context



class MarketActionMixin(LoginRequiredMixin, SuccessMessageMixin):
    
    # Mixin settings
    template_name = 'fantasybumps/form.html'
    redirect_field_name = None  # Don't include return path in login redirect
    
    def get_form_kwargs(self):
        """Supplies team information to the form."""
        kwargs = super().get_form_kwargs()
        self.event = models.Event.objects.first()
        kwargs.update({
            'team': self.request.user.team,
            'day': self.event.active_day,
        })
        return kwargs
    
    def form_valid(self, form):
        """Saves the valid form."""
        self.form_save_out = form.save()
        return super().form_valid(form)



class BuyView(MarketActionMixin, FormView):
    
    # View settings
    form_class = forms.Buy
    
    def get_success_url(self):
        """Returns the relevant market page for the gender purchased."""
        gender = {genders.MENS: 'men', genders.WOMENS: 'women'}[self.form_save_out.crew.gender]
        return reverse(
            'fantasybumps:{}'.format(gender),
            kwargs = {'event_tag': self.event.tag},
        )
    
    
    def get_success_message(self, cleaned_data):
        """Generates the success message text."""
        seat = cleaned_data['seat']
        return 'Successfully added {} to your crew {} {}.'.format(
            cleaned_data['crew'],
            'as the' if seat.cox else 'at',
            str(seat).lower(),
        )



class SellView(MarketActionMixin, FormView):
    
    # View settings
    form_class = forms.Sell
    
    def get_success_url(self):
        """Returns the relevant market page for the gender sold."""
        gender = {genders.MENS: 'men', genders.WOMENS: 'women'}[self.form_save_out]
        return reverse(
            'fantasybumps:{}'.format(gender),
            kwargs = {'event_tag': self.event.tag},
        )
    
    
    def get_success_message(self, cleaned_data):
        """Generates the success message text."""
        seat = cleaned_data['seat']
        return 'Successfully sold your {}{}.'.format(
            str(seat).lower(),
            '' if seat.cox else ' seat',
        )

