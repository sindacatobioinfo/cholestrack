# smart_search/management/commands/fix_disease_database_field.py
"""
Management command to fix the database field in existing Disease records.
Extracts the database prefix from database_id for all Disease records.
"""

from django.core.management.base import BaseCommand
from smart_search.models import Disease


class Command(BaseCommand):
    help = 'Fix database field in existing Disease records by extracting prefix from database_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('=' * 80)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        else:
            self.stdout.write(self.style.SUCCESS('FIXING DISEASE DATABASE FIELDS'))
        self.stdout.write('=' * 80)
        self.stdout.write('')

        # Get all diseases
        diseases = Disease.objects.all()
        total_count = diseases.count()
        self.stdout.write(f'Total diseases to check: {total_count}')
        self.stdout.write('')

        updated_count = 0
        issues_count = 0

        for disease in diseases:
            # Extract database prefix from database_id
            if ':' in disease.database_id:
                expected_database = disease.database_id.split(':')[0][:100]
            else:
                expected_database = 'OMIM'

            # Check if database field needs updating
            if disease.database != expected_database:
                if dry_run:
                    self.stdout.write(
                        f'Would update: {disease.database_id}'
                    )
                    self.stdout.write(
                        f'  Current database field: "{disease.database}"'
                    )
                    self.stdout.write(
                        f'  Expected database field: "{expected_database}"'
                    )
                    self.stdout.write('')
                else:
                    disease.database = expected_database
                    disease.save()

                updated_count += 1

        self.stdout.write('')
        self.stdout.write('=' * 80)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would update {updated_count} out of {total_count} diseases'))
            self.stdout.write('')
            self.stdout.write('Run without --dry-run to apply changes:')
            self.stdout.write('  python manage.py fix_disease_database_field')
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} out of {total_count} diseases'))
            self.stdout.write('')
            self.stdout.write('Next steps:')
            self.stdout.write('  1. Clear search cache: python manage.py clear_search_cache --all')
            self.stdout.write('  2. Run a new search to see updated disease data')
        self.stdout.write('=' * 80)
