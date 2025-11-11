# users/forms.py
"""
Forms for user registration and email verification.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings


class RegistrationForm(UserCreationForm):
    """
    Extended user creation form with email validation for institutional domains.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.name@burlo.trieste.it'
        }),
        help_text='Please use your institutional email address (@burlo.trieste.it or @units.it)'
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        """Validate that email is from an allowed institutional domain"""
        email = self.cleaned_data.get('email')
        if email:
            domain = email.split('@')[-1].lower()
            if domain not in settings.ALLOWED_EMAIL_DOMAINS:
                allowed_domains = ', '.join(f'@{d}' for d in settings.ALLOWED_EMAIL_DOMAINS)
                raise forms.ValidationError(
                    f'Please use an institutional email address. Allowed domains: {allowed_domains}'
                )

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('This email address is already registered.')

        return email


class ResendVerificationForm(forms.Form):
    """Form for resending verification email"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@burlo.trieste.it'
        }),
        help_text='Enter the email address you used to register'
    )
