import re

from django import forms
from django.contrib.auth import models as auth
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


username_blacklist_regexes = [
    ['blacklisttest', None],
    ['hitchen', 'The admin requests that you do not feature them in your team name.'],
    [
        'hitchin',
        'The admin requests that you do not feature them in your team name.'
        + ' Also you spelt it wrong.',
    ],
]


class UserCreationWithEmailForm(UserCreationForm):
    email = forms.EmailField(required = False)
    
    def clean_username(self):
        username = self.cleaned_data['username']
        for blacklist, error_message in username_blacklist_regexes:
            if re.search(blacklist, username, re.IGNORECASE):
                raise ValidationError(error_message or 'This team name is not permitted.')
                
        return username
    
    
    def save(self):
        """Adds an optional e-mail address to the new user."""
        
        user = super().save(commit = False)
        if 'email' in self.cleaned_data:
            user.email = self.cleaned_data['email']
        
        user.save()
        return user



class UserProfileForm(forms.ModelForm):
    """A user-update form with an optional e-mail field."""
    
    class Meta:
        model = auth.User
        fields = ('email',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False

