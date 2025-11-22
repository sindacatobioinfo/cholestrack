"""
AI Agent models for chat sessions, messages, and analysis jobs.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatSession(models.Model):
    """
    Represents a conversation session with the AI agent.
    """
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    total_tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.session_id})"

    def update_title_from_first_message(self):
        """Auto-generate title from first user message."""
        first_message = self.messages.filter(role='user').first()
        if first_message:
            # Take first 50 characters of first message
            self.title = first_message.content[:50]
            if len(first_message.content) > 50:
                self.title += '...'
            self.save()


class ChatMessage(models.Model):
    """
    Individual messages within a chat session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(default=0, help_text='Number of tokens used for this message')

    # Optional metadata for analysis results
    has_analysis_job = models.BooleanField(default=False)
    metadata = models.JSONField(null=True, blank=True, help_text='Additional metadata (e.g., file references, analysis parameters)')

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        preview = self.content[:50]
        return f"{self.role}: {preview}..."


class AnalysisJob(models.Model):
    """
    Background analysis jobs triggered by AI agent conversations.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    JOB_TYPE_CHOICES = [
        ('STATISTICAL', 'Statistical Analysis'),
        ('VARIANT_INTERPRETATION', 'Variant Interpretation'),
        ('COMPARATIVE', 'Comparative Analysis'),
        ('GENETIC_MODEL', 'Genetic Model Filtering'),
        ('CUSTOM_QUERY', 'Custom Query'),
        ('REPORT_GENERATION', 'Report Generation'),
    ]

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='analysis_jobs')
    message = models.ForeignKey(ChatMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='analysis_job')

    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')

    # Job parameters and data
    parameters = models.JSONField(help_text='Analysis parameters and configuration')
    sample_ids = models.JSONField(default=list, help_text='List of sample IDs to analyze')

    # Results
    result_data = models.JSONField(null=True, blank=True, help_text='Analysis results')
    result_file_path = models.CharField(max_length=500, null=True, blank=True, help_text='Path to generated report file')
    result_file_type = models.CharField(max_length=10, null=True, blank=True, choices=[('html', 'HTML'), ('csv', 'CSV'), ('xlsx', 'Excel')])

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} - {self.status} ({self.job_id})"

    def mark_started(self):
        """Mark job as started."""
        self.status = 'PROCESSING'
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self, result_data=None, result_file_path=None, result_file_type=None):
        """Mark job as completed with results."""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        if result_file_path:
            self.result_file_path = result_file_path
            self.result_file_type = result_file_type
        self.save()

    def mark_failed(self, error_message):
        """Mark job as failed with error message."""
        self.status = 'FAILED'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()

    def get_duration_seconds(self):
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
