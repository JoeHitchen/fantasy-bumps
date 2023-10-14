from typing import Any, TYPE_CHECKING

from django.views.generic.edit import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import authenticate, login, models as auth
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as db
from django.urls import reverse_lazy

from . import forms


if TYPE_CHECKING:
    from django.http import HttpResponse
    from django.forms.forms import BaseForm

    ProfileCreateView = CreateView[auth.User, forms.UserCreationWithEmailForm]
    ProfileUpdateView = UpdateView[auth.User, forms.UserProfileForm]
    ProfileQuerySet = db.QuerySet[auth.User]
else:
    ProfileCreateView = CreateView
    ProfileUpdateView = UpdateView
    ProfileQuerySet = db.QuerySet


class UserCreationView(SuccessMessageMixin, ProfileCreateView):
    """Renders and processes a user creation form."""

    # View settings
    form_class = forms.UserCreationWithEmailForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('index')

    def get_success_message(self, cleaned_data: dict[str, str]) -> str:
        return 'Welcome {} - Your account has been created.'.format(self.object)

    def form_valid(self, form: 'BaseForm') -> 'HttpResponse':
        """Creates and signs in the new user."""

        redirect = super().form_valid(form)
        authed_user = authenticate(
            username = form.cleaned_data['username'],
            password = form.cleaned_data['password1'],
        )
        login(self.request, authed_user)
        return redirect



class UserProfileView(LoginRequiredMixin, SuccessMessageMixin, ProfileUpdateView):
    """Renders and processes a user update form."""

    # View settings
    form_class = forms.UserProfileForm
    template_name = 'registration/profile.html'
    redirect_field_name = None
    success_url = reverse_lazy('profile')
    success_message = 'Profile updated'

    def get_object(self, queryset: ProfileQuerySet | None = None) -> Any:
        return self.request.user

