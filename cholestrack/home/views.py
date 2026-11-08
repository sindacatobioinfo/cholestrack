# home/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, BooleanField, ExpressionWrapper
from users.models import UserRole, RoleChangeRequest, EmailVerification
from users.decorators import role_required
from samples.models import Patient
from django.core.paginator import Paginator
from django.utils.crypto import get_random_string

from .forms import AdminUserCreateForm, AdminUserEditForm, AdminUserResetPasswordForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_last_active_confirmed_admin(user):
    """
    Returns True when *user* is currently the only active, confirmed ADMIN.
    Used to block actions that would leave the system without an admin.
    """
    try:
        role = user.role
        if role.role != 'ADMIN' or not role.confirmed_by_admin or not user.is_active:
            return False
    except Exception:
        return False
    count = UserRole.objects.filter(
        role='ADMIN',
        confirmed_by_admin=True,
        user__is_active=True,
    ).count()
    return count <= 1


def _admin_guard(request, target_user, action='modify'):
    """
    Enforce standard safeguards for mutating actions on another user.

    Returns an error message string if a safeguard fires, otherwise None.
    Caller should add the message and redirect when a string is returned.

    Self-action rules per requirements:
      - Editing basic info (action='edit') and password reset are ALLOWED for self.
      - Delete, deactivate, demote, revoke_role_confirm are BLOCKED for self.
    """
    # Dangerous actions are blocked on self
    SELF_BLOCKED_ACTIONS = ('delete', 'deactivate', 'demote', 'revoke_role_confirm')
    if action in SELF_BLOCKED_ACTIONS and target_user.pk == request.user.pk:
        return f'You cannot {action} your own account.'

    # Non-superuser cannot touch a superuser account (all actions)
    if target_user.is_superuser and not request.user.is_superuser:
        return 'Only a superuser can modify another superuser account.'

    # For destructive actions, block if target is the last active admin
    if action in SELF_BLOCKED_ACTIONS:
        if _is_last_active_confirmed_admin(target_user):
            return (
                'Cannot perform this action: this is the last active confirmed administrator. '
                'Promote another user to Administrator first.'
            )

    return None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
@never_cache
def dashboard(request):
    """
    Main dashboard view that serves as the navigation hub after user login.
    """
    profile = request.user.profile

    if not profile.profile_completed:
        messages.info(request, 'Please complete your profile to access all features.')
        return redirect('profile:create_profile')

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'home/dashboard.html', context)


@login_required
def redirect_to_samples(request):
    return redirect('samples:sample_list')


# ---------------------------------------------------------------------------
# Admin Center — overview dashboard
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_center(request):
    """Admin center dashboard with system-wide statistics."""
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    pending_email_verifications = EmailVerification.objects.filter(email_confirmed=False).count()
    pending_role_confirmations = UserRole.objects.filter(confirmed_by_admin=False).count()
    confirmed_roles = UserRole.objects.filter(confirmed_by_admin=True).count()
    pending_role_changes = RoleChangeRequest.objects.filter(status='PENDING').count()
    role_distribution = UserRole.objects.values('role').annotate(count=Count('role'))

    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_registrations = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    total_patients = Patient.objects.count()

    recent_users = User.objects.select_related(
        'role', 'email_verification'
    ).order_by('-date_joined')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'pending_email_verifications': pending_email_verifications,
        'pending_role_confirmations': pending_role_confirmations,
        'confirmed_roles': confirmed_roles,
        'pending_role_changes': pending_role_changes,
        'role_distribution': role_distribution,
        'recent_registrations': recent_registrations,
        'total_patients': total_patients,
        'recent_users': recent_users,
    }
    return render(request, 'home/admin_center/dashboard.html', context)


