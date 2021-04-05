from django.urls import path, include
from django.conf.urls.static import static

from . import settings
from . import views


urlpatterns = [
    path('accounts/signup/', views.UserCreationView.as_view(), name = 'signup'),
    path('accounts/profile/', views.UserProfileView.as_view(), name = 'profile'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('fantasy.urls')),
    path('', lambda req: None, name = 'index'),  # Alias, handled by app
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
