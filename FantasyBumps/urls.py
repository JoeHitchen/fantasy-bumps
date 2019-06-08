from django.urls import path, include

from .constants import genders
from . import views


app_name = 'fantasybumps'
urlpatterns = [
    path('buy/', views.BuyView.as_view(), name = 'buy'),
    path('sell/', views.SellView.as_view(), name = 'sell'),
    path('<slug:event_tag>/', include([
        path('men/', views.MarketView.as_view(), {'gender': genders.MENS}, name = 'men'),
        path('women/', views.MarketView.as_view(), {'gender': genders.WOMENS}, name = 'women'),
        path('leaderboard/', views.LeaderboardView.as_view(), name = 'leaderboard'),
        path('', views.EventView.as_view(), name = 'event'),
    ])),
    path('', views.IndexView.as_view(), name = 'index'),
]