# ---------------------------------------------------------------------------
# Admin Center — user list
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_users(request):
    """
    User management page — list all users with filtering, search, and
    per-row action buttons. Users are annotated with has_role /
    has_email_verification flags so the template can avoid hasattr.
    """
    status_filter = request.GET.get('status', 'all')
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')

    users = User.objects.select_related(
        'role', 'email_verification', 'profile'
    ).annotate(
        has_role=ExpressionWrapper(
            Q(role__isnull=False), output_field=BooleanField()
        ),
        has_email_verification=ExpressionWrapper(
            Q(email_verification__isnull=False), output_field=BooleanField()
        ),
    )

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'pending_email':
        users = users.filter(email_verification__email_confirmed=False)
    elif status_filter == 'pending_role':
        users = users.filter(role__confirmed_by_admin=False)

    if role_filter != 'all':
        users = users.filter(role__role=role_filter)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    users = users.order_by('-date_joined')

    paginator = Paginator(users, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'search_query': search_query,
        'role_choices': UserRole.ROLE_CHOICES,
    }
    return render(request, 'home/admin_center/users.html', context)


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Create
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_user_create(request):
    """Admin creates a new user account with role and verification flags."""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = User.objects.create_user(
                username=cd['username'],
                email=cd['email'],
                password=cd['password1'],
                first_name=cd.get('first_name', ''),
                last_name=cd.get('last_name', ''),
                is_active=cd.get('is_active', True),
            )

            # EmailVerification
            email_confirmed = cd.get('email_confirmed', True)
            EmailVerification.objects.create(
                user=user,
                verification_token=get_random_string(64),
                email_confirmed=email_confirmed,
                confirmed_at=timezone.now() if email_confirmed else None,
            )

            # UserRole
            confirm_role = cd.get('confirm_role', True)
            UserRole.objects.create(
                user=user,
                role=cd['role'],
                assigned_by=request.user,
                confirmed_by_admin=confirm_role,
                confirmed_at=timezone.now() if confirm_role else None,
            )

            messages.success(
                request,
                f'User "{user.username}" created successfully.',
            )
            return redirect('home:admin_user_detail', user_id=user.pk)
    else:
        form = AdminUserCreateForm(initial={'is_active': True, 'email_confirmed': True, 'confirm_role': True})

    return render(request, 'home/admin_center/user_create.html', {'form': form})


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Read (detail)
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_user_detail(request, user_id):
    """Detail view for a single user: data, role, status, role change history."""
    target = get_object_or_404(
        User.objects.select_related('role', 'email_verification', 'profile'),
        pk=user_id,
    )
    role_requests = RoleChangeRequest.objects.filter(
        user=target
    ).order_by('-created_at')[:10]

    # Safe-access helpers (the template still uses them, but we pass flags too)
    try:
        user_role = target.role
    except Exception:
        user_role = None

    try:
        email_verification = target.email_verification
    except Exception:
        email_verification = None

    context = {
        'target': target,
        'user_role': user_role,
        'email_verification': email_verification,
        'role_requests': role_requests,
        'role_choices': UserRole.ROLE_CHOICES,
        'is_self': target.pk == request.user.pk,
        'is_last_admin': _is_last_active_confirmed_admin(target),
    }
    return render(request, 'home/admin_center/user_detail.html', context)


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Update (edit basic data)
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_user_edit(request, user_id):
    """Edit basic data for a user (username, email, first/last name)."""
    target = get_object_or_404(User, pk=user_id)

    guard = _admin_guard(request, target, action='edit')
    if guard:
        messages.error(request, guard)
        return redirect('home:admin_user_detail', user_id=user_id)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, user=target)
        if form.is_valid():
            cd = form.cleaned_data
            target.username = cd['username']
            target.email = cd['email']
            target.first_name = cd.get('first_name', '')
            target.last_name = cd.get('last_name', '')
            target.save()
            messages.success(request, f'User "{target.username}" updated successfully.')
            return redirect('home:admin_user_detail', user_id=user_id)
    else:
        form = AdminUserEditForm(
            initial={
                'username': target.username,
                'email': target.email,
                'first_name': target.first_name,
                'last_name': target.last_name,
            },
            user=target,
        )

    return render(request, 'home/admin_center/user_edit.html', {
        'form': form,
        'target': target,
    })


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Toggle active
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
@require_POST
def admin_user_toggle_active(request, user_id):
    """Activate or deactivate a user account."""
    target = get_object_or_404(User, pk=user_id)

    action = 'deactivate' if target.is_active else 'modify'
    guard = _admin_guard(request, target, action=action)
    if guard:
        messages.error(request, guard)
        return redirect('home:admin_user_detail', user_id=user_id)

    target.is_active = not target.is_active
    target.save()
    state = 'activated' if target.is_active else 'deactivated'
    messages.success(request, f'User "{target.username}" has been {state}.')
    return redirect('home:admin_user_detail', user_id=user_id)


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Toggle role confirmation
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
@require_POST
def admin_user_toggle_role_confirm(request, user_id):
    """Confirm or revoke admin confirmation of a user's role."""
    target = get_object_or_404(User, pk=user_id)
    try:
        user_role = target.role
    except Exception:
        messages.error(request, 'This user has no role assigned.')
        return redirect('home:admin_user_detail', user_id=user_id)

    if user_role.confirmed_by_admin:
        # Revoking — apply last-admin guard
        guard = _admin_guard(request, target, action='revoke_role_confirm')
        if guard:
            messages.error(request, guard)
            return redirect('home:admin_user_detail', user_id=user_id)
        user_role.confirmed_by_admin = False
        user_role.confirmed_at = None
        user_role.save()
        messages.success(request, f'Role confirmation revoked for "{target.username}".')
    else:
        user_role.confirmed_by_admin = True
        user_role.confirmed_at = timezone.now()
        user_role.save()
        messages.success(request, f'Role confirmed for "{target.username}".')

    return redirect('home:admin_user_detail', user_id=user_id)


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Mark email verified
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
@require_POST
def admin_user_mark_email_verified(request, user_id):
    """Force-mark a user's email as verified."""
    target = get_object_or_404(User, pk=user_id)
    ev, created = EmailVerification.objects.get_or_create(
        user=target,
        defaults={'verification_token': get_random_string(64)},
    )
    if not ev.email_confirmed:
        ev.email_confirmed = True
        ev.confirmed_at = timezone.now()
        ev.save()
        messages.success(request, f'Email marked as verified for "{target.username}".')
    else:
        messages.info(request, f'Email was already verified for "{target.username}".')
    return redirect('home:admin_user_detail', user_id=user_id)


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Reset password
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_user_reset_password(request, user_id):
    """Admin sets a new password for another user."""
    target = get_object_or_404(User, pk=user_id)

    guard = _admin_guard(request, target, action='reset the password of')
    if guard:
        messages.error(request, guard)
        return redirect('home:admin_user_detail', user_id=user_id)

    if request.method == 'POST':
        form = AdminUserResetPasswordForm(request.POST)
        if form.is_valid():
            target.set_password(form.cleaned_data['new_password1'])
            target.save()
            messages.success(
                request,
                f'Password reset successfully for "{target.username}".',
            )
            return redirect('home:admin_user_detail', user_id=user_id)
    else:
        form = AdminUserResetPasswordForm()

    return render(request, 'home/admin_center/user_reset_password.html', {
        'form': form,
        'target': target,
    })


