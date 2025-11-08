# samples/admin.py
from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'patient_id', 
        'name', 
        'birth_date', 
        'main_exome_result', 
        'responsible_user', 
        'get_file_count',
        'created_at'
    )
    search_fields = ('patient_id', 'name')
    list_filter = ('main_exome_result', 'responsible_user', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'get_file_count')
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_id', 'name', 'birth_date')
        }),
        ('Clinical Data', {
            'fields': ('clinical_info_json', 'main_exome_result', 'notes')
        }),
        ('Management', {
            'fields': ('responsible_user', 'get_file_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_file_count(self, obj):
        """Display the count of active files for this patient."""
        return obj.get_file_count()
    get_file_count.short_description = 'Number of Files'