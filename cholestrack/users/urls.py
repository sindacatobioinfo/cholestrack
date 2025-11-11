# users/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CholestrackLoginView,
    register,
    verify_email,
    resend_verification,
    registration_complete
)

app_name = 'users'

urlpatterns = [
    # User Registration
    path('register/', register, name='register'),
    path('registration-complete/', registration_complete, name='registration_complete'),

    # Email Verification
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification, name='resend_verification'),

    # User Login
    path('login/', CholestrackLoginView.as_view(), name='login'),

    # User Logout (redirects to login page after logout)
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
]