# gene_search/admin.py
"""
Admin interface for gene search app.
"""

from django.contrib import admin
from .models import GeneSearchQuery


@admin.register(GeneSearchQuery)
class GeneSearchQueryAdmin(admin.ModelAdmin):
    list_display = ('search_term', 'search_type', 'user', 'created_at', 'success', 'hpo_count', 'omim_count', 'pharmgkb_count')
    list_filter = ('search_type', 'success', 'created_at')
    search_fields = ('search_term', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def hpo_count(self, obj):
        return obj.get_hpo_count()
    hpo_count.short_description = 'HPO Terms'

    def omim_count(self, obj):
        return obj.get_omim_count()
    omim_count.short_description = 'OMIM Diseases'

    def pharmgkb_count(self, obj):
        return obj.get_pharmgkb_count()
    pharmgkb_count.short_description = 'PharmGKB Entries'
