# home/urls.py
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('samples/', views.redirect_to_samples, name='goto_samples'),

    # Admin Center — overview
    path('admin-center/', views.admin_center, name='admin_center'),

    # Admin Center — user list
    path('admin-center/users/', views.admin_users, name='admin_users'),

    # Admin Center — CRUD: Create
    path('admin-center/users/create/', views.admin_user_create, name='admin_user_create'),

    # Admin Center — CRUD: Read (detail)
    path('admin-center/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),

    # Admin Center — CRUD: Update
    path('admin-center/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('admin-center/users/<int:user_id>/reset-password/', views.admin_user_reset_password, name='admin_user_reset_password'),

    # Admin Center — CRUD: Toggle active / role-confirm / email verify
    path('admin-center/users/<int:user_id>/toggle-active/', views.admin_user_toggle_active, name='admin_user_toggle_active'),
    path('admin-center/users/<int:user_id>/toggle-role-confirm/', views.admin_user_toggle_role_confirm, name='admin_user_toggle_role_confirm'),
    path('admin-center/users/<int:user_id>/mark-email-verified/', views.admin_user_mark_email_verified, name='admin_user_mark_email_verified'),

    # Admin Center — CRUD: Delete
    path('admin-center/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),

    # Admin Center — existing endpoints (backward-compatible)
    path('admin-center/users/<int:user_id>/confirm-role/', views.admin_confirm_role, name='admin_confirm_role'),
    path('admin-center/users/<int:user_id>/change-role/', views.admin_change_user_role, name='admin_change_user_role'),

    # Admin Center — role change requests
    path('admin-center/role-requests/', views.admin_role_requests, name='admin_role_requests'),
    path('admin-center/role-requests/<int:request_id>/approve/', views.admin_approve_role_request, name='admin_approve_role_request'),
    path('admin-center/role-requests/<int:request_id>/deny/', views.admin_deny_role_request, name='admin_deny_role_request'),
]
