# users/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import EmailVerification, UserRole, RoleChangeRequest


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin interface for email verifications"""
    list_display = ['user', 'email_confirmed', 'token_created_at', 'confirmed_at']
    list_filter = ['email_confirmed', 'token_created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['verification_token', 'token_created_at', 'confirmed_at']

    def has_add_permission(self, request):
        """Prevent manual creation of email verifications"""
        return False


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """
    Admin interface for user roles with automatic welcome email on role confirmation.
    """
    list_display = ['user', 'role', 'confirmed_by_admin', 'assigned_at', 'confirmed_at']
    list_filter = ['role', 'confirmed_by_admin', 'assigned_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['assigned_at', 'confirmed_at', 'assigned_by']
    fields = ['user', 'role', 'confirmed_by_admin', 'assigned_by', 'assigned_at', 'confirmed_at']

    def save_model(self, request, obj, form, change):
        """
        Override save to send welcome email when role is confirmed by admin.
        """
        # Check if this is an update (not new creation)
        if change:
            # Check if confirmed_by_admin was just changed to True
            old_obj = UserRole.objects.get(pk=obj.pk)
            if not old_obj.confirmed_by_admin and obj.confirmed_by_admin:
                # Role was just confirmed
                obj.confirmed_at = timezone.now()

                # Send welcome email to user
                self._send_welcome_email(obj.user, obj.get_role_display())

        # If this is a new role assignment, set the assigned_by field
        if not change:
            obj.assigned_by = request.user

        super().save_model(request, obj, form, change)

    def _send_welcome_email(self, user, role_display):
        """
        Send welcome email to user after role confirmation.
        """
        try:
            # Create email subject
            subject = 'Welcome to Cholestrack - Your Account is Now Active!'

            # Create email body
            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #008080; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
        <h1 style="color: white; margin: 0;">Cholestrack</h1>
        <p style="color: #e0f2f1; margin: 5px 0 0 0;">Genomic Analysis Platform</p>
    </div>

    <div style="background-color: #ffffff; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
        <h2 style="color: #008080; margin-top: 0;">Welcome to Cholestrack!</h2>

        <p>Hello <strong>{user.first_name} {user.last_name}</strong>,</p>

        <p>Great news! Your Cholestrack account has been fully activated by our administrator.</p>

        <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;">
                <strong>Your Account Details:</strong><br>
                Username: <strong>{user.username}</strong><br>
                Email: <strong>{user.email}</strong><br>
                Role: <strong>{role_display}</strong>
            </p>
        </div>

        <p>You can now log in and access the genomic analysis platform:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="http://cholestrack.burlo.trieste.it/users/login/"
               style="background-color: #008080; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                Log In to Cholestrack
            </a>
        </div>

        <div style="background-color: #d1ecf1; border-left: 4px solid #0c5460; padding: 12px; margin: 20px 0;">
            <h4 style="margin-top: 0;">What You Can Do:</h4>
            <ul style="margin-bottom: 0;">
                <li>Access patient genomic analysis data</li>
                <li>Download genomic files (VCF, BAM, etc.)</li>
                <li>Filter and search through patient samples</li>
                <li>View detailed analysis reports</li>
            </ul>
        </div>

        <p>If you have any questions or need assistance, please contact the administrator.</p>

        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The Cholestrack Team</strong><br>
            IRCCS Materno Infantile Burlo Garofolo
        </p>
    </div>

    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-top: 20px;">
        <p style="font-size: 12px; color: #666; margin: 0; text-align: center;">
            For security reasons, please do not share your login credentials with anyone.
        </p>
    </div>
</body>
</html>
"""

            # Send email
            send_mail(
                subject,
                '',  # Plain text version (empty)
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=html_message
            )

        except Exception as e:
            # Log the error but don't fail the save
            print(f"Failed to send welcome email to {user.email}: {str(e)}")


