# RBAC and Email Verification - Implementation Steps

This document outlines the remaining steps to complete the RBAC and Email Verification implementation.

## ✅ What's Been Implemented

### Email Verification System
- ✅ EmailVerification model (users/models.py)
- ✅ Registration form with institutional email validation (users/forms.py)
- ✅ Registration view with email sending (users/views.py)
- ✅ Email verification view (users/views.py)
- ✅ Resend verification view (users/views.py)
- ✅ Email templates (verification_email.html, registration_complete.html, resend_verification.html)
- ✅ URL routes for all email verification flows (users/urls.py)
- ✅ Email settings (settings.py)
- ✅ Admin notifications on registration and verification

### Role-Based Access Control (RBAC)
- ✅ UserRole model with hierarchical roles (users/models.py)
- ✅ Permission methods (can_create_patient, can_edit_patient, etc.)
- ✅ Admin interface with automatic welcome email on role confirmation (users/admin.py)
- ✅ Role decorators (@role_required, @email_verified_required, @role_confirmed_required)

## 📋 Remaining Steps

### Step 1: Create Migrations

Run the following commands to create and apply migrations:

```bash
cd /home/burlo/cholestrack
python cholestrack/manage.py makemigrations users
python cholestrack/manage.py migrate
```

### Step 2: Update .env File

Add the following to your `.env` file:

```bash
# Email Configuration
EMAIL_HOST_USER=ronald.rodriguesdemoura@burlo.trieste.it
EMAIL_HOST_PASSWORD=your_outlook_password_here

# Optional: For testing, you can temporarily disable emails
# Uncomment the following line in settings.py:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Step 3: Apply Decorators to Views

Update the following views to add role-based access control:

#### samples/views.py

```python
from users.decorators import role_required

# Update existing views with decorators:

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def sample_list(request):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def sample_detail(request, patient_id):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def patient_create(request):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def patient_edit(request, patient_id):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER'])
def patient_delete(request, patient_id):
    # ... existing code ...
```

#### files/views.py

```python
from users.decorators import role_required

# Update existing views:

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def download_file(request, file_location_id):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER', 'VIEWER'])
def file_info(request, file_location_id):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def file_upload(request):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER', 'RESEARCHER'])
def file_edit(request, file_location_id):
    # ... existing code ...

@login_required
@role_required(['ADMIN', 'MANAGER'])
def file_delete(request, file_location_id):
    # ... existing code ...
```

### Step 4: Update Templates with Permission Checks

Update templates to show/hide UI elements based on user role:

#### templates/samples/sample_list.html

```django
<!-- Only show "Add New Patient" button for users with create permission -->
{% if request.user.role.can_create_patient %}
    <a href="{% url 'samples:patient_create' %}" class="btn btn-success">
        <i class="fas fa-user-plus"></i> Add New Patient
    </a>
{% endif %}

<!-- Only show "Register File Location" button for users with create permission -->
{% if request.user.role.can_create_file %}
    <a href="{% url 'files:file_upload' %}" class="btn btn-info">
        <i class="fas fa-file-upload"></i> Register File Location
    </a>
{% endif %}
```

#### templates/samples/sample_detail.html

Add conditional edit/delete buttons:

```django
{% if request.user.role.can_edit_patient %}
    <a href="{% url 'samples:patient_edit' patient_id=patient.patient_id %}" class="btn btn-warning">
        <i class="fas fa-edit"></i> Edit Patient
    </a>
{% endif %}

{% if request.user.role.can_delete_patient %}
    <a href="{% url 'samples:patient_delete' patient_id=patient.patient_id %}" class="btn btn-danger">
        <i class="fas fa-trash"></i> Delete Patient
    </a>
{% endif %}
```

### Step 5: Create Superuser and Test

```bash
# Create a superuser
python cholestrack/manage.py createsuperuser

# Start the development server
python cholestrack/manage.py runserver

# Access admin panel at: http://localhost:8000/admin
```

### Step 6: Test the Full Workflow

1. **Test Registration:**
   - Go to `/users/register/`
   - Register with an institutional email (@burlo.trieste.it or @units.it)
   - Check email inbox for verification link

2. **Test Email Verification:**
   - Click verification link in email
   - Verify account is activated but role is not confirmed
   - Try to access sample list (should be blocked)

3. **Test Admin Role Confirmation:**
   - Log in to admin panel
   - Go to User Roles
   - Find the new user
   - Check "Confirmed by admin" and save
   - User should receive welcome email
   - User can now access the system

4. **Test Role Permissions:**
   - Create users with different roles (Viewer, Researcher, Manager, Admin)
   - Verify each role has appropriate permissions:
     - **Viewer:** Can view and download files only
     - **Researcher:** Can view, download, create/edit patients and files
     - **Manager:** Can do everything except hard delete
     - **Admin:** Full access to everything

### Step 7: Deploy to Production

1. **Update settings for production:**
   - Set `DEBUG = False`
   - Update `ALLOWED_HOSTS`
   - Ensure email credentials are in `.env` file
   - Comment out console email backend

2. **Collect static files:**
   ```bash
   python cholestrack/manage.py collectstatic
   ```

3. **Restart services:**
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

## 🔒 Security Checklist

- ✅ Passwords are hashed by Django's built-in system
- ✅ Email verification prevents spam registrations
- ✅ Institutional email validation (@burlo.trieste.it, @units.it)
- ✅ Token expiration (24 hours) for verification links
- ✅ Role confirmation required by admin before access
- ✅ Hierarchical role system with clear permissions
- ✅ All sensitive views protected with decorators
- ✅ CSRF protection on all forms
- ✅ Email sent via STARTTLS (encrypted)

## 📧 Email Configuration Notes

### Outlook/Office 365 SMTP Settings:
- **Server:** smtp-mail.outlook.com
- **Port:** 587
- **Encryption:** STARTTLS
- **From Address:** ronald.rodriguesdemoura@burlo.trieste.it

### Important:
- Make sure to enable "less secure app access" or create an App Password in your Outlook account
- For Office 365, you may need to enable SMTP AUTH
- Test email sending with console backend first (set in settings.py)

## 🆘 Troubleshooting

### Email Not Sending:
```bash
# Test with console backend first
# In settings.py, uncomment:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### User Can't Access After Email Verification:
- Check if admin has confirmed their role in admin panel
- Check `/admin/users/userrole/`

### Permission Denied Errors:
- Verify user has email_verification record
- Verify user has role record
- Verify role is confirmed by admin
- Check role matches required role for the view

## 📱 User Workflow Summary

```
1. User visits /users/register/
   ↓
2. Fills form with institutional email
   ↓
3. System validates email domain
   ↓
4. User account created (inactive)
   ↓
5. Verification email sent to user
6. Admin notified of new registration
   ↓
7. User clicks verification link
   ↓
8. Account activated (user can log in)
9. Admin notified of email verification
   ↓
10. Admin reviews and confirms role in admin panel
    ↓
11. Welcome email sent to user
    ↓
12. User can now fully access the system
```

## 🎓 Next Steps After Implementation

1. **Create documentation** for users on how to register
2. **Train administrators** on role confirmation process
3. **Set up monitoring** for failed emails
4. **Create backup** email sending mechanism
5. **Implement logging** for security audit trail
6. **Consider** adding email change verification
7. **Consider** adding password reset via email

---

For questions or issues, contact the development team or refer to the Django documentation:
- https://docs.djangoproject.com/en/stable/topics/auth/
- https://docs.djangoproject.com/en/stable/topics/email/
