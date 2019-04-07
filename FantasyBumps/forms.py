from django import forms

from external import models as ext_models
from external.constants import genders

from . import models


class Buy(forms.ModelForm):
    
    class Meta:
        model = models.Purchase
        fields = ('crew', 'seat')
    
    
    def save(self, team, day):
        """Add a team and day to the created purchase."""
        
        purchase = super().save(commit = False)
        purchase.team = team
        purchase.day = day
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
    
    def __init__(self, *args, team, day, **kwargs):
        """Store the 'team' and 'day' keyword arguments."""
        
        super().__init__(*args, **kwargs)
        self.team = team
        self.day = day
    
    
    def save(self):
        """Delete all purchase instances matching the criteria provided. Return the gender."""
        
        models.Purchase.objects.filter(
            team = self.team,
            day = self.day,
            seat = self.cleaned_data['seat'],
            crew__gender = self.cleaned_data['gender'],
        ).delete()
        return self.cleaned_data['gender']

