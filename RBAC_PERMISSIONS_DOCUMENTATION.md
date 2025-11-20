# CholesTrack RBAC Permissions Documentation

## Overview

This document provides a comprehensive analysis of the Role-Based Access Control (RBAC) implementation in the CholesTrack Django application. It details what each user tier can actually do in the **current version** of the code, highlighting gaps between intended permissions and actual enforcement.

**Document Status:** Analysis of current implementation as of 2025-11-20
**Critical Finding:** RBAC permissions are defined but **not enforced** in several key areas.

---

## User Roles Hierarchy

The system defines four user roles with the following hierarchy (from highest to lowest privileges):

| Role | Code | Description |
|------|------|-------------|
| **Administrator** | `ADMIN` | Full access to everything |
| **Data Manager** | `DATA_MANAGER` | Create/Edit/View/Soft-delete (no hard delete) |
| **Researcher** | `RESEARCHER` | Create/Edit/View (no delete) |
| **Clinician** | `CLINICIAN` | View only (read-only access) |

**Default Role:** All new users are assigned `CLINICIAN` role upon registration.

---

## Authentication Requirements

All users must satisfy the following requirements before accessing any feature:

### 1. User Registration Flow
1. User fills registration form (`/register/`)
2. Account created with `is_active=False`
3. Email verification link sent to user
4. Default role assigned: `CLINICIAN` (unconfirmed)

### 2. Email Verification
- ✅ **Required:** User must click verification link within 24 hours
- ✅ Sets `is_active=True` on user account
- ✅ Marks `email_confirmed=True` in EmailVerification model
- ❌ User still cannot access features until admin confirms role

### 3. Admin Role Confirmation
- ✅ **Required:** Administrator must manually confirm user role in Django Admin
- ✅ Sets `confirmed_by_admin=True` in UserRole model
- ✅ Triggers welcome email to user
- ✅ Only after this step can users access protected features

**Summary:** Users need **both** email verification **and** admin approval to access the system.

---

## Defined Permission Methods (UserRole Model)

The `UserRole` model in `cholestrack/users/models.py` defines the following permission methods:

### Patient/Sample Management
| Method | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN | Code Reference |
|--------|:-----:|:------------:|:----------:|:---------:|----------------|
| `can_create_patient()` | ✅ | ✅ | ✅ | ❌ | `users/models.py:129-131` |
| `can_edit_patient()` | ✅ | ✅ | ✅ | ❌ | `users/models.py:133-135` |
| `can_delete_patient()` | ✅ | ✅ | ❌ | ❌ | `users/models.py:137-139` |
| `can_view_samples()` | ✅ | ✅ | ✅ | ✅ | `users/models.py:157-159` |

### File Management
| Method | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN | Code Reference |
|--------|:-----:|:------------:|:----------:|:---------:|----------------|
| `can_create_file()` | ✅ | ✅ | ✅ | ❌ | `users/models.py:141-143` |
| `can_edit_file()` | ✅ | ✅ | ✅ | ❌ | `users/models.py:145-147` |
| `can_delete_file()` | ✅ | ✅ | ❌ | ❌ | `users/models.py:149-151` |
| `can_download_files()` | ✅ | ✅ | ✅ | ✅ | `users/models.py:153-155` |

**Important Note:** These methods exist but are **NOT being called** in the views! This is a critical security gap.

---

## Actual Permissions by Feature (Current Implementation)

### 🔴 **Samples App** (`/samples/`)

**Security Status:** ⚠️ **CRITICAL - NO ROLE ENFORCEMENT**

| Feature | Endpoint | Current Protection | Should Require | Issue |
|---------|----------|-------------------|----------------|-------|
| View samples list | `/samples/` | `@login_required` | All confirmed users | ✅ OK (but weak) |
| View sample detail | `/samples/<id>/` | `@login_required` | All confirmed users | ✅ OK (but weak) |
| **Create patient** | `/samples/create/` | `@login_required` | ADMIN, DATA_MANAGER, RESEARCHER | ❌ **ANY user can create** |
| **Edit patient** | `/samples/edit/<id>/` | `@login_required` | ADMIN, DATA_MANAGER, RESEARCHER | ❌ **ANY user can edit** |
| **Delete patient** | `/samples/delete/<id>/` | `@login_required` | ADMIN, DATA_MANAGER | ❌ **ANY user can delete** |

**Reference:** `cholestrack/samples/views.py`

**Critical Issue:**
```python
# Current implementation (samples/views.py:125)
@login_required
def patient_create(request):
    # NO role checking!
    # Any authenticated user can create patients
```

