from django.urls import path, include

from .constants import Genders
from . import views


app_name = 'fantasy'

leaderboard_subpatterns = [
    path(
        'men/',
        views.LeaderboardView.as_view(),
        {'gender': Genders.MEN},
        name = 'leaderboard_men',
    ),
    path(
        'women/',
        views.LeaderboardView.as_view(),
        {'gender': Genders.WOMEN},
        name = 'leaderboard_women',
    ),
    path(
        '',
        views.LeaderboardView.as_view(),
        name = 'leaderboard',
    ),
]

urlpatterns = [
    path(
        'guide-rules/',
        views.IndexView.as_view(template_name = 'fantasy/rules.html'),
        name = 'rules',
    ),
    path('buy/', views.buy, name = 'buy'),
    path('sell/', views.sell, name = 'sell'),
    path('switch/<int:purchase_id>/', views.Switch.as_view(), name = 'switch'),
    path('<slug:event_tag>/', include([
        path('men/', views.MarketView.as_view(), {'gender': Genders.MEN}, name = 'men'),
        path('women/', views.MarketView.as_view(), {'gender': Genders.WOMEN}, name = 'women'),
        path('leaderboard/', include(leaderboard_subpatterns)),
        path('teams/<team_name>/', views.TeamView.as_view(), name = 'team'),
        path('', views.EventView.as_view(), name = 'event'),
    ])),
    path('', views.IndexView.as_view(), name = 'index'),
]
