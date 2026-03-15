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
    path('events/', views.EventsList.as_view(), name = 'events'),
    path('guide-rules/', views.RulesView.as_view(), name = 'rules'),
    path(
        'privacy/',
        views.RulesView.as_view(template_name = 'fantasy/privacy.html'),
        name = 'privacy',
    ),
    path('buy/', views.buy, name = 'buy'),
    path('sell/', views.sell, name = 'sell'),
    path('hire/', views.hire, name = 'hire'),
    path('fire/', views.fire, name = 'fire'),
    path('switch/<int:purchase_id>/', views.Switch.as_view(), name = 'switch'),
    path('market-hold/', views.market_hold, name = 'market-hold'),
    path('<slug:event_tag>/', include([
        path('men/', views.MarketView.as_view(), {'gender': Genders.MEN}, name = 'men'),
        path('women/', views.MarketView.as_view(), {'gender': Genders.WOMEN}, name = 'women'),
        path('leaderboard/', include(leaderboard_subpatterns)),
        path('teams/<team_name>/', views.TeamView.as_view(), name = 'team'),
        path(
            'guide-rules/',
            views.EventBase.as_view(template_name = 'fantasy/rules.html'),
            name = 'rules',
        ),
        path(
            'privacy/',
            views.EventBase.as_view(template_name = 'fantasy/privacy.html'),
            name = 'privacy',
        ),
        path('', views.EventView.as_view(), name = 'event'),
    ])),
    path('', views.IndexView.as_view(), name = 'index'),
]
