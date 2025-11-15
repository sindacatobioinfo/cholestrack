# smart_search/management/commands/clear_search_cache.py
"""
Management command to clear cached search queries.
Useful after updating HPO database to force fresh searches.
"""

from django.core.management.base import BaseCommand
from smart_search.models import GeneSearchQuery


class Command(BaseCommand):
    help = 'Clear cached search queries to force fresh searches with updated database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete all search queries (default: just expire cache)',
        )
        parser.add_argument(
            '--gene',
            type=str,
            help='Only clear cache for a specific gene symbol',
        )

    def handle(self, *args, **options):
        if options['all']:
            if options['gene']:
                # Delete queries for specific gene
                queries = GeneSearchQuery.objects.filter(search_term__iexact=options['gene'])
                count = queries.count()
                queries.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deleted {count} cached queries for gene: {options["gene"]}'
                    )
                )
            else:
                # Delete all queries
                count = GeneSearchQuery.objects.count()
                GeneSearchQuery.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted all {count} cached queries')
                )
        else:
            if options['gene']:
                # Expire cache for specific gene
                queries = GeneSearchQuery.objects.filter(search_term__iexact=options['gene'])
                count = queries.update(cache_expires_at=None)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Expired cache for {count} queries for gene: {options["gene"]}'
                    )
                )
            else:
                # Expire all caches
                count = GeneSearchQuery.objects.update(cache_expires_at=None)
                self.stdout.write(
                    self.style.SUCCESS(f'Expired cache for all {count} queries')
                )

        self.stdout.write('')
        self.stdout.write('Note: Users will get fresh results from the updated database on their next search.')
