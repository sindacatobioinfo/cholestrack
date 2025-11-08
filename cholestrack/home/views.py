# home/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages

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