@admin.register(RoleChangeRequest)
class RoleChangeRequestAdmin(admin.ModelAdmin):
    """
    Admin interface for role change requests with approval workflow.
    """
    list_display = ['user', 'current_role', 'requested_role', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'requested_role', 'created_at']
    search_fields = ['user__username', 'user__email', 'reason']
    readonly_fields = ['user', 'current_role', 'requested_role', 'reason', 'created_at', 'updated_at']
    fields = ['user', 'current_role', 'requested_role', 'reason', 'status', 'admin_notes', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        """
        Override save to update user role when request is approved.
        """
        # Check if this is an update and status changed to APPROVED
        if change:
            old_obj = RoleChangeRequest.objects.get(pk=obj.pk)
            if old_obj.status != 'APPROVED' and obj.status == 'APPROVED':
                # Request was just approved
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()

                # Update user's role
                try:
                    user_role = UserRole.objects.get(user=obj.user)
                    user_role.role = obj.requested_role
                    user_role.confirmed_by_admin = True
                    user_role.confirmed_at = timezone.now()
                    user_role.save()

                    # Send approval email to user
                    self._send_approval_email(obj.user, obj.requested_role)

                except UserRole.DoesNotExist:
                    # Create new role if it doesn't exist
                    UserRole.objects.create(
                        user=obj.user,
                        role=obj.requested_role,
                        confirmed_by_admin=True,
                        assigned_by=request.user
                    )

            elif old_obj.status != 'DENIED' and obj.status == 'DENIED':
                # Request was denied
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()

                # Send denial email to user
                self._send_denial_email(obj.user, obj.requested_role, obj.admin_notes)

        super().save_model(request, obj, form, change)

    def _send_approval_email(self, user, new_role):
        """
        Send email to user when role change is approved.
        """
        try:
            role_display = dict(UserRole.ROLE_CHOICES).get(new_role, new_role)

            subject = 'CholesTrack - Role Change Request Approved'

            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #008080; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
        <h1 style="color: white; margin: 0;">Cholestrack</h1>
        <p style="color: #e0f2f1; margin: 5px 0 0 0;">Role Change Request</p>
    </div>

    <div style="background-color: #ffffff; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
        <h2 style="color: #008080; margin-top: 0;">Role Change Approved!</h2>

        <p>Hello <strong>{user.first_name} {user.last_name}</strong>,</p>

        <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;">
                <strong>Your role change request has been approved by an administrator.</strong><br>
                <strong>New Role:</strong> {role_display}
            </p>
        </div>

        <p>You can now access features and permissions associated with your new role.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="http://cholestrack.burlo.trieste.it/users/login/"
               style="background-color: #008080; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                Log In to Cholestrack
            </a>
        </div>

        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The Cholestrack Team</strong><br>
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
                [user.email],
                fail_silently=False,
                html_message=html_message
            )

        except Exception as e:
            print(f"Failed to send role change approval email to {user.email}: {str(e)}")

    def _send_denial_email(self, user, requested_role, admin_notes):
        """
        Send email to user when role change is denied.
        """
        try:
            role_display = dict(UserRole.ROLE_CHOICES).get(requested_role, requested_role)

            subject = 'CholesTrack - Role Change Request Status'

            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #008080; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
        <h1 style="color: white; margin: 0;">Cholestrack</h1>
        <p style="color: #e0f2f1; margin: 5px 0 0 0;">Role Change Request</p>
    </div>

    <div style="background-color: #ffffff; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
        <h2 style="color: #008080; margin-top: 0;">Role Change Request Update</h2>

        <p>Hello <strong>{user.first_name} {user.last_name}</strong>,</p>

        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;">
                <strong>Your request to change to {role_display} has been reviewed.</strong>
            </p>
        </div>

        {"<p><strong>Administrator Notes:</strong><br>" + admin_notes + "</p>" if admin_notes else ""}

        <p>If you have questions about this decision, please contact an administrator.</p>

        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The Cholestrack Team</strong><br>
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
                [user.email],
                fail_silently=False,
                html_message=html_message
            )

        except Exception as e:
            print(f"Failed to send role change denial email to {user.email}: {str(e)}")


# The users app focuses exclusively on authentication.
# User profile management is handled by the profile app.
# Patient and file data are managed by the samples and files apps respectively.