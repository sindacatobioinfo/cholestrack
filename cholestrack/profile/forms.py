# profile/forms.py
from django import forms
from .models import UserProfile

class ProfileForm(forms.ModelForm):
    """
    Form for creating and editing user profiles.
    """
    class Meta:
        model = UserProfile
        fields = ['full_name', 'role', 'team', 'institutional_email', 'phone', 'institution_id']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'team': forms.Select(attrs={'class': 'form-control'}),
            'institutional_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.name@burlo.trieste.it'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+39 XXX XXX XXXX'
            }),
            'institution_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your institutional ID'
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'role': 'Your Role',
            'team': 'Team/Department',
            'institutional_email': 'Institutional Email Address',
            'phone': 'Phone Number',
            'institution_id': 'Institution ID',
        }