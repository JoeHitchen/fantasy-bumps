from django import forms
from django.contrib.auth import models as auth
from django.contrib.auth.forms import UserCreationForm


class UserCreationWithEmailForm(UserCreationForm):
    email = forms.EmailField(required = False)
    
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

