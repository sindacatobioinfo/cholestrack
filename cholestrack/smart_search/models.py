# smart_search/models.py
"""
Models for gene search and HPO relationship tracking.
Caches API results from HPO to minimize external API calls.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class GeneSearchQuery(models.Model):
    """
    Track gene searches and cache HPO results (phenotypes and diseases).
    Stores HPO phenotypes and associated diseases for each gene.
    """

    # Search information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='smart_searches',
        verbose_name="User"
    )

    search_term = models.CharField(
        max_length=200,
        verbose_name="Search Term",
        help_text="Gene symbol (e.g., ATP8B1, BRCA1)"
    )

    # Cached results (stored as JSON)
    phenotypes = models.JSONField(
        null=True,
        blank=True,
        verbose_name="HPO Phenotypes",
        help_text="Human Phenotype Ontology phenotype terms"
    )

    diseases = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Associated Diseases",
        help_text="Diseases associated with the gene from HPO database"
    )

    gene_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Gene Information",
        help_text="Gene metadata from HPO"
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
        verbose_name = "Smart Search Query"
        verbose_name_plural = "Smart Search Queries"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['search_term']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f"{self.search_term} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def is_cache_valid(self):
        """Check if cached results are still valid."""
        if not self.cache_expires_at:
            return False
        return timezone.now() < self.cache_expires_at

    def set_cache_expiration(self, days=7):
        """Set cache expiration time (default 7 days)."""
        self.cache_expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['cache_expires_at'])

    def get_phenotype_count(self):
        """Get count of HPO phenotype terms."""
        if self.phenotypes and isinstance(self.phenotypes, list):
            return len(self.phenotypes)
        return 0

    def get_disease_count(self):
        """Get count of associated diseases."""
        if self.diseases and isinstance(self.diseases, list):
            return len(self.diseases)
        return 0
