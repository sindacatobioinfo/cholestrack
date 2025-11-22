# RBAC Implementation Fixes

## Summary

This document describes the fixes applied to enforce Role-Based Access Control (RBAC) in the CholesTrack application.

**Date:** 2025-11-20
**Status:** ✅ Completed

---

## Changes Made

### 1. ✅ View-Level Permission Enforcement

#### Samples App (`cholestrack/samples/views.py`)

Added `@role_required` decorator to protect patient management endpoints:

| View Function | Allowed Roles | Change |
|---------------|---------------|--------|
| `patient_create()` | ADMIN, DATA_MANAGER, RESEARCHER | Added `@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])` |
| `patient_edit()` | ADMIN, DATA_MANAGER, RESEARCHER | Added `@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])` |
| `patient_delete()` | ADMIN, DATA_MANAGER | Added `@role_required(['ADMIN', 'DATA_MANAGER'])` |

**Before:**
```python
@login_required
def patient_create(request):
    # ANY logged-in user could create patients
```

**After:**
```python
@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def patient_create(request):
    # Only ADMIN, DATA_MANAGER, and RESEARCHER can create patients
```

#### Files App (`cholestrack/files/views.py`)

Added `@role_required` decorator to protect file management endpoints:

| View Function | Allowed Roles | Change |
|---------------|---------------|--------|
| `file_upload()` | ADMIN, DATA_MANAGER, RESEARCHER | Added `@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])` |
| `file_edit()` | ADMIN, DATA_MANAGER, RESEARCHER | Added `@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])` |
| `file_delete()` | ADMIN, DATA_MANAGER | Added `@role_required(['ADMIN', 'DATA_MANAGER'])` |

---

### 2. ✅ Template-Level Permission Checks

#### Sample List Template (`templates/samples/sample_list.html`)

Added conditional rendering of action buttons based on user permissions:

**Before:**
```html
<!-- Buttons shown to ALL users -->
<a href="{% url 'samples:patient_create' %}" class="btn btn-success">
    Add New Patient
</a>
<a href="{% url 'files:file_upload' %}" class="btn btn-info">
    Register File Location
</a>
```

**After:**
```html
<!-- Buttons only shown if user has permission -->
{% if user.role.can_create_patient %}
<a href="{% url 'samples:patient_create' %}" class="btn btn-success">
    Add New Patient
</a>
{% endif %}
{% if user.role.can_create_file %}
<a href="{% url 'files:file_upload' %}" class="btn btn-info">
    Register File Location
</a>
{% endif %}
```

#### Sample Detail Template (`templates/samples/sample_detail.html`)

Added permission checks for edit and delete buttons:

**Before:**
```html
<!-- Buttons shown to ALL users -->
<a href="{% url 'samples:patient_edit' ... %}" class="btn-edit">Edit Patient</a>
<a href="{% url 'samples:patient_delete' ... %}" class="btn-delete">Delete Patient</a>
```

**After:**
```html
<!-- Buttons only shown if user has permission -->
{% if user.role.can_edit_patient or user.role.can_delete_patient %}
<div class="action-buttons">
    {% if user.role.can_edit_patient %}
    <a href="{% url 'samples:patient_edit' ... %}" class="btn-edit">Edit Patient</a>
    {% endif %}
    {% if user.role.can_delete_patient %}
    <a href="{% url 'samples:patient_delete' ... %}" class="btn-delete">Delete Patient</a>
    {% endif %}
</div>
{% endif %}
```

#### File Info Template (`templates/files/file_info.html`)

Added permission checks for file actions:

```html
<!-- Download button - all confirmed users -->
{% if user.role.can_download_files %}
<button type="submit" class="btn-download">Download File</button>
{% endif %}

<!-- Edit button - ADMIN, DATA_MANAGER, RESEARCHER only -->
{% if user.role.can_edit_file %}
<a href="{% url 'files:file_edit' ... %}" class="btn-edit">Edit Metadata</a>
{% endif %}

<!-- Delete button - ADMIN, DATA_MANAGER only -->
{% if user.role.can_delete_file %}
<a href="{% url 'files:file_delete' ... %}" class="btn-delete-file">Remove File</a>
{% endif %}
```

---

### 3. ✅ Automated Tests

Created comprehensive test suite: `cholestrack/users/test_rbac.py`

