from django.views.generic.edit import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse

from . import forms


healthcheck_notice = 'This healthcheck gives the name of the service and echos any GET data provided to demonstrate a dynamic response.'  # noqa: E501


def healthcheck(request):
    return JsonResponse({
        **request.GET.dict(),
        'name': 'FantasyBumps',
        'notice': healthcheck_notice,
    })


class UserCreationView(SuccessMessageMixin, CreateView):
    """Renders and processes a user creation form."""
    
    # View settings
    form_class = forms.UserCreationWithEmailForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('index')
    
    def get_success_message(self, data):
        return 'Welcome {} - Your account has been created.'.format(self.object)
    
    def form_valid(self, form):
        """Creates and signs in the new user."""
        
        redirect = super().form_valid(form)
        authed_user = authenticate(
            username = self.request.POST['username'],
            password = self.request.POST['password1'],
        )
        login(self.request, authed_user)
        return redirect



class UserProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Renders and processes a user update form."""
    
    # View settings
    form_class = forms.UserProfileForm
    template_name = 'registration/profile.html'
    redirect_field_name = None
    success_url = reverse_lazy('profile')
    success_message = 'Profile updated'
    
    def get_object(self, *args, **kwargs):
        return self.request.user

