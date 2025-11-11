# Implementation Suggestions for Cholestrack

This document contains detailed suggestions for implementing Role-Based Access Control (RBAC) and Email Confirmation features in the Cholestrack application.

---

## 1. Role-Based Access Control (RBAC) for CRUD Operations

### Overview
Implement a hierarchical permission system where users have different levels of access to Sample and File CRUD operations based on their assigned roles.

### Recommended Role Hierarchy

```
┌─────────────────────┐
│   Administrator     │  Full access to everything
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───┴────┐   ┌────┴────┐
│ Manager│   │Researcher│  Create/Edit/View (limited delete)
└────┬───┘   └─────┬───┘
     │             │
     └──────┬──────┘
            │
      ┌─────┴──────┐
      │   Viewer   │  View only (no create/edit/delete)
      └────────────┘
```

### Implementation Approach

#### Step 1: Extend Django's User Model with Roles

**Option A: Using Django Groups (Recommended for simplicity)**

Create groups with specific permissions:

```python
# In management command or migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from samples.models import Patient
from files.models import AnalysisFileLocation

# Create groups
admin_group = Group.objects.create(name='Administrator')
manager_group = Group.objects.create(name='Manager')
researcher_group = Group.objects.create(name='Researcher')
viewer_group = Group.objects.create(name='Viewer')

# Get content types
patient_ct = ContentType.objects.get_for_model(Patient)
file_ct = ContentType.objects.get_for_model(AnalysisFileLocation)

# Assign permissions to Administrator (all permissions)
admin_permissions = Permission.objects.filter(
    content_type__in=[patient_ct, file_ct]
)
admin_group.permissions.set(admin_permissions)

# Assign permissions to Manager (all except hard delete)
manager_permissions = Permission.objects.filter(
    content_type__in=[patient_ct, file_ct]
).exclude(codename__in=['delete_patient', 'delete_analysisfilelocation'])
manager_group.permissions.set(manager_permissions)

# Assign permissions to Researcher (view, add, change)
researcher_permissions = Permission.objects.filter(
    content_type__in=[patient_ct, file_ct],
    codename__in=['view_patient', 'add_patient', 'change_patient',
                   'view_analysisfilelocation', 'add_analysisfilelocation',
                   'change_analysisfilelocation']
)
researcher_group.permissions.set(researcher_permissions)

# Assign permissions to Viewer (view only)
viewer_permissions = Permission.objects.filter(
    content_type__in=[patient_ct, file_ct],
    codename__in=['view_patient', 'view_analysisfilelocation']
)
viewer_group.permissions.set(viewer_permissions)
```

**Option B: Custom Role Model (More flexible)**

```python
# users/models.py
from django.db import models
from django.contrib.auth.models import User

class UserRole(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('RESEARCHER', 'Researcher'),
        ('VIEWER', 'Viewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_roles',
        help_text="Administrator who assigned this role"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    confirmed_by_admin = models.BooleanField(
        default=False,
        help_text="Whether an administrator has confirmed this role assignment"
    )

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def can_create_patient(self):
        return self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_edit_patient(self):
        return self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']

    def can_delete_patient(self):
        return self.role in ['ADMIN', 'MANAGER']

    def can_download_files(self):
        return self.role in ['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER']

    def can_upload_files(self):
        return self.role in ['ADMIN', 'MANAGER', 'RESEARCHER']
```

#### Step 2: Create Permission Decorators

```python
# samples/decorators.py
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def role_required(allowed_roles):
    """
    Decorator to restrict view access based on user role.

    Usage:
        @role_required(['ADMIN', 'MANAGER'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, 'You must be logged in to access this page.')
                return redirect('users:login')

            # Check if user has a role
            if not hasattr(request.user, 'role'):
                messages.error(request, 'Your account does not have a role assigned. Please contact an administrator.')
                return redirect('home:index')

            # Check if role is confirmed by admin
            if not request.user.role.confirmed_by_admin:
                messages.error(request, 'Your role has not been confirmed by an administrator yet.')
                return redirect('home:index')

            # Check if user's role is in allowed roles
            if request.user.role.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('samples:sample_list')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required_with_message(perm, message=None):
    """
    Decorator to check Django permissions with custom error message.

    Usage:
        @permission_required_with_message('samples.add_patient')
        def patient_create(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                error_message = message or f'You do not have permission to perform this action.'
                messages.error(request, error_message)
                return redirect('samples:sample_list')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

#### Step 3: Apply Decorators to Views

**Using Custom Role Model:**

```python
# samples/views.py
from .decorators import role_required

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def patient_create(request):
    # Your create logic
    pass

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def patient_edit(request, patient_id):
    # Your edit logic
    pass

