from django import forms

from external import models as ext_models
from external.constants import genders

from . import models


class Buy(forms.ModelForm):
    
    class Meta:
        model = models.Rower
        fields = ('crew', 'seat')
    
    
    def save(self, team):
        """Adds the team to the Rower object and creates it."""
        
        rower = super().save(commit = False)
        rower.team = team
        rower.save()
        return rower



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
        """Deletes all rower instances matching the team, seat, and gender. Returns the gender."""
        
        models.Rower.objects.filter(
            team = self.team,
            seat = self.cleaned_data['seat'],
            crew__gender = self.cleaned_data['gender'],
        ).delete()
        return self.cleaned_data['gender']