#### Test Classes

**1. `UserRolePermissionMethodsTest`**
- Tests all permission methods on UserRole model
- Verifies each role (ADMIN, DATA_MANAGER, RESEARCHER, CLINICIAN) has correct permissions
- Tests unconfirmed users have no permissions

**2. `SampleViewsRBACTest`**
- Tests view-level access control for samples app
- Verifies CLINICIAN cannot create/edit/delete patients
- Verifies RESEARCHER can create/edit but not delete
- Verifies ADMIN has full access

**3. `FileViewsRBACTest`**
- Tests view-level access control for files app
- Verifies CLINICIAN cannot register/edit/delete files
- Verifies RESEARCHER can register/edit but not delete
- Verifies ADMIN has full access

**4. `RoleDecoratorTest`**
- Tests the `@role_required` decorator
- Verifies unverified users are denied access
- Verifies users without roles are denied access
- Verifies users with unconfirmed roles are denied access

#### Running Tests

To run the RBAC tests in your Django environment:

```bash
# Activate virtual environment (if using one)
source .venv/bin/activate

# Run all RBAC tests
python manage.py test users.test_rbac

# Run with verbose output
python manage.py test users.test_rbac -v 2

# Run specific test class
python manage.py test users.test_rbac.UserRolePermissionMethodsTest

# Run specific test method
python manage.py test users.test_rbac.UserRolePermissionMethodsTest.test_admin_has_all_permissions
```

**Expected Test Count:** 30+ test cases covering:
- 8 permission method tests (UserRolePermissionMethodsTest)
- 10+ sample view access tests (SampleViewsRBACTest)
- 8+ file view access tests (FileViewsRBACTest)
- 3+ decorator tests (RoleDecoratorTest)

---

## Permission Matrix After Fixes

### Complete Permissions by Role

| Feature | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN |
|---------|:-----:|:------------:|:----------:|:---------:|
| **View samples list** | ✅ | ✅ | ✅ | ✅ |
| **View sample detail** | ✅ | ✅ | ✅ | ✅ |
| **Create patients** | ✅ | ✅ | ✅ | ❌ |
| **Edit patients** | ✅ | ✅ | ✅ | ❌ |
| **Delete patients** | ✅ | ✅ | ❌ | ❌ |
| **Register files** | ✅ | ✅ | ✅ | ❌ |
| **Edit file metadata** | ✅ | ✅ | ✅ | ❌ |
| **Delete files** | ✅ | ✅ | ❌ | ❌ |
| **Download files** | ✅ | ✅ | ✅ | ✅ |
| **View file info** | ✅ | ✅ | ✅ | ✅ |
| **BAM region extraction** | ✅ | ✅ | ✅ | ✅ |
| **HPO gene search** | ✅ | ✅ | ✅ | ✅ |
| **Workflow builder** | ✅ | ✅ | ✅ | ✅ |

### UI Changes by Role

**Clinician will see:**
- ❌ NO "Add New Patient" button
- ❌ NO "Register File Location" button
- ❌ NO "Edit Patient" button
- ❌ NO "Delete Patient" button
- ❌ NO "Edit Metadata" button (on file info page)
- ❌ NO "Remove File" button (on file info page)
- ✅ CAN view all data
- ✅ CAN download files
- ✅ CAN use search and extraction tools

**Researcher will see:**
- ✅ "Add New Patient" button
- ✅ "Register File Location" button
- ✅ "Edit Patient" button
- ✅ "Edit Metadata" button
- ❌ NO "Delete Patient" button
- ❌ NO "Remove File" button
- ✅ Full access except deletes

**Data Manager will see:**
- ✅ All buttons (full CRUD access)
- ✅ Can soft-delete files and patients

**Admin will see:**
- ✅ All buttons (full access)
- ✅ Plus Django admin panel access

---

## Security Improvements

### Before Fixes

🔴 **Critical Security Issues:**
1. Any authenticated user (including CLINICIAN) could create patients
2. Any authenticated user could edit patient data
3. Any authenticated user could delete patients
4. Any authenticated user could register file locations
5. Any authenticated user could edit file metadata
6. Any authenticated user could delete files
7. UI showed action buttons to all users regardless of permissions

### After Fixes