@login_required
@role_required(['ADMIN', 'MANAGER'])
def patient_delete(request, patient_id):
    # Your delete logic
    pass

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def sample_list(request):
    # Your list logic
    pass
```

**Using Django Groups/Permissions:**

```python
# samples/views.py
from .decorators import permission_required_with_message

@login_required
@permission_required_with_message('samples.add_patient',
                                   'You do not have permission to create patients.')
def patient_create(request):
    # Your create logic
    pass

@login_required
@permission_required_with_message('samples.change_patient',
                                   'You do not have permission to edit patients.')
def patient_edit(request, patient_id):
    # Your edit logic
    pass
```

#### Step 4: Template-Level Permission Checks

Update templates to hide/show UI elements based on permissions:

```django
{# templates/samples/sample_list.html #}

{% if perms.samples.add_patient %}
    <a href="{% url 'samples:patient_create' %}" class="btn btn-success">
        <i class="fas fa-user-plus"></i> Add New Patient
    </a>
{% endif %}

{# Using custom role model #}
{% if request.user.role.can_create_patient %}
    <a href="{% url 'samples:patient_create' %}" class="btn btn-success">
        <i class="fas fa-user-plus"></i> Add New Patient
    </a>
{% endif %}
```

#### Step 5: Admin Interface for Role Management

```python
# users/admin.py
from django.contrib import admin
from .models import UserRole

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'confirmed_by_admin', 'assigned_at', 'assigned_by']
    list_filter = ['role', 'confirmed_by_admin']
    search_fields = ['user__username', 'user__email']

    def save_model(self, request, obj, form, change):
        if change and 'confirmed_by_admin' in form.changed_data:
            # Log who confirmed the role
            if obj.confirmed_by_admin:
                # Send notification to user that role was confirmed
                pass
        super().save_model(request, obj, form, change)
```

#### Step 6: Self-Registration with Pending Role

```python
# users/views.py
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create default role (Viewer, not confirmed)
            UserRole.objects.create(
                user=user,
                role='VIEWER',  # Default role
                confirmed_by_admin=False  # Requires admin confirmation
            )

            messages.success(
                request,
                'Account created successfully! An administrator will review and '
                'confirm your role before you can access the system.'
            )
            return redirect('users:login')
    else:
        form = UserCreationForm()

    return render(request, 'users/register.html', {'form': form})
```

### Recommended Implementation Path

1. **Start with Django Groups** (simpler, built-in)
2. **Create migration** to set up groups and permissions
3. **Add decorators** to views
4. **Update templates** to show/hide based on permissions
5. **Later migrate to Custom Role Model** if more flexibility is needed

---

## 2. Email Confirmation for Account Creation

### Overview
Implement email verification to ensure users provide valid institutional email addresses before they can access the system.

### Implementation Approach

#### Step 1: Install Required Packages

```bash
# Already included in Django, but you may want django-allauth for advanced features
pip install django-allauth
```

**OR use built-in Django email verification (simpler)**

#### Step 2: Configure Email Backend

```python
# cholestrack/project/settings.py

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your institution's SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')  # Store in .env
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')  # Store in .env
DEFAULT_FROM_EMAIL = 'noreply@cholestrack.org'

# For development/testing, use console backend
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email validation - restrict to institutional domains
ALLOWED_EMAIL_DOMAINS = [
    'burlo.trieste.it',  # Your institution
    'units.it',  # University
    # Add more allowed domains
]
```

#### Step 3: Extend User Model with Email Verification

```python
# users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    email_confirmed = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, unique=True)
    token_created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def is_token_valid(self):
        """Token expires after 24 hours"""
        expiration_time = self.token_created_at + timedelta(hours=24)
        return timezone.now() < expiration_time

    def generate_new_token(self):
        """Generate a new verification token"""
        self.verification_token = get_random_string(64)
        self.token_created_at = timezone.now()
        self.save()
        return self.verification_token

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def __str__(self):
        return f"{self.user.username} - {'Verified' if self.email_confirmed else 'Pending'}"
```

#### Step 4: Create Registration View with Email Validation

```python
# users/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from .models import EmailVerification, UserRole
from .forms import RegistrationForm