# ---------------------------------------------------------------------------
# Admin Center — CRUD: Delete
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_user_delete(request, user_id):
    """
    GET: Confirmation page.
    POST: Hard delete the user.
    Callers should prefer deactivation over deletion; the UI surfaces this.
    """
    target = get_object_or_404(User, pk=user_id)

    guard = _admin_guard(request, target, action='delete')
    if guard:
        messages.error(request, guard)
        return redirect('home:admin_user_detail', user_id=user_id)

    if request.method == 'POST':
        # Double-check safeguard on POST as well
        guard = _admin_guard(request, target, action='delete')
        if guard:
            messages.error(request, guard)
            return redirect('home:admin_user_detail', user_id=user_id)

        username = target.username
        target.delete()
        messages.success(request, f'User "{username}" has been permanently deleted.')
        return redirect('home:admin_users')

    return render(request, 'home/admin_center/user_delete.html', {'target': target})


# ---------------------------------------------------------------------------
# Admin Center — existing: confirm role (kept for backward compat)
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_confirm_role(request, user_id):
    """Confirm a user's role (backward-compatible endpoint)."""
    user = get_object_or_404(User, id=user_id)
    try:
        user_role = user.role
    except Exception:
        messages.error(request, 'This user has no role to confirm.')
        return redirect('home:admin_users')

    if request.method == 'POST':
        if not user_role.confirmed_by_admin:
            user_role.confirmed_by_admin = True
            user_role.confirmed_at = timezone.now()
            user_role.save()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = 'Your Cholestrack Role Has Been Confirmed'
                message = (
                    f'Hello {user.first_name},\n\n'
                    f'Your role assignment ({user_role.get_role_display()}) has been '
                    f'confirmed by an administrator.\n\nYou now have full access.\n\n'
                    f'Best regards,\nCholestrack Admin Team'
                )
                send_mail(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL, [user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(request, f'Role confirmed for user {user.username}.')
        else:
            messages.info(request, f'Role for user {user.username} was already confirmed.')

        return redirect('home:admin_users')

    return redirect('home:admin_users')


# ---------------------------------------------------------------------------
# Admin Center — existing: change user role
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_change_user_role(request, user_id):
    """Change a user's role with safeguards."""
    user = get_object_or_404(User, id=user_id)
    try:
        user_role = user.role
    except Exception:
        messages.error(request, 'This user has no role to change.')
        return redirect('home:admin_users')

    if request.method == 'POST':
        new_role = request.POST.get('role')

        if new_role not in dict(UserRole.ROLE_CHOICES):
            messages.error(request, 'Invalid role selected.')
            return redirect('home:admin_users')

        # Guard: demoting the last admin is not allowed
        if user_role.role == 'ADMIN' and new_role != 'ADMIN':
            guard = _admin_guard(request, user, action='demote')
            if guard:
                messages.error(request, guard)
                return redirect('home:admin_users')

        # Guard: self-action
        if user.pk == request.user.pk:
            messages.error(request, 'You cannot change your own role.')
            return redirect('home:admin_users')

        old_role = user_role.role
        user_role.role = new_role
        user_role.assigned_by = request.user
        user_role.assigned_at = timezone.now()
        user_role.save()

        messages.success(
            request,
            f'Role for {user.username} changed from '
            f'{dict(UserRole.ROLE_CHOICES)[old_role]} to '
            f'{dict(UserRole.ROLE_CHOICES)[new_role]}.',
        )

        return redirect('home:admin_users')

    return redirect('home:admin_users')


# ---------------------------------------------------------------------------
# Admin Center — role change requests
# ---------------------------------------------------------------------------

@login_required
@role_required(['ADMIN'])
def admin_role_requests(request):
    """View and manage role change requests."""
    status_filter = request.GET.get('status', 'pending')
    requests_qs = RoleChangeRequest.objects.select_related('user', 'reviewed_by').all()

    if status_filter == 'pending':
        requests_qs = requests_qs.filter(status='PENDING')
    elif status_filter == 'approved':
        requests_qs = requests_qs.filter(status='APPROVED')
    elif status_filter == 'denied':
        requests_qs = requests_qs.filter(status='DENIED')

    requests_qs = requests_qs.order_by('-created_at')
    paginator = Paginator(requests_qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'home/admin_center/role_requests.html', context)


@login_required
@role_required(['ADMIN'])
def admin_approve_role_request(request, request_id):
    """Approve a role change request."""
    role_request = get_object_or_404(RoleChangeRequest, id=request_id)

    if request.method == 'POST':
        if role_request.status == 'PENDING':
            try:
                user_role = role_request.user.role
            except Exception:
                messages.error(request, 'Target user has no role record.')
                return redirect('home:admin_role_requests')

            old_role = user_role.role

            # Guard: demoting the last active confirmed admin is not allowed
            if old_role == 'ADMIN' and role_request.requested_role != 'ADMIN':
                guard = _admin_guard(request, role_request.user, action='demote')
                if guard:
                    messages.error(request, guard)
                    return redirect('home:admin_role_requests')

            user_role.role = role_request.requested_role
            user_role.assigned_by = request.user
            user_role.assigned_at = timezone.now()
            user_role.save()

            role_request.status = 'APPROVED'
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.admin_notes = request.POST.get('admin_notes', '')
            role_request.save()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    'Your Role Change Request Has Been Approved',
                    (
                        f'Hello {role_request.user.first_name},\n\n'
                        f'Your role change request has been approved.\n'
                        f'New role: {dict(UserRole.ROLE_CHOICES)[role_request.requested_role]}\n\n'
                        f'Best regards,\nCholestrack Admin Team'
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [role_request.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(
                request,
                f'Role change request approved for {role_request.user.username}.',
            )
        else:
            messages.warning(request, 'This request has already been processed.')

        return redirect('home:admin_role_requests')

    return redirect('home:admin_role_requests')


@login_required
@role_required(['ADMIN'])
def admin_deny_role_request(request, request_id):
    """Deny a role change request."""
    role_request = get_object_or_404(RoleChangeRequest, id=request_id)

    if request.method == 'POST':
        if role_request.status == 'PENDING':
            role_request.status = 'DENIED'
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.admin_notes = request.POST.get('admin_notes', '')
            role_request.save()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    'Your Role Change Request Has Been Denied',
                    (
                        f'Hello {role_request.user.first_name},\n\n'
                        f'Your role change request has been denied.\n'
                        f'Admin notes: {role_request.admin_notes or "None"}\n\n'
                        f'Best regards,\nCholestrack Admin Team'
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [role_request.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(
                request,
                f'Role change request denied for {role_request.user.username}.',
            )
        else:
            messages.warning(request, 'This request has already been processed.')

        return redirect('home:admin_role_requests')

    return redirect('home:admin_role_requests')
