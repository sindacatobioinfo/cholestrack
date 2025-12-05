# users/urls.py
from django.urls import path
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from .views import (
    CholestrackLoginView,
    CholestrackPasswordResetView,
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

    # Password Reset
    path('password-reset/',
         CholestrackPasswordResetView.as_view(),
         name='password_reset'),

    path('password-reset/done/',
         PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ),
         name='password_reset_confirm'),

    path('password-reset-complete/',
         PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]