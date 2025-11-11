# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib import messages
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from .forms import RegistrationForm, ResendVerificationForm
from .models import EmailVerification, UserRole


def register(request):
    """
    User registration view with email verification.
    Creates inactive user account and sends verification email to institutional address.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Create user (inactive until email confirmed)
            user = form.save(commit=False)
            user.is_active = False  # User cannot login until email confirmed
            user.save()

            # Create email verification token
            verification = EmailVerification.objects.create(
                user=user,
                verification_token=get_random_string(64)
            )

            # Create default role (Clinician, pending admin confirmation)
            UserRole.objects.create(
                user=user,
                role='CLINICIAN',
                confirmed_by_admin=False
            )

            # Send verification email
            current_site = get_current_site(request)
            protocol = 'https' if request.is_secure() else 'http'
            verification_url = f"{protocol}://{current_site.domain}/verify-email/{verification.verification_token}/"

            email_subject = 'Verify Your Cholestrack Account'
            email_body = render_to_string('users/verification_email.html', {
                'user': user,
                'verification_url': verification_url,
                'site_name': 'Cholestrack',
            })

            try:
                send_mail(
                    email_subject,
                    '',  # Plain text version (empty)
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                    html_message=email_body
                )

                # Send notification to admin
                admin_subject = f'New User Registration - {user.username}'
                admin_body = f"""
A new user has registered on Cholestrack:

Username: {user.username}
Email: {user.email}
Name: {user.first_name} {user.last_name}
Registration Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

The user will verify their email address. After email verification, please review and confirm their role in the admin panel.

Admin Panel: {protocol}://{current_site.domain}/admin/users/userrole/
"""

                send_mail(
                    admin_subject,
                    admin_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=True
                )

                messages.success(
                    request,
                    f'Account created successfully! A verification email has been sent to {user.email}. '
                    'Please check your inbox and click the verification link to activate your account.'
                )
                return redirect('users:registration_complete')

            except Exception as e:
                # If email fails, delete the user and show error
                user.delete()
                messages.error(
                    request,
                    f'Failed to send verification email. Please try again or contact the administrator.'
                )
                return render(request, 'users/register.html', {'form': form})
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def verify_email(request, token):
    """
    Email verification view. Activates user account after email confirmation.
    """
    try:
        verification = EmailVerification.objects.get(verification_token=token)

        # Check if token is still valid
        if not verification.is_token_valid():
            messages.error(
                request,
                'This verification link has expired (valid for 24 hours). Please request a new one.'
            )
            return redirect('users:resend_verification')

        # Check if already verified
        if verification.email_confirmed:
            messages.info(request, 'Your email has already been verified. You can log in now.')
            return redirect('users:login')

        # Activate user account
        user = verification.user
        user.is_active = True
        user.save()

        # Mark email as confirmed
        verification.email_confirmed = True
        verification.confirmed_at = timezone.now()
        verification.save()

        # Notify admin that user has verified email
        try:
            current_site = get_current_site(request)
            protocol = 'https' if request.is_secure() else 'http'

            admin_subject = f'Email Verified - Action Required: {user.username}'
            admin_body = f"""
User {user.username} has successfully verified their email address.

User Details:
- Username: {user.username}
- Email: {user.email}
- Name: {user.first_name} {user.last_name}
- Email Verified: {verification.confirmed_at.strftime('%Y-%m-%d %H:%M:%S')}

ACTION REQUIRED: Please review and confirm their role assignment in the admin panel.

Review User Role: {protocol}://{current_site.domain}/admin/users/userrole/

Until you confirm their role, they will not be able to access patient data.
"""

            send_mail(
                admin_subject,
                admin_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True
            )
        except:
            pass  # Don't fail if admin notification fails

        messages.success(
            request,
            'Your email has been verified successfully! You can now log in. '
            'An administrator will review and confirm your role before you can access patient data.'
        )
        return redirect('users:login')

    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('users:register')


def resend_verification(request):
    """
    Resend verification email if the original was not received or expired.
    """
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email, is_active=False)
                verification = user.email_verification

                # Generate new token
                verification.generate_new_token()

                # Send new verification email
                current_site = get_current_site(request)
                protocol = 'https' if request.is_secure() else 'http'
                verification_url = f"{protocol}://{current_site.domain}/verify-email/{verification.verification_token}/"

                email_subject = 'Verify Your Cholestrack Account (New Link)'
                email_body = render_to_string('users/verification_email.html', {
                    'user': user,
                    'verification_url': verification_url,
                    'site_name': 'Cholestrack',
                })

                send_mail(
                    email_subject,
                    '',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                    html_message=email_body
                )

                messages.success(
                    request,
                    f'A new verification email has been sent to {email}. Please check your inbox.'
                )
                return redirect('users:registration_complete')

            except User.DoesNotExist:
                messages.error(
                    request,
                    'No inactive account found with this email address. '
                    'The account may already be verified, or the email address is incorrect.'
                )
            except Exception as e:
                messages.error(request, 'Failed to send verification email. Please try again later.')
    else:
        form = ResendVerificationForm()

    return render(request, 'users/resend_verification.html', {'form': form})


def registration_complete(request):
    """
    Registration complete page shown after successful registration.
    """
    return render(request, 'users/registration_complete.html')


class CholestrackLoginView(DjangoLoginView):
    """
    Custom login view using Django's built-in authentication.
    """
    template_name = 'users/login.html'