def validate_institutional_email(email):
    """Validate that email is from an allowed institutional domain"""
    domain = email.split('@')[-1].lower()
    return domain in settings.ALLOWED_EMAIL_DOMAINS

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Validate institutional email
            if not validate_institutional_email(email):
                allowed_domains = ', '.join(settings.ALLOWED_EMAIL_DOMAINS)
                messages.error(
                    request,
                    f'Please use an institutional email address. '
                    f'Allowed domains: {allowed_domains}'
                )
                return render(request, 'users/register.html', {'form': form})

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'This email address is already registered.')
                return render(request, 'users/register.html', {'form': form})

            # Create user (inactive until email confirmed)
            user = form.save(commit=False)
            user.is_active = False  # User cannot login until email confirmed
            user.save()

            # Create email verification token
            verification = EmailVerification.objects.create(
                user=user,
                verification_token=get_random_string(64)
            )

            # Create default role (pending admin confirmation)
            UserRole.objects.create(
                user=user,
                role='VIEWER',
                confirmed_by_admin=False
            )

            # Send verification email
            current_site = get_current_site(request)
            verification_url = f"http://{current_site.domain}/users/verify-email/{verification.verification_token}/"

            email_subject = 'Verify Your Cholestrack Account'
            email_body = render_to_string('users/verification_email.html', {
                'user': user,
                'verification_url': verification_url,
                'site_name': 'Cholestrack',
            })

            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=email_body
            )

            messages.success(
                request,
                f'Account created successfully! A verification email has been sent to {email}. '
                'Please check your inbox and click the verification link to activate your account.'
            )
            return redirect('users:registration_complete')
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})
```

#### Step 5: Create Email Verification View

```python
# users/views.py
def verify_email(request, token):
    try:
        verification = EmailVerification.objects.get(verification_token=token)

        # Check if token is still valid
        if not verification.is_token_valid():
            messages.error(
                request,
                'This verification link has expired. Please request a new one.'
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
    """Allow users to request a new verification email"""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_active=False)
            verification = user.email_verification

            # Generate new token
            verification.generate_new_token()

            # Send new verification email
            current_site = get_current_site(request)
            verification_url = f"http://{current_site.domain}/users/verify-email/{verification.verification_token}/"

            email_subject = 'Verify Your Cholestrack Account (New Link)'
            email_body = render_to_string('users/verification_email.html', {
                'user': user,
                'verification_url': verification_url,
                'site_name': 'Cholestrack',
            })

            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=email_body
            )

            messages.success(
                request,
                f'A new verification email has been sent to {email}.'
            )
            return redirect('users:registration_complete')

        except User.DoesNotExist:
            messages.error(request, 'No inactive account found with this email address.')

    return render(request, 'users/resend_verification.html')
```

#### Step 6: Create Email Templates

```html
<!-- templates/users/verification_email.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Verify Your Email</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2 style="color: #008080;">Welcome to {{ site_name }}!</h2>

        <p>Hello {{ user.username }},</p>

        <p>Thank you for registering with Cholestrack. Please verify your email address by clicking the button below:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ verification_url }}"
               style="background-color: #008080; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Verify Email Address
            </a>
        </div>

        <p>Or copy and paste this link into your browser:</p>
        <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
            {{ verification_url }}
        </p>

        <p>This link will expire in 24 hours.</p>

        <p><strong>Note:</strong> After verifying your email, an administrator will need to confirm your role before you can access patient data.</p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

        <p style="font-size: 12px; color: #666;">
            If you didn't create this account, please ignore this email.
        </p>
    </div>
