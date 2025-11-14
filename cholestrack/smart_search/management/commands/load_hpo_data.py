# smart_search/management/commands/load_hpo_data.py
"""
Management command to download and load HPO annotation data into the local database.

Usage:
    python manage.py load_hpo_data [options]

Examples:
    # Download from default HPO GitHub release
    python manage.py load_hpo_data

    # Load from local files
    python manage.py load_hpo_data --genes-file /path/to/genes_to_phenotype.txt

    # Download from specific release
    python manage.py load_hpo_data --release v2025-10-22
"""

import os
import csv
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from smart_search.models import (
    HPOTerm, Gene, Disease,
    GenePhenotypeAssociation,
    DiseasePhenotypeAssociation,
    GeneDiseaseAssociation
)


class Command(BaseCommand):
    help = 'Download and load HPO annotation data into the local database'

    # Default release version (can be overridden with --release argument)
    DEFAULT_RELEASE = 'v2025-10-22'

    def get_file_url(self, release, filename):
        """Generate download URL for a file from the specified release."""
        return (
            f'https://github.com/obophenotype/human-phenotype-ontology/releases/download/'
            f'{release}/{filename}'
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--release',
            type=str,
            default=self.DEFAULT_RELEASE,
            help=f'HPO release version (default: {self.DEFAULT_RELEASE})',
        )
        parser.add_argument(
            '--genes-to-phenotype-file',
            type=str,
            help='Path to local genes_to_phenotype.txt file',
        )
        parser.add_argument(
            '--genes-to-disease-file',
            type=str,
            help='Path to local genes_to_disease.txt file',
        )
        parser.add_argument(
            '--phenotype-to-genes-file',
            type=str,
            help='Path to local phenotype_to_genes.txt file',
        )
        parser.add_argument(
            '--disease-file',
            type=str,
            help='Path to local phenotype.hpoa file',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing HPO data before loading',
        )
        parser.add_argument(
            '--skip-genes-to-phenotype',
            action='store_true',
            help='Skip loading genes_to_phenotype data',
        )
        parser.add_argument(
            '--skip-genes-to-disease',
            action='store_true',
            help='Skip loading genes_to_disease data',
        )
        parser.add_argument(
            '--skip-phenotype-to-genes',
            action='store_true',
            help='Skip loading phenotype_to_genes data',
        )
        parser.add_argument(
            '--skip-diseases',
            action='store_true',
            help='Skip loading phenotype.hpoa data',
        )

    def handle(self, *args, **options):
        try:
            release = options['release']
            self.stdout.write(f'Using HPO release: {release}')

            # Clear existing data if requested
            if options['clear']:
                self.stdout.write('Clearing existing HPO data...')
                self.clear_hpo_data()

            # Load genes_to_phenotype data
            if not options['skip_genes_to_phenotype']:
                file_path = options.get('genes_to_phenotype_file')
                if file_path and os.path.exists(file_path):
                    self.stdout.write(f'Loading genes_to_phenotype from file: {file_path}')
                    self.load_genes_to_phenotype(file_path)
                else:
                    url = self.get_file_url(release, 'genes_to_phenotype.txt')
                    self.stdout.write(f'Downloading genes_to_phenotype from: {url}')
                    file_path = self.download_file(url, 'genes_to_phenotype.txt')
                    self.load_genes_to_phenotype(file_path)
                    os.remove(file_path)

            # Load disease to phenotype data
            if not options['skip_diseases']:
                file_path = options.get('disease_file')
                if file_path and os.path.exists(file_path):
                    self.stdout.write(f'Loading phenotype.hpoa from file: {file_path}')
                    self.load_phenotype_hpoa(file_path)
                else:
                    url = self.get_file_url(release, 'phenotype.hpoa')
                    self.stdout.write(f'Downloading phenotype.hpoa from: {url}')
                    file_path = self.download_file(url, 'phenotype.hpoa')
                    self.load_phenotype_hpoa(file_path)
                    os.remove(file_path)

            # Load genes_to_disease data (direct gene-disease associations)
            if not options['skip_genes_to_disease']:
                file_path = options.get('genes_to_disease_file')
                if file_path and os.path.exists(file_path):
                    self.stdout.write(f'Loading genes_to_disease from file: {file_path}')
                    self.load_genes_to_disease(file_path)
                else:
                    url = self.get_file_url(release, 'genes_to_disease.txt')
                    self.stdout.write(f'Downloading genes_to_disease from: {url}')
                    file_path = self.download_file(url, 'genes_to_disease.txt')
                    self.load_genes_to_disease(file_path)
                    os.remove(file_path)

            # Load phenotype_to_genes data (additional associations)
            if not options['skip_phenotype_to_genes']:
                file_path = options.get('phenotype_to_genes_file')
                if file_path and os.path.exists(file_path):
                    self.stdout.write(f'Loading phenotype_to_genes from file: {file_path}')
                    self.load_phenotype_to_genes(file_path)
                else:
                    url = self.get_file_url(release, 'phenotype_to_genes.txt')
                    self.stdout.write(f'Downloading phenotype_to_genes from: {url}')
                    file_path = self.download_file(url, 'phenotype_to_genes.txt')
                    self.load_phenotype_to_genes(file_path)
                    os.remove(file_path)

            self.stdout.write(self.style.SUCCESS('Successfully loaded HPO data'))
            self.print_statistics()

        except Exception as e:
            raise CommandError(f'Error loading HPO data: {str(e)}')

    def download_file(self, url, filename):
        """Download a file from URL."""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            temp_file = f'/tmp/{filename}'
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            return temp_file
        except requests.RequestException as e:
            raise CommandError(f'Failed to download {url}: {str(e)}')

    def clear_hpo_data(self):
        """Clear all HPO data from database."""
        with transaction.atomic():
            GeneDiseaseAssociation.objects.all().delete()
            DiseasePhenotypeAssociation.objects.all().delete()
            GenePhenotypeAssociation.objects.all().delete()
            Disease.objects.all().delete()
            Gene.objects.all().delete()
            HPOTerm.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared existing HPO data'))

    def load_genes_to_phenotype(self, file_path):
        """
        Load genes_to_phenotype.txt file.

        Expected format (tab-separated):
        #Format: entrez-gene-id<tab>entrez-gene-symbol<tab>HPO-Term-ID<tab>HPO-Term-Name
        Note: The actual format has HPO ID before HPO Name (columns 3 and 4 are ID then Name)
        """
        self.stdout.write(f'Processing {file_path}...')

        genes_created = 0
        terms_created = 0
        associations_created = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip header lines
            for line in f:
                if not line.startswith('#'):
                    # Read this line as first data line
                    reader = csv.reader([line] + list(f), delimiter='\t')
                    break
            else:
                # If we never broke, there are no data lines
                reader = []

            with transaction.atomic():
                for row in reader:
                    if len(row) < 4:
                        continue

                    try:
                        # Strip whitespace and validate data
                        entrez_id = int(row[0].strip())
                        gene_symbol = row[1].strip()[:50]  # Max 50 chars
                        hpo_id = row[2].strip()[:50]        # Column 3 is HPO ID
                        hpo_name = row[3].strip()[:500]     # Column 4 is HPO Name

                        # Skip if any required field is empty
                        if not gene_symbol or not hpo_id:
                            continue

                        # Create or get Gene
                        gene, created = Gene.objects.get_or_create(
                            entrez_id=entrez_id,
                            defaults={'gene_symbol': gene_symbol}
                        )
                        if created:
                            genes_created += 1

                        # Create or get HPO Term
                        hpo_term, created = HPOTerm.objects.get_or_create(
                            hpo_id=hpo_id,
                            defaults={'name': hpo_name}
                        )
                        if created:
                            terms_created += 1

                        # Create association
                        _, created = GenePhenotypeAssociation.objects.get_or_create(
                            gene=gene,
                            hpo_term=hpo_term
                        )
                        if created:
                            associations_created += 1

                    except (ValueError, IndexError) as e:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping invalid row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error processing row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded genes_to_phenotype: '
            f'{genes_created} genes, {terms_created} terms, '
            f'{associations_created} associations'
        ))

    def load_genes_to_disease(self, file_path):
        """
        Load genes_to_disease.txt file.

        Expected format (tab-separated):
        #Format: entrez-gene-id<tab>entrez-gene-symbol<tab>disease-ID<tab>disease-name
        """
        self.stdout.write(f'Processing {file_path}...')

        genes_created = 0
        diseases_created = 0
        associations_created = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip header lines
            for line in f:
                if not line.startswith('#'):
                    reader = csv.reader([line] + list(f), delimiter='\t')
                    break
            else:
                reader = []

            with transaction.atomic():
                for row in reader:
                    if len(row) < 4:
                        continue

                    try:
                        entrez_id = int(row[0].strip())
                        gene_symbol = row[1].strip()[:50]
                        disease_id = row[2].strip()[:200]
                        disease_name = row[3].strip()[:500]

                        if not gene_symbol or not disease_id:
                            continue

                        # Extract database type (e.g., OMIM, ORPHA)
                        database = disease_id.split(':')[0] if ':' in disease_id else 'OMIM'
                        database = database[:100]

                        # Create or get Gene
                        gene, created = Gene.objects.get_or_create(
                            entrez_id=entrez_id,
                            defaults={'gene_symbol': gene_symbol}
                        )
                        if created:
                            genes_created += 1

                        # Create or get Disease
                        disease, created = Disease.objects.get_or_create(
                            database_id=disease_id,
                            defaults={
                                'disease_name': disease_name,
                                'database': database
                            }
                        )
                        if created:
                            diseases_created += 1

                        # Create gene-disease association
                        _, created = GeneDiseaseAssociation.objects.get_or_create(
                            gene=gene,
                            disease=disease
                        )
                        if created:
                            associations_created += 1

                    except (ValueError, IndexError) as e:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping invalid row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error processing row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded genes_to_disease: '
            f'{genes_created} genes, {diseases_created} diseases, '
            f'{associations_created} associations'
        ))

    def load_phenotype_to_genes(self, file_path):
        """
        Load phenotype_to_genes.txt file.

        Expected format (tab-separated):
        #Format: HPO-Term-ID<tab>HPO-Term-Name<tab>entrez-gene-id<tab>entrez-gene-symbol
        """
        self.stdout.write(f'Processing {file_path}...')

        genes_created = 0
        terms_created = 0
        associations_created = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip header lines
            for line in f:
                if not line.startswith('#'):
                    reader = csv.reader([line] + list(f), delimiter='\t')
                    break
            else:
                reader = []

            with transaction.atomic():
                for row in reader:
                    if len(row) < 4:
                        continue

                    try:
                        hpo_id = row[0].strip()[:50]
                        hpo_name = row[1].strip()[:500]
                        entrez_id = int(row[2].strip())
                        gene_symbol = row[3].strip()[:50]

                        if not gene_symbol or not hpo_id:
                            continue

                        # Create or get HPO Term
                        hpo_term, created = HPOTerm.objects.get_or_create(
                            hpo_id=hpo_id,
                            defaults={'name': hpo_name}
                        )
                        if created:
                            terms_created += 1

                        # Create or get Gene
                        gene, created = Gene.objects.get_or_create(
                            entrez_id=entrez_id,
                            defaults={'gene_symbol': gene_symbol}
                        )
                        if created:
                            genes_created += 1

                        # Create association (may be duplicate from genes_to_phenotype)
                        _, created = GenePhenotypeAssociation.objects.get_or_create(
                            gene=gene,
                            hpo_term=hpo_term
                        )
                        if created:
                            associations_created += 1

                    except (ValueError, IndexError) as e:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping invalid row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error processing row: {row[:4] if len(row) >= 4 else row} - {e}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded phenotype_to_genes: '
            f'{genes_created} genes, {terms_created} terms, '
            f'{associations_created} associations'
        ))

    def load_phenotype_hpoa(self, file_path):
        """
        Load phenotype.hpoa file.

        Expected format (tab-separated):
        DatabaseID, DiseaseName, Qualifier, HPO_ID, Reference, Evidence,
        Onset, Frequency, Sex, Modifier, Aspect, Biocuration
        """
        self.stdout.write(f'Processing {file_path}...')

        diseases_created = 0
        terms_created = 0
        associations_created = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader((line for line in f if not line.startswith('#')),
                                   delimiter='\t')

            with transaction.atomic():
                for row in reader:
                    try:
                        # Get and strip data, handling both lowercase and uppercase column names
                        database_id = (row.get('database_id') or row.get('DatabaseID', '')).strip()[:200]
                        disease_name = (row.get('disease_name') or row.get('DiseaseName', '')).strip()[:500]
                        hpo_id = (row.get('hpo_id') or row.get('HPO_ID', '')).strip()[:50]
                        hpo_name = row.get('hpo_name', '').strip()[:500]
                        frequency = (row.get('frequency') or row.get('Frequency', '')).strip()[:100]

                        # Skip if required fields are empty
                        if not database_id or not hpo_id:
                            continue

                        # Extract database type (e.g., OMIM, ORPHA)
                        database = database_id.split(':')[0] if ':' in database_id else 'OMIM'
                        database = database[:100]  # Truncate to max length

                        # Create or get Disease
                        disease, created = Disease.objects.get_or_create(
                            database_id=database_id,
                            defaults={
                                'disease_name': disease_name,
                                'database': database
                            }
                        )
                        if created:
                            diseases_created += 1

                        # Create or get HPO Term
                        hpo_term, created = HPOTerm.objects.get_or_create(
                            hpo_id=hpo_id,
                            defaults={'name': hpo_name}
                        )
                        if created:
                            terms_created += 1

                        # Create association
                        _, created = DiseasePhenotypeAssociation.objects.get_or_create(
                            disease=disease,
                            hpo_term=hpo_term,
                            defaults={'frequency': frequency}
                        )
                        if created:
                            associations_created += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Skipping row due to error: {str(e)[:200]}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded phenotype.hpoa: '
            f'{diseases_created} diseases, {terms_created} terms, '
            f'{associations_created} associations'
        ))

    def print_statistics(self):
        """Print database statistics."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('HPO Database Statistics:')
        self.stdout.write('='*50)
        self.stdout.write(f'HPO Terms: {HPOTerm.objects.count()}')
        self.stdout.write(f'Genes: {Gene.objects.count()}')
        self.stdout.write(f'Diseases: {Disease.objects.count()}')
        self.stdout.write(f'Gene-Phenotype Associations: {GenePhenotypeAssociation.objects.count()}')
        self.stdout.write(f'Disease-Phenotype Associations: {DiseasePhenotypeAssociation.objects.count()}')
        self.stdout.write(f'Gene-Disease Associations: {GeneDiseaseAssociation.objects.count()}')
        self.stdout.write('='*50)
