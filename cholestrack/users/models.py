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
    - Data Manager: Create/Edit/View/Soft-delete (no hard delete)
    - Researcher: Create/Edit/View (no delete)
    - Clinician: View only (read-only access)
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('DATA_MANAGER', 'Data Manager'),
        ('RESEARCHER', 'Researcher'),
        ('CLINICIAN', 'Clinician'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='role'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLINICIAN',
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
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER']

    def can_edit_patient(self):
        """Check if user can edit patients"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER']

    def can_delete_patient(self):
        """Check if user can delete patients"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER']

    def can_create_file(self):
        """Check if user can register new file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER']

    def can_edit_file(self):
        """Check if user can edit file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER']

    def can_delete_file(self):
        """Check if user can delete file locations"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER']

    def can_download_files(self):
        """Check if user can download files"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER', 'CLINICIAN']

    def can_view_samples(self):
        """Check if user can view sample list"""
        return self.confirmed_by_admin and self.role in ['ADMIN', 'DATA_MANAGER', 'RESEARCHER', 'CLINICIAN']


class RoleChangeRequest(models.Model):
    """
    Tracks user requests to change their role.
    Requires admin approval before role is updated.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_change_requests')
    current_role = models.CharField(max_length=20, choices=UserRole.ROLE_CHOICES)
    requested_role = models.CharField(max_length=20, choices=UserRole.ROLE_CHOICES)
    reason = models.TextField(
        verbose_name="Reason for Change",
        help_text="Please explain why you need this role change"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    # Admin review
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_role_changes'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Admin notes on this request")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Role Change Request"
        verbose_name_plural = "Role Change Requests"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.get_current_role_display()} → {self.get_requested_role_display()} ({self.get_status_display()})"

    def send_admin_notification(self):
        """
        Send email notification to all administrators about new role change request.
        """
        from django.core.mail import send_mail
        from django.conf import settings

        # Get all admin users
        admin_users = User.objects.filter(is_superuser=True, is_active=True)
        admin_emails = [user.email for user in admin_users if user.email]

        if not admin_emails:
            return

        try:
            current_role_display = dict(UserRole.ROLE_CHOICES).get(self.current_role, self.current_role)
            requested_role_display = dict(UserRole.ROLE_CHOICES).get(self.requested_role, self.requested_role)

            subject = f'CholesTrack - New Role Change Request from {self.user.username}'

            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #008080; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
        <h1 style="color: white; margin: 0;">Cholestrack Admin</h1>
        <p style="color: #e0f2f1; margin: 5px 0 0 0;">Role Change Request</p>
    </div>

    <div style="background-color: #ffffff; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
        <h2 style="color: #008080; margin-top: 0;">New Role Change Request</h2>

        <p>A user has requested a role change:</p>

        <div style="background-color: #f8f9fa; border-left: 4px solid #008080; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;">
                <strong>User:</strong> {self.user.username} ({self.user.first_name} {self.user.last_name})<br>
                <strong>Email:</strong> {self.user.email}<br>
                <strong>Current Role:</strong> {current_role_display}<br>
                <strong>Requested Role:</strong> {requested_role_display}<br>
                <strong>Request Date:</strong> {self.created_at.strftime("%B %d, %Y at %H:%M")}
            </p>
        </div>

        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;"><strong>User's Reason:</strong></p>
            <p style="margin: 10px 0 0 0;">{self.reason}</p>
        </div>

        <p>Please review this request in the admin panel:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.SITE_DOMAIN}/admin/users/rolechangerequest/{self.id}/change/"
               style="background-color: #008080; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                Review Request in Admin Panel
            </a>
        </div>

        <p style="margin-top: 30px; font-size: 12px; color: #666;">
            This is an automated notification from the Cholestrack system.<br>
            IRCCS Materno Infantile Burlo Garofolo
        </p>
    </div>
</body>
</html>
"""

            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
                html_message=html_message
            )

        except Exception as e:
            print(f"Failed to send admin notification email: {str(e)}")
