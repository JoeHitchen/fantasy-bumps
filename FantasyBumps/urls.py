from django.urls import path
from django.views.generic.base import TemplateView

from . import views


app_name = 'fantasybumps'
urlpatterns = [
    path('men/', views.MarketView.as_view(), {'gender': 'M'}, name = 'men'),
    path('women/', views.MarketView.as_view(), {'gender': 'W'}, name = 'women'),
    path('', views.IndexView.as_view(), name = 'index'),
]
