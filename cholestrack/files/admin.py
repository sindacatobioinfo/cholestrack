# files/admin.py
from django.contrib import admin
from .models import AnalysisFileLocation

@admin.register(AnalysisFileLocation)
class AnalysisFileLocationAdmin(admin.ModelAdmin):
    list_display = (
        'patient', 
        'sample_id', 
        'project_name', 
        'data_type', 
        'file_type', 
        'server_name', 
        'file_size_mb',
        'is_active',
        'created_at'
    )
    list_filter = (
        'project_name', 
        'data_type', 
        'server_name', 
        'file_type', 
        'is_active',
        'created_at'
    )
    search_fields = (
        'patient__patient_id', 
        'patient__name', 
        'sample_id', 
        'file_path'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Patient Reference', {
            'fields': ('patient',)
        }),
        ('Sample Metadata', {
            'fields': ('project_name', 'batch_id', 'sample_id', 'data_type')
        }),
        ('File Information', {
            'fields': ('file_type', 'file_size_mb', 'checksum')
        }),
        ('Storage Location', {
            'fields': ('server_name', 'file_path'),
            'description': 'Internal server configuration - file paths are not exposed to end users'
        }),
        ('Management', {
            'fields': ('uploaded_by', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize admin queries by prefetching related objects."""
        return super().get_queryset(request).select_related('patient', 'uploaded_by')