# profile/admin.py
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'role', 'team', 'profile_completed', 'approved', 'created_at')
    list_filter = ('role', 'team', 'profile_completed', 'approved')
    search_fields = ('user__username', 'user__email', 'full_name', 'institutional_email', 'institution_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'institutional_email')
        }),
        ('Institutional Details', {
            'fields': ('role', 'team', 'institution_id', 'phone')
        }),
        ('Status', {
            'fields': ('profile_completed', 'approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )