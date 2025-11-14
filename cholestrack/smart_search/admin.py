# smart_search/admin.py
"""
Admin interface for smart search app.
"""

from django.contrib import admin
from .models import GeneSearchQuery


@admin.register(GeneSearchQuery)
class GeneSearchQueryAdmin(admin.ModelAdmin):
    list_display = ('search_term', 'user', 'created_at', 'success', 'phenotype_count', 'disease_count')
    list_filter = ('success', 'created_at')
    search_fields = ('search_term', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def phenotype_count(self, obj):
        return obj.get_phenotype_count()
    phenotype_count.short_description = 'HPO Phenotypes'

    def disease_count(self, obj):
        return obj.get_disease_count()
    disease_count.short_description = 'Associated Diseases'