**What it should be:**
```python
from users.decorators import role_required

@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def patient_create(request):
    # Protected by role
```

---

### 🔴 **Files App** (`/files/`)

**Security Status:** ⚠️ **CRITICAL - NO ROLE ENFORCEMENT**

| Feature | Endpoint | Current Protection | Should Require | Issue |
|---------|----------|-------------------|----------------|-------|
| Download file | `/files/download/<id>/` | `@login_required` | All confirmed users | ✅ OK (but weak) |
| View file info | `/files/info/<id>/` | `@login_required` | All confirmed users | ✅ OK (but weak) |
| **Register file** | `/files/upload/` | `@login_required` | ADMIN, DATA_MANAGER, RESEARCHER | ❌ **ANY user can register** |
| **Edit file** | `/files/edit/<id>/` | `@login_required` | ADMIN, DATA_MANAGER, RESEARCHER | ❌ **ANY user can edit** |
| **Delete file** | `/files/delete/<id>/` | `@login_required` | ADMIN, DATA_MANAGER | ❌ **ANY user can delete** |

**Reference:** `cholestrack/files/views.py`

**Critical Issue:**
```python
# Current implementation (files/views.py:271)
@login_required
def file_upload(request):
    # NO role checking!
    # Any authenticated user can register files
```

**Note:** The `download_file` view has a TODO comment acknowledging missing permission checks:
```python
# files/views.py:55-65
# TODO: Implement granular permission checking
# Current implementation assumes all authenticated users have access
# Future enhancement should verify:
# - User has permission to access this specific patient's data
# - User's role permits downloading this file type
# - File access has been approved by responsible researcher
```

---

### ✅ **Region Selection App** (`/region-selection/`)

**Security Status:** 🟢 **PARTIALLY PROTECTED**

| Feature | Endpoint | Current Protection | Allowed Roles |
|---------|----------|-------------------|---------------|
| Create extraction | `/region-selection/create/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| View extraction job | `/region-selection/job/<uuid>/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| Download extraction | `/region-selection/download/<uuid>/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| List jobs | `/region-selection/jobs/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |

**Reference:** `cholestrack/region_selection/views.py`

**Current Implementation:**
```python
# region_selection/views.py:31-33
@login_required
@role_confirmed_required
def create_extraction(request):
    # Only requires admin-confirmed role
    # Does not restrict by specific role type
```

**What Users Can Do:**
- ✅ **ADMIN:** Full access to create and download BAM region extractions
- ✅ **DATA_MANAGER:** Full access to create and download BAM region extractions
- ✅ **RESEARCHER:** Full access to create and download BAM region extractions
- ✅ **CLINICIAN:** Full access to create and download BAM region extractions

---

### ✅ **Smart Search App** (`/smart-search/`)

**Security Status:** 🟢 **PARTIALLY PROTECTED**

| Feature | Endpoint | Current Protection | Allowed Roles |
|---------|----------|-------------------|---------------|
| Search home | `/smart-search/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| View results | `/smart-search/result/<id>/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| Search history | `/smart-search/history/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |

**Reference:** `cholestrack/smart_search/views.py`

**What Users Can Do:**
- ✅ **All confirmed users** can search genes in HPO database
- ✅ **All confirmed users** can view phenotype and disease associations
- ✅ **All confirmed users** can access their search history

---

### ✅ **Analysis Workflows App** (`/analysis-workflows/`)

**Security Status:** 🟢 **PARTIALLY PROTECTED**

| Feature | Endpoint | Current Protection | Allowed Roles |
|---------|----------|-------------------|---------------|
| Config builder | `/analysis-workflows/builder/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| Preview config | `/analysis-workflows/preview/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| Download config | `/analysis-workflows/download/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |
| Saved configs | `/analysis-workflows/saved/` | `@login_required` + `@role_confirmed_required` | ALL confirmed roles |

**Reference:** `cholestrack/analysis_workflows/views.py`

**What Users Can Do:**
- ✅ **All confirmed users** can build workflow configurations
- ✅ **All confirmed users** can save and download YAML configs
- ✅ Users only see their own saved configurations

---

### 🟡 **Home/Dashboard** (`/home/`)

**Security Status:** 🟡 **BASIC PROTECTION**

| Feature | Endpoint | Current Protection | Notes |
|---------|----------|-------------------|-------|
| Dashboard | `/home/dashboard/` | `@login_required` | Redirects to profile if incomplete |

**Reference:** `cholestrack/home/views.py`

