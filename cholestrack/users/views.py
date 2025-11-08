# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView

def register(request):
    """
    User registration view. Creates a new user account and redirects to profile creation.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile:create_profile')
    else:
        form = UserCreationForm()
        
    return render(request, 'users/register.html', {'form': form})


class CholestrackLoginView(DjangoLoginView):
    """
    Custom login view using Django's built-in authentication.
    """
    template_name = 'users/login.html'