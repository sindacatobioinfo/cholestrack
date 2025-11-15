# analysis_workflows/models.py
"""
Models for analysis workflow configuration.
"""

from django.db import models
from django.contrib.auth.models import User


class WorkflowConfiguration(models.Model):
    """
    Stores workflow configuration for tracking and reuse.
    """
    ALIGNER_CHOICES = [
        ('bwa', 'BWA-MEM'),
        ('dragmap', 'DRAGEN DRAGMAP'),
        ('minimap2', 'Minimap2'),
    ]

    MINIMAP2_PRESET_CHOICES = [
        ('sr', 'Short reads (Illumina)'),
        ('map-ont', 'Oxford Nanopore'),
        ('map-pb', 'PacBio CLR'),
        ('map-hifi', 'PacBio HiFi/CCS'),
        ('asm5', 'Assembly-to-ref (e95% identity)'),
        ('asm10', 'Assembly-to-ref (e90% identity)'),
        ('asm20', 'Assembly-to-ref (e80% identity)'),
    ]

    # User and metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workflow_configs',
        verbose_name="User"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Configuration Name",
        help_text="Descriptive name for this configuration"
    )
    project_name = models.CharField(
        max_length=200,
        default='workflow_test',
        verbose_name="Project Name",
        help_text="Project name for input/output directory structure"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Aligner configuration
    aligner = models.CharField(
        max_length=20,
        choices=ALIGNER_CHOICES,
        default='minimap2',
        verbose_name="Alignment Tool"
    )
    minimap2_preset = models.CharField(
        max_length=20,
        choices=MINIMAP2_PRESET_CHOICES,
        default='sr',
        blank=True,
        verbose_name="Minimap2 Preset"
    )

    # Variant callers
    use_gatk = models.BooleanField(
        default=True,
        verbose_name="Use GATK HaplotypeCaller"
    )
    use_strelka = models.BooleanField(
        default=True,
        verbose_name="Use Strelka2"
    )

    # Annotation tools
    run_annovar = models.BooleanField(
        default=False,
        verbose_name="Run ANNOVAR"
    )
    run_vep = models.BooleanField(
        default=True,
        verbose_name="Run VEP"
    )

    class Meta:
        verbose_name = "Workflow Configuration"
        verbose_name_plural = "Workflow Configurations"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username}) - {self.aligner}"
