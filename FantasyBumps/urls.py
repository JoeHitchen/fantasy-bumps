from django.urls import path
from django.views.generic.base import TemplateView

from . import views


app_name = 'fantasybumps'
urlpatterns = [
    path('', views.IndexView.as_view(), name = 'index'),
]
