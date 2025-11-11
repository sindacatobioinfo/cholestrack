# profile/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import ProfileForm
from .models import UserProfile
from users.models import UserRole

@login_required
def create_profile(request):
    """
    View for users to complete their profile after registration.
    """
    profile = request.user.profile
    
    # If profile is already completed, redirect to edit view
    if profile.profile_completed:
        return redirect('profile:edit_profile')
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.profile_completed = True
            profile.save()
            messages.success(request, 'Your profile has been created successfully.')
            return redirect('home:dashboard')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        'title': 'Complete Your Profile'
    }
    return render(request, 'profile/create_profile.html', context)


@login_required
def edit_profile(request):
    """
    View for users to edit their existing profile.
    When role is changed, syncs with UserRole and notifies admin.
    """
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            # Check if role has changed
            old_role = profile.role
            new_profile = form.save()
            new_role = new_profile.role

            # If role changed, update UserRole and notify admin
            if old_role != new_role:
                # Get display names for messaging
                role_display_map = dict(UserProfile.ROLE_CHOICES)
                old_role_display = role_display_map.get(old_role, old_role)
                new_role_display = role_display_map.get(new_role, new_role)

                # Get or create UserRole for this user
                user_role, created = UserRole.objects.get_or_create(
                    user=request.user,
                    defaults={'role': new_role, 'confirmed_by_admin': False}
                )

                if not created:
                    # Update existing UserRole
                    user_role.role = new_role
                    user_role.confirmed_by_admin = False  # Require re-approval
                    user_role.confirmed_at = None
                    user_role.save()

                # Send notification email to admin
                _send_role_change_notification(request.user, old_role, new_role)

                messages.warning(
                    request,
                    f'Your role change request (from {old_role_display} to {new_role_display}) '
                    'has been sent to the administrator for approval.'
                )
            else:
                messages.success(request, 'Your profile has been updated successfully.')

            return redirect('home:dashboard')
    else:
        form = ProfileForm(instance=profile)

    context = {
        'form': form,
        'title': 'Edit Your Profile'
    }
    return render(request, 'profile/edit_profile.html', context)


def _send_role_change_notification(user, old_role, new_role):
    """
    Send email notification to admin when user requests role change.
    """
    # Map role codes to display names
    role_display_map = dict(UserProfile.ROLE_CHOICES)
    old_role_display = role_display_map.get(old_role, old_role)
    new_role_display = role_display_map.get(new_role, new_role)

    subject = f'Role Change Request: {user.username}'

    # Prepare email context
    context = {
        'user': user,
        'old_role': old_role_display,
        'new_role': new_role_display,
        'admin_url': f'{settings.SITE_DOMAIN}/admin/users/userrole/',
    }

    # Render HTML email
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; }}
            .button {{ display: inline-block; padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            .info {{ background-color: #fff; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Role Change Request</h2>
            </div>
            <div class="content">
                <p>A user has requested a role change:</p>
                <div class="info">
                    <p><strong>User:</strong> {user.username}</p>
                    <p><strong>Email:</strong> {user.email}</p>
                    <p><strong>Full Name:</strong> {user.profile.full_name or 'N/A'}</p>
                </div>
                <div class="info">
                    <p><strong>Previous Role:</strong> {old_role_display}</p>
                    <p><strong>Requested Role:</strong> {new_role_display}</p>
                </div>
                <p>Please review and approve or deny this role change request in the admin panel:</p>
                <p style="text-align: center;">
                    <a href="{context.get('admin_url', '#')}" class="button">Review in Admin Panel</a>
                </p>
            </div>
            <div style="text-align: center; color: #6c757d; font-size: 12px; padding: 20px;">
                <p>This is an automated message from Cholestrack RBAC System</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_message = f"""
Role Change Request

A user has requested a role change:

User: {user.username}
Email: {user.email}
Full Name: {user.profile.full_name or 'N/A'}

Previous Role: {old_role_display}
Requested Role: {new_role_display}

Please review and approve or deny this role change request in the admin panel.
    """

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send role change notification email: {e}")