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

    SEARCH_TYPE_CHOICES = [
        ('gene', 'Gene'),
        ('phenotype', 'Phenotype'),
        ('disease', 'Disease'),
        ('variant', 'Variant'),
    ]

    search_type = models.CharField(
        max_length=20,
        choices=SEARCH_TYPE_CHOICES,
        default='gene',
        verbose_name="Search Type",
        help_text="Type of search: gene or phenotype"
    )

    search_term = models.CharField(
        max_length=200,
        verbose_name="Search Term",
        help_text="Gene symbol (e.g., ATP8B1, BRCA1) or phenotype name"
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

    clinpgx_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="ClinPGx Data",
        help_text="Pharmacogenomic data from ClinPGx API"
    )

    clinpgx_drug_labels = models.JSONField(
        null=True,
        blank=True,
        verbose_name="ClinPGx Drug Labels",
        help_text="Drug label annotations from ClinPGx API"
    )

    variant_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Variant Data",
        help_text="Variant information from Ensembl API"
    )

    clinpgx_variant_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="ClinPGx Variant Data",
        help_text="Variant annotation data from ClinPGx API"
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

    @property
    def get_phenotype_count(self):
        """Get count of HPO phenotype terms."""
        if self.phenotypes and isinstance(self.phenotypes, list):
            return len(self.phenotypes)
        return 0

    @property
    def get_disease_count(self):
        """Get count of associated diseases."""
        if self.diseases and isinstance(self.diseases, list):
            return len(self.diseases)
        return 0


# =============================================================================
# HPO Local Database Models
# =============================================================================


class HPOTerm(models.Model):
    """
    HPO phenotype term from the Human Phenotype Ontology.
    """
    hpo_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="HPO ID",
        help_text="HPO term identifier (e.g., HP:0000001)"
    )

    name = models.CharField(
        max_length=500,
        verbose_name="Term Name",
        help_text="Human-readable name of the phenotype"
    )

    definition = models.TextField(
        blank=True,
        null=True,
        verbose_name="Definition",
        help_text="Description of the phenotype term"
    )

    class Meta:
        verbose_name = "HPO Term"
        verbose_name_plural = "HPO Terms"
        ordering = ['hpo_id']
        indexes = [
            models.Index(fields=['hpo_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.hpo_id}: {self.name}"


class Gene(models.Model):
    """
    Gene information from HPO annotations.
    """
    entrez_id = models.IntegerField(
        unique=True,
        db_index=True,
        verbose_name="Entrez Gene ID",
        help_text="NCBI Entrez Gene ID"
    )

    gene_symbol = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Gene Symbol",
        help_text="Official gene symbol (e.g., ATP8B1)"
    )

    class Meta:
        verbose_name = "Gene"
        verbose_name_plural = "Genes"
        ordering = ['gene_symbol']
        indexes = [
            models.Index(fields=['entrez_id']),
            models.Index(fields=['gene_symbol']),
        ]

    def __str__(self):
        return f"{self.gene_symbol} (Entrez:{self.entrez_id})"


class Disease(models.Model):
    """
    Disease information from HPO annotations.
    """
    database_id = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        verbose_name="Database ID",
        help_text="Disease identifier (e.g., OMIM:123456)"
    )

    disease_name = models.CharField(
        max_length=500,
        verbose_name="Disease Name",
        help_text="Name of the disease"
    )

    database = models.CharField(
        max_length=100,
        default="OMIM",
        verbose_name="Database",
        help_text="Source database (OMIM, ORPHA, DECIPHER, etc.)"
    )

    class Meta:
        verbose_name = "Disease"
        verbose_name_plural = "Diseases"
        ordering = ['disease_name']
        indexes = [
            models.Index(fields=['database_id']),
            models.Index(fields=['database']),
        ]

    def __str__(self):
        return f"{self.database_id}: {self.disease_name}"


class GenePhenotypeAssociation(models.Model):
    """
    Association between genes and HPO phenotype terms.
    """
    gene = models.ForeignKey(
        Gene,
        on_delete=models.CASCADE,
        related_name='phenotype_associations',
        verbose_name="Gene"
    )

    hpo_term = models.ForeignKey(
        HPOTerm,
        on_delete=models.CASCADE,
        related_name='gene_associations',
        verbose_name="HPO Term"
    )

    class Meta:
        verbose_name = "Gene-Phenotype Association"
        verbose_name_plural = "Gene-Phenotype Associations"
        unique_together = [['gene', 'hpo_term']]
        indexes = [
            models.Index(fields=['gene', 'hpo_term']),
        ]

    def __str__(self):
        return f"{self.gene.gene_symbol} - {self.hpo_term.hpo_id}"


class DiseasePhenotypeAssociation(models.Model):
    """
    Association between diseases and HPO phenotype terms.
    """
    disease = models.ForeignKey(
        Disease,
        on_delete=models.CASCADE,
        related_name='phenotype_associations',
        verbose_name="Disease"
    )

    hpo_term = models.ForeignKey(
        HPOTerm,
        on_delete=models.CASCADE,
        related_name='disease_associations',
        verbose_name="HPO Term"
    )

    frequency = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Frequency",
        help_text="Frequency of phenotype in disease (e.g., 'Very frequent', '5/10')"
    )

    class Meta:
        verbose_name = "Disease-Phenotype Association"
        verbose_name_plural = "Disease-Phenotype Associations"
        unique_together = [['disease', 'hpo_term']]
        indexes = [
            models.Index(fields=['disease', 'hpo_term']),
        ]

    def __str__(self):
        return f"{self.disease.database_id} - {self.hpo_term.hpo_id}"


class GeneDiseaseAssociation(models.Model):
    """
    Association between genes and diseases.
    """
    gene = models.ForeignKey(
        Gene,
        on_delete=models.CASCADE,
        related_name='disease_associations',
        verbose_name="Gene"
    )

    disease = models.ForeignKey(
        Disease,
        on_delete=models.CASCADE,
        related_name='gene_associations',
        verbose_name="Disease"
    )

    class Meta:
        verbose_name = "Gene-Disease Association"
        verbose_name_plural = "Gene-Disease Associations"
        unique_together = [['gene', 'disease']]
        indexes = [
            models.Index(fields=['gene', 'disease']),
        ]

    def __str__(self):
        return f"{self.gene.gene_symbol} - {self.disease.database_id}"
