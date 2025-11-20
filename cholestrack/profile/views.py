# profile/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import ProfileForm, RoleChangeRequestForm
from .models import UserProfile
from users.models import UserRole, RoleChangeRequest

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
    Note: Role changes are now handled through the role change request system.
    """
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('home:dashboard')
    else:
        form = ProfileForm(instance=profile)

    # Get user's current role for display
    try:
        user_role = UserRole.objects.get(user=request.user)
        current_role = user_role.get_role_display()
        role_confirmed = user_role.confirmed_by_admin
    except UserRole.DoesNotExist:
        current_role = 'No role assigned'
        role_confirmed = False

    # Check if user has pending role change requests
    pending_requests = RoleChangeRequest.objects.filter(
        user=request.user,
        status='PENDING'
    ).order_by('-created_at')

    context = {
        'form': form,
        'title': 'Edit Your Profile',
        'current_role': current_role,
        'role_confirmed': role_confirmed,
        'pending_requests': pending_requests,
    }
    return render(request, 'profile/edit_profile.html', context)


@login_required
def request_role_change(request):
    """
    View for users to request a role change.
    Creates a RoleChangeRequest that requires admin approval.
    """
    # Get user's current role
    try:
        user_role = UserRole.objects.get(user=request.user)
        current_role = user_role.role
        current_role_display = user_role.get_role_display()
    except UserRole.DoesNotExist:
        current_role = 'CLINICIAN'  # Default role
        current_role_display = 'Clinician'

    # Check if user already has a pending request
    pending_request = RoleChangeRequest.objects.filter(
        user=request.user,
        status='PENDING'
    ).first()

    if pending_request:
        messages.warning(
            request,
            f'You already have a pending role change request to {pending_request.get_requested_role_display()}. '
            'Please wait for admin review.'
        )
        return redirect('profile:edit_profile')

    if request.method == 'POST':
        form = RoleChangeRequestForm(request.POST)
        if form.is_valid():
            # Check if requested role is same as current role
            requested_role = form.cleaned_data['requested_role']
            if requested_role == current_role:
                messages.error(request, 'You already have this role.')
                return redirect('profile:edit_profile')

            # Create the role change request
            role_request = form.save(commit=False)
            role_request.user = request.user
            role_request.current_role = current_role
            role_request.save()

            # Send notification to admins
            role_request.send_admin_notification()

            messages.success(
                request,
                f'Your request to change from {current_role_display} to {role_request.get_requested_role_display()} '
                'has been submitted. An administrator will review your request.'
            )
            return redirect('profile:edit_profile')
    else:
        form = RoleChangeRequestForm()

    context = {
        'form': form,
        'title': 'Request Role Change',
        'current_role': current_role_display,
    }
    return render(request, 'profile/request_role_change.html', context)
