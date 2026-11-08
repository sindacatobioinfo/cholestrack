# home/forms.py
"""
Forms for the admin center user management CRUD.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from users.models import UserRole


class AdminUserCreateForm(forms.Form):
    """Form for admin-initiated user creation."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'user@example.com'}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    role = forms.ChoiceField(
        choices=UserRole.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='Account active',
        help_text='Inactive users cannot log in.',
    )
    email_confirmed = forms.BooleanField(
        required=False,
        initial=True,
        label='Mark email as verified',
        help_text='Skip email verification step for admin-created accounts.',
    )
    confirm_role = forms.BooleanField(
        required=False,
        initial=True,
        label='Confirm role immediately',
        help_text='Grants access without waiting for separate admin approval.',
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned_data


class AdminUserEditForm(forms.Form):
    """Form for editing an existing user's basic data."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user  # used in uniqueness validation

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username__iexact=username)
        if self._user:
            qs = qs.exclude(pk=self._user.pk)
        if qs.exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self._user:
            qs = qs.exclude(pk=self._user.pk)
        if qs.exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email


class AdminUserResetPasswordForm(forms.Form):
    """Form for admin-initiated password reset."""

    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'Passwords do not match.')
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as exc:
                self.add_error('new_password1', exc)
        return cleaned_data
