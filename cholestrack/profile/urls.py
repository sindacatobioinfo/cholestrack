# profile/urls.py
from django.urls import path
from . import views

app_name = 'profile'

urlpatterns = [
    path('create/', views.create_profile, name='create_profile'),
    path('edit/', views.edit_profile, name='edit_profile'),
    path('request-role-change/', views.request_role_change, name='request_role_change'),
]