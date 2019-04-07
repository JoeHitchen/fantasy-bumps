from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse

from external import utils as ext
from external.constants import genders
from Bumps import models as bmp_models

from . import forms
from . import utils


class IndexView(TemplateView):
    template_name = 'fantasybumps/index.html'



class MarketView(TemplateView):
    template_name = 'fantasybumps/market.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        gender = context['gender']
        context['gender'] = {genders.MENS: 'Men', genders.WOMENS: 'Women'}[gender]
        
        day = bmp_models.Day.objects.first()
        context['start_order'] = day.start_order(gender)
        
        user = self.request.user
        if user.is_authenticated:
            
            crew = utils.get_crew(user, day, gender)
            context['crew'] = crew
            context['crew_valid'] = utils.has_all_seats(crew)
            
            other_gender = ext.reverse_gender(gender)
            other_crew = utils.get_crew(user, day, other_gender)
            context['other_crew_valid'] = utils.has_all_seats(other_crew)
        
        return context



class BuyView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    
    # View settings
    template_name = 'fantasybumps/form.html'
    form_class = forms.Buy
    redirect_field_name = None  # Don't include return path in login redirect
    
    def form_valid(self, form):
        """Saves the valid form."""
        self.purchase = form.save(self.request.user, bmp_models.Day.objects.first())
        return super().form_valid(form)
    
    
    def get_success_url(self):
        """Returns the relevant market page for the gender purchased."""
        return reverse('fantasybumps:{}'.format(
            {genders.MENS: 'men', genders.WOMENS: 'women'}[self.purchase.crew.gender],
        ))
    
    
    def get_success_message(self, cleaned_data):
        """Generates the success message text."""
        seat = cleaned_data['seat']
        return 'Successfully added {} to your crew {} {}.'.format(
            cleaned_data['crew'],
            'as the' if seat.cox else 'at',
            str(seat).lower(),
        )



class SellView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    
    # View settings
    template_name = 'fantasybumps/form.html'
    form_class = forms.Sell
    redirect_field_name = None  # Don't include return path in login redirect
    
    def get_form_kwargs(self):
        """Supplies team information to the form."""
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'team': self.request.user,
            'day': bmp_models.Day.objects.first(),
        })
        return kwargs
    
    def form_valid(self, form):
        """Saves the valid form."""
        self.gender = form.save()
        return super().form_valid(form)
    
    
    def get_success_url(self):
        """Returns the relevant market page for the gender sold."""
        return reverse('fantasybumps:{}'.format(
            {genders.MENS: 'men', genders.WOMENS: 'women'}[self.gender],
        ))
    
    
    def get_success_message(self, cleaned_data):
        """Generates the success message text."""
        seat = cleaned_data['seat']
        return 'Successfully sold your {}{}.'.format(
            str(seat).lower(),
            '' if seat.cox else ' seat',
        )

