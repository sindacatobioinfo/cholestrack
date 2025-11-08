# users/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# The users app focuses exclusively on authentication.
# User profile management is handled by the profile app.
# Patient and file data are managed by the samples and files apps respectively.

# If you want to customize the default User admin, you can do so here.
# Otherwise, Django's default UserAdmin is sufficient for basic user management.