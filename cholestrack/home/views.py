# home/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from users.models import UserRole, RoleChangeRequest, EmailVerification
from users.decorators import role_required
from samples.models import Patient
from django.core.paginator import Paginator

@login_required
@never_cache
def dashboard(request):
    """
    Main dashboard view that serves as the navigation hub after user login.
    
    This view presents users with:
    - Quick access to their profile information
    - Navigation to available tools (samples management, future features)
    - Summary statistics about their data
    - Recent activity or notifications
    """
    # Check if the user has completed their profile
    profile = request.user.profile
    
    if not profile.profile_completed:
        messages.info(request, 'Please complete your profile to access all features.')
        return redirect('profile:create_profile')
    
    # Gather dashboard context
    context = {
        'user': request.user,
        'profile': profile,
    }
    
    return render(request, 'home/dashboard.html', context)


@login_required
def redirect_to_samples(request):
    """
    Convenience redirect function to navigate to the samples management interface.
    This can be expanded in the future to check permissions before redirecting.
    """
    return redirect('samples:sample_list')


# Admin Center Views

@login_required
@role_required(['ADMIN'])
def admin_center(request):
    """
    Admin center dashboard showing system overview and statistics.
    Only accessible to users with ADMIN role.
    """
    # Get statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    pending_email_verifications = EmailVerification.objects.filter(email_confirmed=False).count()

    # Role confirmations
    pending_role_confirmations = UserRole.objects.filter(confirmed_by_admin=False).count()
    confirmed_roles = UserRole.objects.filter(confirmed_by_admin=True).count()

    # Role change requests
    pending_role_changes = RoleChangeRequest.objects.filter(status='PENDING').count()

    # Role distribution
    role_distribution = UserRole.objects.values('role').annotate(count=Count('role'))

    # Recent registrations (last 30 days)
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_registrations = User.objects.filter(date_joined__gte=thirty_days_ago).count()

    # Total patients
    total_patients = Patient.objects.count()

    # Recent users (last 10)
    recent_users = User.objects.select_related('role', 'email_verification').order_by('-date_joined')[:10]

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


@login_required
@role_required(['ADMIN'])
def admin_users(request):
    """
    User management page - list all users with filtering and search.
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    users = User.objects.select_related('role', 'email_verification', 'profile').all()

    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'pending_email':
        users = users.filter(email_verification__email_confirmed=False)
    elif status_filter == 'pending_role':
        users = users.filter(role__confirmed_by_admin=False)

    # Apply role filter
    if role_filter != 'all':
        users = users.filter(role__role=role_filter)

    # Apply search
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Order by date joined (newest first)
    users = users.order_by('-date_joined')

    # Pagination
    paginator = Paginator(users, 25)  # 25 users per page
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


@login_required
@role_required(['ADMIN'])
def admin_confirm_role(request, user_id):
    """
    Confirm a user's role.
    """
    user = get_object_or_404(User, id=user_id)
    user_role = user.role

    if request.method == 'POST':
        if not user_role.confirmed_by_admin:
            user_role.confirmed_by_admin = True
            user_role.confirmed_at = timezone.now()
            user_role.save()

            # Send confirmation email to user
            try:
                from django.core.mail import send_mail
                from django.conf import settings

                subject = 'Your Cholestrack Role Has Been Confirmed'
                message = f"""
Hello {user.first_name},

Your role assignment has been confirmed by an administrator.

Account Details:
- Username: {user.username}
- Role: {user_role.get_role_display()}
- Confirmed At: {user_role.confirmed_at.strftime('%Y-%m-%d %H:%M:%S')}

You now have full access to the Cholestrack platform.

