# profile/forms.py
from django import forms
from .models import UserProfile
from users.models import UserRole, RoleChangeRequest

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


class RoleChangeRequestForm(forms.ModelForm):
    """
    Form for users to request a role change.
    Requires admin approval before role is updated.
    """
    class Meta:
        model = RoleChangeRequest
        fields = ['requested_role', 'reason']
        widgets = {
            'requested_role': forms.Select(attrs={
                'class': 'form-control',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Please explain why you need this role change and how it will help your work.',
                'rows': 5
            }),
        }
        labels = {
            'requested_role': 'Requested Role',
            'reason': 'Reason for Role Change',
        }
        help_texts = {
            'reason': 'Provide a clear justification for why you need access to this role.',
        }