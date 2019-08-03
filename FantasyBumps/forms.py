from django import forms

from . import models


class MarketFormMixin:
    
    def __init__(self, *args, team, day, **kwargs):
        """Store the 'team' and 'day' keyword arguments."""
        
        super().__init__(*args, **kwargs)
        self.team = team
        self.day = day
    
    
    def clean(self):
        """Invalidates the form if markets are closed."""
        super().clean()
        
        if not self.day.market_is_open:
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

