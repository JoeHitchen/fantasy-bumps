from django.urls import path, include
from django.views.generic.base import TemplateView

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path(
        '',
        TemplateView.as_view(template_name = 'core/base.html'),
        name = 'index',
    ),
]
