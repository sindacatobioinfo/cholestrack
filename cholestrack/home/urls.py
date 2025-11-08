# home/urls.py
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('samples/', views.redirect_to_samples, name='goto_samples'),
]