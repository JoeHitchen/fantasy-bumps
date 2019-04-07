from django import forms

from external import models as ext_models
from external.constants import genders

from . import models


class Buy(forms.ModelForm):
    
    class Meta:
        model = models.Purchase
        fields = ('crew', 'seat')
    
    
    def save(self, team):
        """Add a team to the created purchase and saves it."""
        
        purchase = super().save(commit = False)
        purchase.team = team
        purchase.save()
        return purchase



class Sell(forms.Form):
    
    seat = forms.ModelChoiceField(queryset = ext_models.Seat.objects.all())
    gender = forms.ChoiceField(
        choices = [
            (genders.MENS, "Men's"),
            (genders.WOMENS, "Women's"),
        ],
    )
    
    def __init__(self, *args, team, **kwargs):
        """Stores the 'team' keyword argument."""
        
        super().__init__(*args, **kwargs)
        self.team = team
    
    
    def save(self):
        """Delete all purchase instances matching the team, seat, and gender. Return the gender."""
        
        models.Purchase.objects.filter(
            team = self.team,
            seat = self.cleaned_data['seat'],
            crew__gender = self.cleaned_data['gender'],
        ).delete()
        return self.cleaned_data['gender']

