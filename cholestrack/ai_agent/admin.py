"""
Admin interface for AI Agent models.
"""

from django.contrib import admin
from .models import ChatSession, ChatMessage, AnalysisJob


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'title', 'created_at', 'updated_at', 'is_active', 'total_tokens_used')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('title', 'user__username', 'session_id')
    readonly_fields = ('session_id', 'created_at', 'updated_at', 'total_tokens_used')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'user', 'title', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
        ('Usage', {
            'fields': ('total_tokens_used',)
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'session', 'role', 'content_preview', 'created_at', 'tokens_used', 'has_analysis_job')
    list_filter = ('role', 'has_analysis_job', 'created_at')
    search_fields = ('content', 'session__title', 'session__user__username')
    readonly_fields = ('message_id', 'created_at', 'tokens_used')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message Info', {
            'fields': ('message_id', 'session', 'role', 'content')
        }),
        ('Analysis', {
            'fields': ('has_analysis_job', 'metadata')
        }),
        ('Metadata', {
            'fields': ('created_at', 'tokens_used')
        }),
    )

    def content_preview(self, obj):
        """Show preview of message content."""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'job_type', 'status', 'session', 'created_at', 'completed_at', 'duration')
    list_filter = ('job_type', 'status', 'created_at', 'result_file_type')
    search_fields = ('job_id', 'session__title', 'session__user__username', 'sample_ids')
    readonly_fields = ('job_id', 'created_at', 'started_at', 'completed_at', 'duration')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Job Info', {
            'fields': ('job_id', 'session', 'message', 'job_type', 'status')
        }),
        ('Parameters', {
            'fields': ('parameters', 'sample_ids')
        }),
        ('Results', {
            'fields': ('result_data', 'result_file_path', 'result_file_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def duration(self, obj):
        """Display job duration."""
        duration_seconds = obj.get_duration_seconds()
        if duration_seconds:
            return f"{duration_seconds:.2f}s"
        return "-"
    duration.short_description = 'Duration'
