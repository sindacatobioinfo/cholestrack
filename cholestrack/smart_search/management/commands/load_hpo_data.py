# smart_search/management/commands/load_hpo_data.py
"""
Management command to download and load HPO annotation data into the local database.

Usage:
    python manage.py load_hpo_data [--url URL] [--file FILE]

Examples:
    # Download from default HPO GitHub release
    python manage.py load_hpo_data

    # Load from a local file
    python manage.py load_hpo_data --file /path/to/genes_to_phenotype.txt

    # Download from specific URL
    python manage.py load_hpo_data --url https://example.com/genes_to_phenotype.txt
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

    # Default URLs for HPO annotation files
    DEFAULT_GENES_TO_PHENOTYPE_URL = (
        'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/'
        'genes_to_phenotype.txt'
    )
    DEFAULT_PHENOTYPE_HPOA_URL = (
        'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/'
        'phenotype.hpoa'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--genes-file',
            type=str,
            help='Path to local genes_to_phenotype.txt file',
        )
        parser.add_argument(
            '--disease-file',
            type=str,
            help='Path to local phenotype.hpoa file',
        )
        parser.add_argument(
            '--genes-url',
            type=str,
            default=self.DEFAULT_GENES_TO_PHENOTYPE_URL,
            help='URL to download genes_to_phenotype.txt',
        )
        parser.add_argument(
            '--disease-url',
            type=str,
            default=self.DEFAULT_PHENOTYPE_HPOA_URL,
            help='URL to download phenotype.hpoa',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing HPO data before loading',
        )
        parser.add_argument(
            '--skip-genes',
            action='store_true',
            help='Skip loading genes_to_phenotype data',
        )
        parser.add_argument(
            '--skip-diseases',
            action='store_true',
            help='Skip loading phenotype.hpoa data',
        )

    def handle(self, *args, **options):
        try:
            # Clear existing data if requested
            if options['clear']:
                self.stdout.write('Clearing existing HPO data...')
                self.clear_hpo_data()

            # Load genes to phenotype data
            if not options['skip_genes']:
                genes_file = options.get('genes_file')
                if genes_file and os.path.exists(genes_file):
                    self.stdout.write(f'Loading genes from file: {genes_file}')
                    self.load_genes_to_phenotype(genes_file)
                else:
                    genes_url = options['genes_url']
                    self.stdout.write(f'Downloading genes data from: {genes_url}')
                    genes_file = self.download_file(genes_url, 'genes_to_phenotype.txt')
                    self.load_genes_to_phenotype(genes_file)
                    os.remove(genes_file)

            # Load disease to phenotype data
            if not options['skip_diseases']:
                disease_file = options.get('disease_file')
                if disease_file and os.path.exists(disease_file):
                    self.stdout.write(f'Loading diseases from file: {disease_file}')
                    self.load_phenotype_hpoa(disease_file)
                else:
                    disease_url = options['disease_url']
                    self.stdout.write(f'Downloading disease data from: {disease_url}')
                    disease_file = self.download_file(disease_url, 'phenotype.hpoa')
                    self.load_phenotype_hpoa(disease_file)
                    os.remove(disease_file)

            # Create gene-disease associations
            self.stdout.write('Creating gene-disease associations...')
            self.create_gene_disease_associations()

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
        #Format: entrez-gene-id<tab>entrez-gene-symbol<tab>HPO-Term-Name<tab>HPO-Term-ID
        Or similar variations
        """
        self.stdout.write(f'Processing {file_path}...')

        genes_created = 0
        terms_created = 0
        associations_created = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip header lines
            for line in f:
                if not line.startswith('#'):
                    break

            # Process data lines
            reader = csv.reader(f, delimiter='\t')

            with transaction.atomic():
                for row in reader:
                    if len(row) < 4:
                        continue

                    try:
                        entrez_id = int(row[0])
                        gene_symbol = row[1]
                        hpo_name = row[2]
                        hpo_id = row[3]

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
                            self.style.WARNING(f'Skipping invalid row: {row} - {e}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded genes_to_phenotype: '
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
                        database_id = row.get('database_id') or row.get('DatabaseID', '')
                        disease_name = row.get('disease_name') or row.get('DiseaseName', '')
                        hpo_id = row.get('hpo_id') or row.get('HPO_ID', '')
                        hpo_name = row.get('hpo_name', '')
                        frequency = row.get('frequency') or row.get('Frequency', '')

                        if not database_id or not hpo_id:
                            continue

                        # Extract database type (e.g., OMIM, ORPHA)
                        database = database_id.split(':')[0] if ':' in database_id else 'OMIM'

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
                            self.style.WARNING(f'Skipping invalid row: {e}')
                        )
                        continue

        self.stdout.write(self.style.SUCCESS(
            f'Loaded phenotype.hpoa: '
            f'{diseases_created} diseases, {terms_created} terms, '
            f'{associations_created} associations'
        ))

    def create_gene_disease_associations(self):
        """
        Create gene-disease associations based on shared phenotypes.
        Links genes to diseases when they share HPO terms.
        """
        associations_created = 0

        with transaction.atomic():
            # Get all genes
            genes = Gene.objects.all()

            for gene in genes:
                # Get HPO terms for this gene
                hpo_terms = HPOTerm.objects.filter(
                    gene_associations__gene=gene
                ).distinct()

                # Find diseases associated with these HPO terms
                diseases = Disease.objects.filter(
                    phenotype_associations__hpo_term__in=hpo_terms
                ).distinct()

                # Create gene-disease associations
                for disease in diseases:
                    _, created = GeneDiseaseAssociation.objects.get_or_create(
                        gene=gene,
                        disease=disease
                    )
                    if created:
                        associations_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created {associations_created} gene-disease associations'
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
