from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import authenticate, login
from django.urls import reverse_lazy
from django.http import JsonResponse


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
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('fantasybumps:index')
    
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