✅ **Enforced Security:**
1. Only ADMIN, DATA_MANAGER, RESEARCHER can create patients
2. Only ADMIN, DATA_MANAGER, RESEARCHER can edit patients
3. Only ADMIN, DATA_MANAGER can delete patients
4. Only ADMIN, DATA_MANAGER, RESEARCHER can register files
5. Only ADMIN, DATA_MANAGER, RESEARCHER can edit files
6. Only ADMIN, DATA_MANAGER can delete files
7. UI only shows buttons for actions users can perform
8. View-level decorators block unauthorized access attempts
9. Automated tests verify enforcement

---

## Files Modified

### Python Files (Views)
1. `cholestrack/samples/views.py` - Added role decorators to patient CRUD views
2. `cholestrack/files/views.py` - Added role decorators to file CRUD views

### HTML Templates
1. `cholestrack/templates/samples/sample_list.html` - Added permission checks for action buttons
2. `cholestrack/templates/samples/sample_detail.html` - Added permission checks for edit/delete buttons
3. `cholestrack/templates/files/file_info.html` - Added permission checks for file actions

### Test Files
1. `cholestrack/users/test_rbac.py` - **NEW** Comprehensive RBAC test suite

---

## Verification Steps

### Manual Testing

1. **Create test users with different roles:**
   ```bash
   python manage.py createsuperuser  # Creates ADMIN
   # Register other users via /register/ and assign roles in admin panel
   ```

2. **Test as CLINICIAN:**
   - Log in as clinician user
   - Visit `/samples/` - should see patient list ✅
   - Should NOT see "Add New Patient" button ✅
   - Should NOT see "Register File Location" button ✅
   - Try to access `/samples/create/` directly - should be denied ❌
   - Try to access `/samples/edit/<id>/` - should be denied ❌
   - Should be able to download files ✅

3. **Test as RESEARCHER:**
   - Log in as researcher user
   - Should see "Add New Patient" and "Register File Location" buttons ✅
   - Should be able to create and edit patients ✅
   - Try to access `/samples/delete/<id>/` - should be denied ❌
   - Try to access `/files/delete/<id>/` - should be denied ❌

4. **Test as DATA_MANAGER:**
   - Should have full CRUD access to patients and files ✅
   - Can soft-delete patients and files ✅

5. **Test as ADMIN:**
   - Should have full access to everything ✅

### Automated Testing

Run the test suite:
```bash
python manage.py test users.test_rbac -v 2
```

All tests should pass ✅

---

## Migration Notes

### For Existing Users

No database migrations required. The changes only affect:
1. View-level access control (decorators)
2. Template rendering (conditional display)
3. Testing infrastructure

### For Production Deployment

1. **Update code:**
   ```bash
   git pull origin main
   ```

2. **No migration needed** (only code changes, no model changes)

3. **Restart services:**
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

4. **Verify RBAC:**
   - Test with different user roles
   - Check server logs for any permission denied errors
   - Run automated tests in production environment

---

## Future Enhancements

While the current implementation fixes the critical security gaps, consider these enhancements:

### 1. Patient-Level Access Control
Implement per-patient permissions to restrict users to specific projects or patients:
```python
class PatientAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
```

### 2. Audit Logging
Log all create/update/delete operations:
```python
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20)  # CREATE, UPDATE, DELETE
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
```

### 3. Download Tracking
Track file downloads for compliance:
```python
class FileDownloadLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file_location = models.ForeignKey(AnalysisFileLocation, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
```

### 4. Rate Limiting
Prevent abuse by limiting download/access rates per user.

### 5. Two-Factor Authentication
Add 2FA for administrator accounts.

---

## References

- **RBAC Documentation:** `/home/user/cholestrack/RBAC_PERMISSIONS_DOCUMENTATION.md`
- **User Models:** `cholestrack/users/models.py:68-160`
- **Decorators:** `cholestrack/users/decorators.py`
- **Tests:** `cholestrack/users/test_rbac.py`

---

## Support

If you encounter issues with RBAC:

1. Check user's email is verified: `EmailVerification.email_confirmed = True`
2. Check user's role is confirmed: `UserRole.confirmed_by_admin = True`
3. Check user has correct role assigned
4. Review server logs for permission denied errors
5. Run automated tests to verify system integrity

---

**Implementation Status:** ✅ Complete
**Tests Status:** ✅ Created (syntax verified)
**Documentation Status:** ✅ Complete
