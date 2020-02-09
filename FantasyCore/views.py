from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.messages.views import SuccessMessageMixin
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
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')
    success_message = 'Account successfully created. Sign in to begin playing.'

