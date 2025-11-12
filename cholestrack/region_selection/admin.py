# region_selection/admin.py
"""
Admin configuration for region extraction models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import RegionExtractionJob


@admin.register(RegionExtractionJob)
class RegionExtractionJobAdmin(admin.ModelAdmin):
    """
    Admin interface for RegionExtractionJob model.
    """

    list_display = [
        'job_id_short',
        'user',
        'sample_id',
        'region_display',
        'status_badge',
        'created_at',
        'expires_at',
        'file_size_display'
    ]

    list_filter = [
        'status',
        'created_at',
        'completed_at',
    ]

    search_fields = [
        'job_id',
        'user__username',
        'sample_id',
        'gene_name',
        'chromosome'
    ]

    readonly_fields = [
        'job_id',
        'created_at',
        'processing_started_at',
        'completed_at',
        'downloaded_at',
        'output_file_size_mb'
    ]

    fieldsets = (
        ('Job Information', {
            'fields': (
                'job_id',
                'user',
                'status',
                'error_message'
            )
        }),
        ('Sample and Region', {
            'fields': (
                'sample_id',
                'original_bam_file',
                'gene_name',
                'chromosome',
                'start_position',
                'end_position'
            )
        }),
        ('Output', {
            'fields': (
                'output_file_path',
                'output_file_size_mb'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'processing_started_at',
                'completed_at',
                'downloaded_at',
                'expires_at'
            )
        }),
    )

    def job_id_short(self, obj):
        """Display shortened job ID."""
        return str(obj.job_id)[:8]
    job_id_short.short_description = 'Job ID'

    def region_display(self, obj):
        """Display region information."""
        if obj.gene_name:
            return f"Gene: {obj.gene_name}"
        elif obj.chromosome:
            return f"{obj.chromosome}:{obj.start_position}-{obj.end_position}"
        return "N/A"
    region_display.short_description = 'Region'

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'PENDING': 'gray',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'DOWNLOADED': 'purple',
            'EXPIRED': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def file_size_display(self, obj):
        """Display file size with formatting."""
        if obj.output_file_size_mb:
            return f"{obj.output_file_size_mb} MB"
        return "N/A"
    file_size_display.short_description = 'File Size'

    actions = ['mark_as_expired', 'cleanup_files']

    def mark_as_expired(self, request, queryset):
        """Mark selected jobs as expired."""
        updated = queryset.update(status='EXPIRED')
        self.message_user(request, f'{updated} job(s) marked as expired.')
    mark_as_expired.short_description = 'Mark selected jobs as expired'

    def cleanup_files(self, request, queryset):
        """Clean up temporary files for selected jobs."""
        from .utils import cleanup_job_files
        cleaned = 0
        for job in queryset:
            if cleanup_job_files(job):
                cleaned += 1
        self.message_user(request, f'Cleaned up files for {cleaned} job(s).')
    cleanup_files.short_description = 'Clean up temporary files'
