# home/urls.py
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('samples/', views.redirect_to_samples, name='goto_samples'),

    # Admin Center URLs
    path('admin-center/', views.admin_center, name='admin_center'),
    path('admin-center/users/', views.admin_users, name='admin_users'),
    path('admin-center/users/<int:user_id>/confirm-role/', views.admin_confirm_role, name='admin_confirm_role'),
    path('admin-center/users/<int:user_id>/change-role/', views.admin_change_user_role, name='admin_change_user_role'),
    path('admin-center/role-requests/', views.admin_role_requests, name='admin_role_requests'),
    path('admin-center/role-requests/<int:request_id>/approve/', views.admin_approve_role_request, name='admin_approve_role_request'),
    path('admin-center/role-requests/<int:request_id>/deny/', views.admin_deny_role_request, name='admin_deny_role_request'),
]