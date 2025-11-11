# users/decorators.py
"""
Permission decorators for Role-Based Access Control (RBAC).
"""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def role_required(allowed_roles):
    """
    Decorator to restrict view access based on user role.

    Usage:
        @role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
        def my_view(request):
            ...

    Args:
        allowed_roles: List of role codes (e.g., ['ADMIN', 'MANAGER'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, 'You must be logged in to access this page.')
                return redirect('users:login')

            # Check if user has email verified
            if not hasattr(request.user, 'email_verification') or \
               not request.user.email_verification.email_confirmed:
                messages.error(
                    request,
                    'You must verify your email address before accessing this page. '
                    'Please check your email for the verification link.'
                )
                return redirect('users:resend_verification')

            # Check if user has a role
            if not hasattr(request.user, 'role'):
                messages.error(
                    request,
                    'Your account does not have a role assigned. Please contact an administrator.'
                )
                return redirect('home:index')

            # Check if role is confirmed by admin
            if not request.user.role.confirmed_by_admin:
                messages.error(
                    request,
                    'Your role has not been confirmed by an administrator yet. '
                    'You will receive an email once your account is fully activated.'
                )
                return redirect('home:index')

            # Check if user's role is in allowed roles
            if request.user.role.role not in allowed_roles:
                messages.error(
                    request,
                    'You do not have permission to access this page. '
                    f'Required role: {", ".join(allowed_roles)}'
                )
                return redirect('samples:sample_list')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def email_verified_required(view_func):
    """
    Decorator to ensure user has verified their email before accessing views.

    Usage:
        @email_verified_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in.')
            return redirect('users:login')

        if not hasattr(request.user, 'email_verification') or \
           not request.user.email_verification.email_confirmed:
            messages.error(
                request,
                'You must verify your email address before accessing this page. '
                'Please check your email for the verification link.'
            )
            return redirect('users:resend_verification')

        return view_func(request, *args, **kwargs)
    return wrapper


def role_confirmed_required(view_func):
    """
    Decorator to ensure user has admin-confirmed role before accessing views.

    Usage:
        @role_confirmed_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in.')
            return redirect('users:login')

        if not hasattr(request.user, 'role'):
            messages.error(request, 'Your account does not have a role assigned.')
            return redirect('home:index')

        if not request.user.role.confirmed_by_admin:
            messages.error(
                request,
                'Your role has not been confirmed by an administrator yet.'
            )
            return redirect('home:index')

        return view_func(request, *args, **kwargs)
    return wrapper