</body>
</html>
```

#### Step 7: Update URLs

```python
# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('registration-complete/', views.registration_complete, name='registration_complete'),
    # ... other URLs
]
```

#### Step 8: Update Login Middleware/Decorator

```python
# users/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def email_verified_required(view_func):
    """
    Decorator to ensure user has verified their email before accessing views
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in.')
            return redirect('users:login')

        if not hasattr(request.user, 'email_verification') or \
           not request.user.email_verification.email_confirmed:
            messages.error(
                request,
                'You must verify your email address before accessing this page. '
                'Please check your email for the verification link.'
            )
            return redirect('users:resend_verification')

        return view_func(request, *args, **kwargs)
    return wrapper
```

Apply to views:

```python
@login_required
@email_verified_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def sample_list(request):
    # Your view logic
    pass
```

#### Step 9: Admin Notification for New Registrations

```python
# In users/views.py register function, after creating user:

# Send notification to administrators
admin_users = User.objects.filter(is_staff=True, is_active=True)
admin_emails = [admin.email for admin in admin_users if admin.email]

if admin_emails:
    send_mail(
        'New User Registration - Cholestrack',
        f'A new user {user.username} ({user.email}) has registered and verified their email. '
        f'Please review and confirm their role in the admin panel.',
        settings.DEFAULT_FROM_EMAIL,
        admin_emails,
        fail_silently=True
    )
```

### Testing Email in Development

For development, use Django's console email backend:

```python
# settings.py
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

Emails will be printed to the console instead of being sent.

---

## 3. Combined Workflow

### User Registration → Email Verification → Role Confirmation

```
1. User visits registration page
   ↓
2. User fills form with institutional email
   ↓
3. System validates email domain
   ↓
4. System creates inactive user account
   ↓
5. System sends verification email
   ↓
6. User clicks verification link
   ↓
7. System activates user account
   ↓
8. System assigns default "Viewer" role (unconfirmed)
   ↓
9. System notifies administrators
   ↓
10. Admin reviews and confirms role
    ↓
11. User can now access system with confirmed role
```

### Database Schema Changes Needed

```sql
-- Add to users app
CREATE TABLE users_emailverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES auth_user(id),
    email_confirmed BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(100) UNIQUE,
    token_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL
);

CREATE TABLE users_userrole (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES auth_user(id),
    role VARCHAR(20) DEFAULT 'VIEWER',
    assigned_by_id INTEGER REFERENCES auth_user(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_by_admin BOOLEAN DEFAULT FALSE
);
```

---

## 4. Security Considerations

### For RBAC:
1. **Always check permissions server-side** (don't rely only on template hiding)
2. **Log permission changes** for audit trail
3. **Implement role hierarchy** properly (Admin > Manager > Researcher > Viewer)
4. **Test edge cases** (user with no role, role not confirmed, etc.)

### For Email Verification:
1. **Token expiration** (24 hours recommended)
2. **Rate limiting** on resend verification (prevent spam)
3. **Email domain validation** (whitelist institutional domains)
4. **Secure token generation** (use cryptographically secure random strings)
5. **HTTPS only** for verification links in production

---

## 5. Migration Path

### Phase 1: Email Verification (Week 1-2)
1. Add EmailVerification model
2. Update registration flow
3. Configure email backend
4. Test with console backend
5. Deploy with real SMTP
6. Update existing users (mark as verified)

### Phase 2: Basic RBAC (Week 3-4)
1. Add UserRole model
2. Create management command to assign roles to existing users
3. Apply decorators to views
4. Update templates
5. Test all permission combinations

### Phase 3: Admin Confirmation (Week 5)
1. Add admin interface for role confirmation
2. Implement notification system
3. Create admin dashboard for pending approvals

### Phase 4: Refinement (Week 6)
1. Add logging and audit trail
2. Create user documentation
3. Perform security audit
4. Load testing

---

## 6. Useful Management Commands

```python
# management/commands/assign_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserRole

class Command(BaseCommand):
    help = 'Assign roles to existing users'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username')
        parser.add_argument('role', type=str, choices=['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
        parser.add_argument('--confirm', action='store_true', help='Auto-confirm the role')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
            role, created = UserRole.objects.get_or_create(user=user)
            role.role = options['role']
            role.confirmed_by_admin = options.get('confirm', False)
            role.save()

            self.stdout.write(
                self.style.SUCCESS(f'Successfully assigned role {options["role"]} to {user.username}')
            )
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {options["username"]} not found'))
```

Usage:
```bash
python manage.py assign_roles john.doe RESEARCHER --confirm
```

---

## Questions to Consider Before Implementation

1. **RBAC:**
   - Do you want to use Django's built-in Groups/Permissions or create a custom solution?
   - Should roles be hierarchical (Manager can do everything Researcher can do)?
   - Do you need per-patient permissions (e.g., Researcher can only edit their own patients)?

2. **Email Verification:**
   - What SMTP server will you use? (Gmail, institutional server, AWS SES, SendGrid?)
   - What institutional email domains should be allowed?
   - Should admin confirmation happen before or after email verification?
   - Do you want to send welcome emails after role confirmation?

3. **Timeline:**
   - When do you want these features deployed?
   - Should existing users be grandfathered in or require verification?

---

Let me know which approach you prefer and I can help implement it step by step!