---

### 🟡 **Profile App** (`/profile/`)

**Security Status:** 🟡 **BASIC PROTECTION**

| Feature | Endpoint | Current Protection | Notes |
|---------|----------|-------------------|-------|
| Create profile | `/profile/create/` | `@login_required` | First-time setup |
| Edit profile | `/profile/edit/` | `@login_required` | Users can edit own profile |

**Reference:** `cholestrack/profile/views.py`

**Template shows role status:**
- Template `profile/edit_profile.html:249-251` displays role confirmation status
- Shows user's current role if confirmed by admin

---

## Summary Table: What Each Role Can Actually Do

### 🔴 Current Reality (Without Enforcement)

| Feature | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN | Status |
|---------|:-----:|:------------:|:----------:|:---------:|--------|
| **View samples** | ✅ | ✅ | ✅ | ✅ | ⚠️ Any logged-in user |
| **Create patients** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Edit patients** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Delete patients** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Register files** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Edit file metadata** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Delete files** | ✅ | ✅ | ✅ | ✅ | ⚠️ ANY logged-in user |
| **Download files** | ✅ | ✅ | ✅ | ✅ | ⚠️ Any logged-in user |
| **BAM region extraction** | ✅ | ✅ | ✅ | ✅ | 🟢 Confirmed users only |
| **HPO gene search** | ✅ | ✅ | ✅ | ✅ | 🟢 Confirmed users only |
| **Workflow builder** | ✅ | ✅ | ✅ | ✅ | 🟢 Confirmed users only |

### ✅ Intended Design (Permission Methods)

| Feature | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN |
|---------|:-----:|:------------:|:----------:|:---------:|
| **View samples** | ✅ | ✅ | ✅ | ✅ |
| **Create patients** | ✅ | ✅ | ✅ | ❌ |
| **Edit patients** | ✅ | ✅ | ✅ | ❌ |
| **Delete patients** | ✅ | ✅ | ❌ | ❌ |
| **Register files** | ✅ | ✅ | ✅ | ❌ |
| **Edit file metadata** | ✅ | ✅ | ✅ | ❌ |
| **Delete files** | ✅ | ✅ | ❌ | ❌ |
| **Download files** | ✅ | ✅ | ✅ | ✅ |
| **BAM region extraction** | ✅ | ✅ | ✅ | ✅ |
| **HPO gene search** | ✅ | ✅ | ✅ | ✅ |
| **Workflow builder** | ✅ | ✅ | ✅ | ✅ |

---

## Available Decorators

The system provides the following decorators for access control:

### 1. `@role_required(['ADMIN', 'DATA_MANAGER', ...])`
**Location:** `cholestrack/users/decorators.py:11-69`

Checks:
1. ✅ User is authenticated
2. ✅ Email is verified
3. ✅ User has a role assigned
4. ✅ Role is confirmed by admin
5. ✅ User's role is in the allowed list

**Usage:**
```python
from users.decorators import role_required

@role_required(['ADMIN', 'DATA_MANAGER'])
def my_protected_view(request):
    # Only ADMIN and DATA_MANAGER can access
    pass
```

### 2. `@email_verified_required`
**Location:** `cholestrack/users/decorators.py:72-97`

Checks:
1. ✅ User is authenticated
2. ✅ Email is verified

### 3. `@role_confirmed_required`
**Location:** `cholestrack/users/decorators.py:100-127`

Checks:
1. ✅ User is authenticated
2. ✅ User has a role assigned
3. ✅ Role is confirmed by admin

**Does NOT check:** Specific role type (ADMIN vs CLINICIAN)

---

## Template-Level Permission Checking

Currently, templates show UI elements without checking user roles:

### samples/sample_list.html (Lines 17-28)
```html
<!-- NO permission check! -->
<a href="{% url 'samples:patient_create' %}" class="btn btn-success">
    Add New Patient
</a>
<a href="{% url 'files:file_upload' %}" class="btn btn-info">
    Register File Location
</a>
```

**Issue:** Buttons are shown to ALL users, even though CLINICIAN shouldn't create/edit data.

