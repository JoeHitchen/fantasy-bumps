from django.urls import path, re_path, include
from django.conf.urls.static import static

from . import settings
from . import views


urlpatterns = [
    re_path('^healthcheck/?$', views.healthcheck, name = 'healthcheck'),
    path('accounts/signup/', views.UserCreationView.as_view(), name = 'signup'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('FantasyBumps.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
