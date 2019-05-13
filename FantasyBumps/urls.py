from django.urls import path

from .constants import genders
from . import views


app_name = 'fantasybumps'
urlpatterns = [
    path('men/', views.MarketView.as_view(), {'gender': genders.MENS}, name = 'men'),
    path('women/', views.MarketView.as_view(), {'gender': genders.WOMENS}, name = 'women'),
    path('buy/', views.BuyView.as_view(), name = 'buy'),
    path('sell/', views.SellView.as_view(), name = 'sell'),
    path('', views.IndexView.as_view(), name = 'index'),
]
