from django import forms

from external import models as ext_models
from external.constants import genders

from . import models
from . import utils


class MarketFormMixin:
    
    def __init__(self, *args, team, day, **kwargs):
        """Store the 'team' and 'day' keyword arguments."""
        
        super().__init__(*args, **kwargs)
        self.team = team
        self.day = day
    
    
    def clean(self):
        """Invalidates the form if markets are closed."""
        super().clean()
        
        if not utils.markets_open(self.day):
            self.add_error(None, 'Markets are not currently open.')



class Buy(MarketFormMixin, forms.ModelForm):
    
    class Meta:
        model = models.Purchase
        fields = ('crew', 'seat')
    
    
    def save(self):
        """Add a team and day to the created purchase."""
        
        purchase = super().save(commit = False)
        purchase.team = self.team
        purchase.day = self.day
        purchase.save()
        return purchase



class Sell(MarketFormMixin, forms.Form):
    
    seat = forms.ModelChoiceField(queryset = ext_models.Seat.objects.all())
    gender = forms.ChoiceField(
        choices = [
            (genders.MENS, "Men's"),
            (genders.WOMENS, "Women's"),
        ],
    )
    
    
    def save(self):
        """Delete all purchase instances matching the criteria provided. Return the gender."""
        
        models.Purchase.objects.filter(
            team = self.team,
            day = self.day,
            seat = self.cleaned_data['seat'],
            crew__gender = self.cleaned_data['gender'],
        ).delete()
        return self.cleaned_data['gender']

