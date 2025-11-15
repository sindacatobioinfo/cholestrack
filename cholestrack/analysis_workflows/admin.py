# analysis_workflows/admin.py
"""
Django admin configuration for analysis_workflows app.
"""

from django.contrib import admin
from .models import WorkflowConfiguration


@admin.register(WorkflowConfiguration)
class WorkflowConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'aligner', 'use_gatk', 'use_strelka', 'run_annovar', 'run_vep', 'created_at']
    list_filter = ['aligner', 'use_gatk', 'use_strelka', 'run_annovar', 'run_vep', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Configuration Info', {
            'fields': ('user', 'name', 'created_at', 'updated_at')
        }),
        ('Alignment', {
            'fields': ('aligner', 'minimap2_preset')
        }),
        ('Variant Calling', {
            'fields': ('use_gatk', 'use_strelka')
        }),
        ('Annotation', {
            'fields': ('run_annovar', 'run_vep')
        }),
    )
