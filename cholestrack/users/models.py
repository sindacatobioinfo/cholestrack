# users/models.py
"""
Users application models.

This application focuses exclusively on user authentication and account creation.
It leverages Django's built-in User model and authentication framework.

Extended user information is managed by the profile application through the UserProfile model.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta


class EmailVerification(models.Model):
    """
    Email verification model for new user registrations.
    Ensures users have valid institutional email addresses before activating accounts.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_verification'
    )
    email_confirmed = models.BooleanField(
        default=False,
        verbose_name="Email Confirmed"
    )
    verification_token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Verification Token"
    )
    token_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Token Created At"
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmed At"
    )

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def __str__(self):
        status = 'Verified' if self.email_confirmed else 'Pending'
        return f"{self.user.username} - {status}"

    def is_token_valid(self):
        """Check if verification token is still valid (24 hours expiration)"""
        expiration_time = self.token_created_at + timedelta(hours=24)
        return timezone.now() < expiration_time

    def generate_new_token(self):
        """Generate a new verification token"""
        self.verification_token = get_random_string(64)
        self.token_created_at = timezone.now()
        self.save()
        return self.verification_token


class UserRole(models.Model):
    """
    User role model for role-based access control (RBAC).
    Assigns roles to users and tracks admin confirmation status.

    Role Hierarchy (from highest to lowest):
    - Administrator: Full access to everything
    - Manager: Create/Edit/View/Soft-delete (no hard delete)
    - Researcher: Create/Edit/View (no delete)
    - Viewer: View only (read-only access)
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('RESEARCHER', 'Researcher'),
        ('VIEWER', 'Viewer'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='role'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='VIEWER',
        verbose_name="Role"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles',
        verbose_name="Assigned By",
        help_text="Administrator who assigned this role"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Assigned At"
    )
    confirmed_by_admin = models.BooleanField(
        default=False,
        verbose_name="Confirmed by Admin",
        help_text="Whether an administrator has confirmed this role assignment"
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmed At"
    )

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"

    def __str__(self):
        confirmed = " (Confirmed)" if self.confirmed_by_admin else " (Pending)"
        return f"{self.user.username} - {self.get_role_display()}{confirmed}"

    def can_create_patient(self):
        """Check if user can create patients"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_edit_patient(self):
        """Check if user can edit patients"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_delete_patient(self):
        """Check if user can delete patients"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER']

    def can_create_file(self):
        """Check if user can register new file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_edit_file(self):
        """Check if user can edit file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_delete_file(self):
        """Check if user can delete file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER']

    def can_download_files(self):
        """Check if user can download files"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER']

    def can_view_samples(self):
        """Check if user can view sample list"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER']
