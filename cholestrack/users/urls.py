# users/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CholestrackLoginView, register

app_name = 'users'

urlpatterns = [
    # User Registration
    path('register/', register, name='register'),
    
    # User Login
    path('login/', CholestrackLoginView.as_view(), name='login'),
    
    # User Logout (redirects to login page after logout)
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
]