from django.urls import path, include

from .constants import genders
from . import views


app_name = 'fantasybumps'

leaderboard_subpatterns = [
    path(
        'men/',
        views.LeaderboardView.as_view(),
        {'gender': genders.MENS},
        name = 'leaderboard_men',
    ),
    path(
        'women/',
        views.LeaderboardView.as_view(),
        {'gender': genders.WOMENS},
        name = 'leaderboard_women',
    ),
    path(
        '',
        views.LeaderboardView.as_view(),
        name = 'leaderboard',
    ),
]

urlpatterns = [
    path('buy/', views.BuyView.as_view(), name = 'buy'),
    path('sell/', views.sell, name = 'sell'),
    path('<slug:event_tag>/', include([
        path('men/', views.MarketView.as_view(), {'gender': genders.MENS}, name = 'men'),
        path('women/', views.MarketView.as_view(), {'gender': genders.WOMENS}, name = 'women'),
        path('leaderboard/', include(leaderboard_subpatterns)),
        path('', views.EventView.as_view(), name = 'event'),
    ])),
    path('', views.IndexView.as_view(), name = 'index'),
]