Best regards,
Cholestrack Admin Team
"""

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True
                )
            except:
                pass

            messages.success(request, f'Role confirmed for user {user.username}.')
        else:
            messages.info(request, f'Role for user {user.username} was already confirmed.')

        return redirect('home:admin_users')

    return redirect('home:admin_users')


@login_required
@role_required(['ADMIN'])
def admin_change_user_role(request, user_id):
    """
    Change a user's role.
    """
    user = get_object_or_404(User, id=user_id)
    user_role = user.role

    if request.method == 'POST':
        new_role = request.POST.get('role')

        if new_role in dict(UserRole.ROLE_CHOICES):
            old_role = user_role.role
            user_role.role = new_role
            user_role.assigned_by = request.user
            user_role.assigned_at = timezone.now()
            user_role.save()

            messages.success(
                request,
                f'Role for {user.username} changed from {dict(UserRole.ROLE_CHOICES)[old_role]} '
                f'to {dict(UserRole.ROLE_CHOICES)[new_role]}.'
            )
        else:
            messages.error(request, 'Invalid role selected.')

        return redirect('home:admin_users')

    return redirect('home:admin_users')


@login_required
@role_required(['ADMIN'])
def admin_role_requests(request):
    """
    View and manage role change requests.
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')

    # Base queryset
    requests_qs = RoleChangeRequest.objects.select_related('user', 'reviewed_by').all()

    # Apply status filter
    if status_filter == 'pending':
        requests_qs = requests_qs.filter(status='PENDING')
    elif status_filter == 'approved':
        requests_qs = requests_qs.filter(status='APPROVED')
    elif status_filter == 'denied':
        requests_qs = requests_qs.filter(status='DENIED')

    # Order by created date (newest first)
    requests_qs = requests_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(requests_qs, 20)  # 20 requests per page
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
    """
    Approve a role change request.
    """
    role_request = get_object_or_404(RoleChangeRequest, id=request_id)

    if request.method == 'POST':
        if role_request.status == 'PENDING':
            # Update the user's role
            user_role = role_request.user.role
            old_role = user_role.role
            user_role.role = role_request.requested_role
            user_role.assigned_by = request.user
            user_role.assigned_at = timezone.now()
            user_role.save()

            # Update request status
            role_request.status = 'APPROVED'
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.admin_notes = request.POST.get('admin_notes', '')
            role_request.save()

            # Send approval email
            try:
                from django.core.mail import send_mail
                from django.conf import settings

                subject = 'Your Role Change Request Has Been Approved'
                message = f"""
Hello {role_request.user.first_name},

Your role change request has been approved.

Request Details:
- Previous Role: {dict(UserRole.ROLE_CHOICES)[old_role]}
- New Role: {dict(UserRole.ROLE_CHOICES)[role_request.requested_role]}
- Approved By: {request.user.get_full_name() or request.user.username}
- Approved At: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Your new role is now active.

Best regards,
Cholestrack Admin Team
"""

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [role_request.user.email],
                    fail_silently=True
                )
            except:
                pass

            messages.success(
                request,
                f'Role change request approved for {role_request.user.username}.'
            )
        else:
            messages.warning(request, 'This request has already been processed.')

        return redirect('home:admin_role_requests')

    return redirect('home:admin_role_requests')


@login_required
@role_required(['ADMIN'])
def admin_deny_role_request(request, request_id):
    """
    Deny a role change request.
    """
    role_request = get_object_or_404(RoleChangeRequest, id=request_id)

    if request.method == 'POST':
        if role_request.status == 'PENDING':
            # Update request status
            role_request.status = 'DENIED'
            role_request.reviewed_by = request.user
            role_request.reviewed_at = timezone.now()
            role_request.admin_notes = request.POST.get('admin_notes', '')
            role_request.save()

            # Send denial email
            try:
                from django.core.mail import send_mail
                from django.conf import settings

                subject = 'Your Role Change Request Has Been Denied'
                admin_notes = role_request.admin_notes or 'No additional notes provided.'

                message = f"""
Hello {role_request.user.first_name},

Your role change request has been denied.

Request Details:
- Requested Role: {dict(UserRole.ROLE_CHOICES)[role_request.requested_role]}
- Reviewed By: {request.user.get_full_name() or request.user.username}
- Reviewed At: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Admin Notes:
{admin_notes}

If you have questions about this decision, please contact the administrator.

Best regards,
Cholestrack Admin Team
"""

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [role_request.user.email],
                    fail_silently=True
                )
            except:
                pass

            messages.success(
                request,
                f'Role change request denied for {role_request.user.username}.'
            )
        else:
            messages.warning(request, 'This request has already been processed.')

        return redirect('home:admin_role_requests')

    return redirect('home:admin_role_requests')