**Should be:**
```html
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

---

## Critical Security Issues

### 🔴 Issue #1: No Role Enforcement in Samples App
**Severity:** HIGH
**Impact:** ANY authenticated user (including CLINICIAN) can create, edit, and delete patients

**Affected Views:**
- `samples/views.py:125` - `patient_create()`
- `samples/views.py:147` - `patient_edit()`
- `samples/views.py:176` - `patient_delete()`

### 🔴 Issue #2: No Role Enforcement in Files App
**Severity:** HIGH
**Impact:** ANY authenticated user (including CLINICIAN) can register, edit, and delete file locations

**Affected Views:**
- `files/views.py:271` - `file_upload()`
- `files/views.py:297` - `file_edit()`
- `files/views.py:329` - `file_delete()`

### 🟡 Issue #3: UI Shows Actions User Cannot Perform
**Severity:** MEDIUM
**Impact:** Confusing UX - users see buttons they shouldn't use

**Affected Templates:**
- `templates/samples/sample_list.html` - Shows "Add Patient" to all users
- `templates/samples/sample_list.html` - Shows "Register File" to all users

### 🟡 Issue #4: Missing Granular Download Permissions
**Severity:** MEDIUM
**Impact:** No per-patient access control - users can download any patient's files

**Affected Views:**
- `files/views.py:18` - `download_file()` has TODO comment acknowledging this

---

## Recommendations for Fixing RBAC

### 1. Add Role Decorators to Sample Views
```python
# samples/views.py
from users.decorators import role_required

@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def patient_create(request):
    # ...

@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def patient_edit(request, patient_id):
    # ...

@login_required
@role_required(['ADMIN', 'DATA_MANAGER'])
def patient_delete(request, patient_id):
    # ...
```

### 2. Add Role Decorators to File Views
```python
# files/views.py
from users.decorators import role_required

@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def file_upload(request):
    # ...

@login_required
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def file_edit(request, file_location_id):
    # ...

@login_required
@role_required(['ADMIN', 'DATA_MANAGER'])
def file_delete(request, file_location_id):
    # ...
```

### 3. Update Templates with Permission Checks
```html
<!-- templates/samples/sample_list.html -->
{% if user.role.can_create_patient %}
    <a href="{% url 'samples:patient_create' %}" class="btn btn-success">
        <i class="fas fa-user-plus"></i> Add New Patient
    </a>
{% endif %}

{% if user.role.can_create_file %}
    <a href="{% url 'files:file_upload' %}" class="btn btn-info">
        <i class="fas fa-file-upload"></i> Register File Location
    </a>
{% endif %}
```

### 4. Implement Granular Download Permissions
Add project-level or patient-level access control to restrict which patients' data a user can access.

---

## Testing RBAC

### Manual Testing Steps

1. **Create test users for each role:**
   ```bash
   python manage.py createsuperuser  # ADMIN
   # Create other users via /register/ and assign roles in admin
   ```

2. **Test as CLINICIAN:**
   - ❌ Should NOT see "Add Patient" button
   - ❌ Should NOT access `/samples/create/`
   - ✅ Should view sample list
   - ✅ Should download files

3. **Test as RESEARCHER:**
   - ✅ Should create patients
   - ✅ Should edit patients
   - ❌ Should NOT delete patients
   - ✅ Should register files

4. **Test as DATA_MANAGER:**
   - ✅ Should create/edit/delete patients
   - ✅ Should register/edit/delete files
   - ✅ Full access except admin panel

5. **Test as ADMIN:**
   - ✅ Should have full access to everything

---

## Code References

### Models
- `cholestrack/users/models.py:68-160` - UserRole model with permission methods

### Decorators
- `cholestrack/users/decorators.py:11-69` - `@role_required()`
- `cholestrack/users/decorators.py:72-97` - `@email_verified_required`
- `cholestrack/users/decorators.py:100-127` - `@role_confirmed_required`

### Views Needing Fixes
- `cholestrack/samples/views.py` - All CRUD operations
- `cholestrack/files/views.py` - All CRUD operations

### Protected Views (Examples)
- `cholestrack/region_selection/views.py:31-33` - Using `@role_confirmed_required`
- `cholestrack/smart_search/views.py:16-18` - Using `@role_confirmed_required`

---

## Conclusion

**Current Status:** The RBAC infrastructure is in place (roles, permission methods, decorators) but **enforcement is incomplete**.

**Main Issues:**
1. ❌ Samples app has no role-based restrictions
2. ❌ Files app has no role-based restrictions
3. ⚠️ Templates don't check permissions before showing actions
4. ⚠️ No patient-level access control

**Next Steps:**
1. Apply `@role_required` decorators to samples and files views
2. Update templates to conditionally show UI elements
3. Implement patient-level access control (optional, for multi-project scenarios)
4. Add automated tests for RBAC enforcement

---

**Document Version:** 1.0
**Last Updated:** 2025-11-20
**Author:** Claude (Automated Analysis)
