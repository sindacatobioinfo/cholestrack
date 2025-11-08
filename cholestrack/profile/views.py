# profile/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm
from .models import UserProfile

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
    
    context = {
        'form': form,
        'title': 'Edit Your Profile'
    }
    return render(request, 'profile/edit_profile.html', context)