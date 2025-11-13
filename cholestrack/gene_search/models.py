# gene_search/models.py
"""
Models for gene/disease/drug search and relationship tracking.
Caches API results from HPO, OMIM, and PharmGKB to minimize external API calls.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class GeneSearchQuery(models.Model):
    """
    Track gene/disease/drug searches and cache results from external APIs.
    Stores HPO phenotypes, OMIM diseases, and PharmGKB pharmacogenetics data.
    """
    SEARCH_TYPE_CHOICES = [
        ('GENE', 'Gene'),
        ('DISEASE', 'Disease'),
        ('DRUG', 'Drug'),
    ]

    # Search information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='gene_searches',
        verbose_name="User"
    )

    search_term = models.CharField(
        max_length=200,
        verbose_name="Search Term",
        help_text="Gene name (e.g., ATP8B1, BRCA1), disease name, or drug name"
    )

    search_type = models.CharField(
        max_length=20,
        choices=SEARCH_TYPE_CHOICES,
        default='GENE',
        verbose_name="Search Type"
    )

    # Cached results (stored as JSON)
    hpo_results = models.JSONField(
        null=True,
        blank=True,
        verbose_name="HPO Results",
        help_text="Human Phenotype Ontology phenotypes and terms"
    )

    omim_results = models.JSONField(
        null=True,
        blank=True,
        verbose_name="OMIM Results",
        help_text="OMIM disease information with IDs and names"
    )

    pharmgkb_results = models.JSONField(
        null=True,
        blank=True,
        verbose_name="PharmGKB Results",
        help_text="Pharmacogenetics information (ADME genes, drug response variants)"
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    cache_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Cache Expires At",
        help_text="When cached results should be refreshed (default 7 days)"
    )

    success = models.BooleanField(
        default=True,
        verbose_name="Success",
        help_text="Whether the search was successful"
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Error Message"
    )

    class Meta:
        verbose_name = "Gene Search Query"
        verbose_name_plural = "Gene Search Queries"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['search_term', 'search_type']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f"{self.search_term} ({self.search_type}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def is_cache_valid(self):
        """Check if cached results are still valid."""
        if not self.cache_expires_at:
            return False
        return timezone.now() < self.cache_expires_at

    def set_cache_expiration(self, days=7):
        """Set cache expiration time (default 7 days)."""
        self.cache_expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['cache_expires_at'])

    def get_hpo_count(self):
        """Get count of HPO terms."""
        if self.hpo_results and isinstance(self.hpo_results, list):
            return len(self.hpo_results)
        return 0

    def get_omim_count(self):
        """Get count of OMIM diseases."""
        if self.omim_results and isinstance(self.omim_results, list):
            return len(self.omim_results)
        return 0

    def get_pharmgkb_count(self):
        """Get count of PharmGKB entries."""
        if self.pharmgkb_results and isinstance(self.pharmgkb_results, list):
            return len(self.pharmgkb_results)
        return 0
