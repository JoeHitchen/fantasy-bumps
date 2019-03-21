from django.urls import path

from external.constants import genders

from . import views


app_name = 'fantasybumps'
urlpatterns = [
    path('men/', views.MarketView.as_view(), {'gender': genders.MENS}, name = 'men'),
    path('women/', views.MarketView.as_view(), {'gender': genders.WOMENS}, name = 'women'),
    path('', views.IndexView.as_view(), name = 'index'),
]
