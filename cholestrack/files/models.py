# files/models.py
from django.db import models
from django.contrib.auth.models import User

class AnalysisFileLocation(models.Model):
    """
    Central registry for genomic analysis file locations.
    This model provides secure file metadata management without exposing internal server paths.
    Acts as the interface between sample records and physical file storage infrastructure.
    """
    # Reference to the patient (foreign key to samples.Patient)
    # We use string reference to avoid circular imports
    patient = models.ForeignKey(
        'samples.Patient',
        on_delete=models.CASCADE, 
        related_name='file_locations',
        verbose_name="Patient"
    )
    
    # Sample metadata fields
    project_name = models.CharField(
        max_length=50, 
        verbose_name="Project",
        help_text="Research project or study identifier"
    )
    batch_id = models.CharField(
        max_length=50, 
        verbose_name="Batch",
        help_text="Sequencing batch identifier"
    )
    sample_id = models.CharField(
        max_length=50, 
        verbose_name="Sample ID",
        help_text="Laboratory sample identifier",
        db_index=True
    )
    
    DATA_TYPE_CHOICES = [
        ('WGS', 'Whole Genome Sequencing'),
        ('WES', 'Whole Exome Sequencing'),
        ('RNA', 'RNA-Seq'),
        ('PANEL', 'Gene Panel'),
        ('OTHER', 'Other'),
    ]
    data_type = models.CharField(
        max_length=10, 
        choices=DATA_TYPE_CHOICES, 
        default='WES', 
        verbose_name="Data Type"
    )
    
    SERVER_CHOICES = [
        ('SERVER1', 'BioHub Main Server'),
        ('SERVER2', 'Burlo Garofolo Archive'),
        ('SERVER3', 'Backup/FTP Server'),
    ]
    server_name = models.CharField(
        max_length=10, 
        choices=SERVER_CHOICES, 
        verbose_name="Server Location"
    )
    
    file_path = models.CharField(
        max_length=500, 
        verbose_name="File Path",
        help_text="Relative path to the file on the server (internal use only, never exposed to client)"
    )
    
    FILE_TYPE_CHOICES = [
        ('VCF', 'VCF - Variant Call Format'),
        ('BAM', 'BAM - Binary Alignment Map'),
        ('FASTQ', 'FASTQ - Raw Sequencing Data'),
        ('PDF', 'PDF - Analysis Report'),
        ('TSV', 'TSV - Tabular Data'),
        ('CRAM', 'CRAM - Compressed Alignment'),
    ]
    file_type = models.CharField(
        max_length=10, 
        choices=FILE_TYPE_CHOICES,
        default="VCF", 
        verbose_name="File Type"
    )
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='uploaded_files',
        verbose_name="Uploaded By"
    )
    
    file_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="File Size (MB)",
        help_text="File size in megabytes for tracking storage usage"
    )
    
    checksum = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="File Checksum (MD5)",
        help_text="MD5 hash for file integrity verification"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Set to False to soft-delete files without removing database records"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    def __str__(self):
        return f"{self.patient.patient_id} - {self.sample_id} ({self.data_type}) - {self.file_type}"
    
    def get_full_server_path(self):
        """
        Constructs the complete internal server path for file access.
        This method should only be called by authorized file serving functions.
        """
        return f"/{self.server_name.lower()}_data/{self.file_path}"
    
    class Meta:
        verbose_name = "Analysis File Location"
        verbose_name_plural = "Analysis File Locations"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sample_id', 'file_type']),
            models.Index(fields=['patient', 'is_active']),
        ]