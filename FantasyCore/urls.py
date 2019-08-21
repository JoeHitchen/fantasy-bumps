from django.urls import path, include, reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.conf.urls.static import static

from . import settings

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path(
        'accounts/signup/',
        CreateView.as_view(
            form_class = UserCreationForm,
            template_name = 'registration/signup.html',
            success_url = reverse_lazy('login'),
        ),
        name = 'signup',
    ),
    path('', include('FantasyBumps.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
