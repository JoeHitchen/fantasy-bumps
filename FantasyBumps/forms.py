from django import forms

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

