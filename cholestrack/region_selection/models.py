# region_selection/models.py
"""
Models for region extraction tracking and temporary file management.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class RegionExtractionJob(models.Model):
    """
    Tracks region extraction jobs for BAM files.
    Manages temporary files and cleanup.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('DOWNLOADED', 'Downloaded'),
        ('EXPIRED', 'Expired'),
    ]

    # Job identification
    job_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Job ID",
        help_text="Unique identifier for this extraction job"
    )

    # User and sample information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='region_extractions',
        verbose_name="User"
    )

    sample_id = models.CharField(
        max_length=50,
        verbose_name="Sample ID",
        help_text="Sample ID for the BAM file"
    )

    # Region specification (either gene or coordinates)
    gene_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Gene Name",
        help_text="Gene name for region extraction (e.g., BRCA1)"
    )

    chromosome = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Chromosome",
        help_text="Chromosome (e.g., chr1, 1, X, Y)"
    )

    start_position = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Start Position",
        help_text="Start position in base pairs"
    )

    end_position = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="End Position",
        help_text="End position in base pairs"
    )

    # File information
    original_bam_file = models.ForeignKey(
        'files.AnalysisFileLocation',
        on_delete=models.CASCADE,
        related_name='region_extractions',
        verbose_name="Original BAM File"
    )

    output_file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Output File Path",
        help_text="Path to the extracted BAM file in temporary storage"
    )

    output_file_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Output File Size (MB)"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Status"
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Error Message"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    processing_started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Processing Started At"
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Completed At"
    )

    downloaded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Downloaded At"
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Expires At",
        help_text="When this temporary file should be deleted (10 minutes after completion)"
    )

    class Meta:
        verbose_name = "Region Extraction Job"
        verbose_name_plural = "Region Extraction Jobs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.gene_name:
            region = f"Gene: {self.gene_name}"
        else:
            region = f"{self.chromosome}:{self.start_position}-{self.end_position}"
        return f"{self.sample_id} - {region} ({self.status})"

    def get_region_string(self):
        """Returns the region specification in samtools format."""
        if self.chromosome and self.start_position and self.end_position:
            # Ensure chromosome has 'chr' prefix for samtools (e.g., 'chr6:32578770-32589836')
            chr_name = self.chromosome if self.chromosome.startswith('chr') else f'chr{self.chromosome}'
            return f"{chr_name}:{self.start_position}-{self.end_position}"
        return None

    def is_expired(self):
        """Check if this job has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def set_expiration(self, minutes=10):
        """Set expiration time for this job."""
        self.expires_at = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['expires_at'])

    def mark_downloaded(self):
        """Mark this job as downloaded."""
        self.status = 'DOWNLOADED'
        self.downloaded_at = timezone.now()
        self.save(update_fields=['status', 'downloaded_at'])
