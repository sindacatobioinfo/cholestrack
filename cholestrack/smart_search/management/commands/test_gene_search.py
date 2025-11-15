# smart_search/management/commands/test_gene_search.py
"""
Management command to test gene search functionality and verify database relationships.
"""

from django.core.management.base import BaseCommand
from smart_search.models import Gene, Disease, GeneDiseaseAssociation, GenePhenotypeAssociation
from smart_search.api_utils import HPOLocalClient


class Command(BaseCommand):
    help = 'Test gene search functionality and verify database relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gene',
            type=str,
            default='ATP8B1',
            help='Gene symbol to test (default: ATP8B1)',
        )

    def handle(self, *args, **options):
        gene_symbol = options['gene']

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('DATABASE STATISTICS'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'Total Genes: {Gene.objects.count()}')
        self.stdout.write(f'Total Diseases: {Disease.objects.count()}')
        self.stdout.write(f'Total Gene-Disease Associations: {GeneDiseaseAssociation.objects.count()}')
        self.stdout.write(f'Total Gene-Phenotype Associations: {GenePhenotypeAssociation.objects.count()}')
        self.stdout.write('')

        # Test with a specific gene
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'TESTING GENE: {gene_symbol}'))
        self.stdout.write('=' * 80)

        # Direct database query
        gene = Gene.objects.filter(gene_symbol__iexact=gene_symbol).first()

        if not gene:
            self.stdout.write(self.style.ERROR(f'Gene "{gene_symbol}" not found in database'))
            self.stdout.write('')
            self.stdout.write('Available genes (first 10):')
            for g in Gene.objects.all()[:10]:
                self.stdout.write(f'  - {g.gene_symbol} (Entrez: {g.entrez_id})')
            return

        self.stdout.write(f'Found Gene: {gene.gene_symbol} (Entrez ID: {gene.entrez_id}, DB ID: {gene.id})')
        self.stdout.write('')

        # Count phenotype associations
        phenotype_count = GenePhenotypeAssociation.objects.filter(gene=gene).count()
        self.stdout.write(f'Gene-Phenotype Associations: {phenotype_count}')

        # Count disease associations
        disease_count = GeneDiseaseAssociation.objects.filter(gene=gene).count()
        self.stdout.write(f'Gene-Disease Associations: {disease_count}')
        self.stdout.write('')

        if disease_count > 0:
            self.stdout.write(f'Diseases associated with {gene_symbol}:')
            disease_assocs = GeneDiseaseAssociation.objects.filter(
                gene=gene
            ).select_related('disease')[:10]

            for i, assoc in enumerate(disease_assocs, 1):
                self.stdout.write(
                    f'  {i}. {assoc.disease.database_id}: {assoc.disease.disease_name} '
                    f'(DB: {assoc.disease.database})'
                )

            if disease_count > 10:
                self.stdout.write(f'  ... and {disease_count - 10} more')
        else:
            self.stdout.write(self.style.WARNING(f'No disease associations found for {gene_symbol}'))
            self.stdout.write('')
            self.stdout.write('Checking if any genes have disease associations...')
            genes_with_diseases = Gene.objects.filter(
                disease_associations__isnull=False
            ).distinct()[:5]

            if genes_with_diseases.exists():
                self.stdout.write('Sample genes with disease associations:')
                for g in genes_with_diseases:
                    count = GeneDiseaseAssociation.objects.filter(gene=g).count()
                    self.stdout.write(f'  - {g.gene_symbol}: {count} diseases')
            else:
                self.stdout.write(self.style.ERROR(
                    'No gene-disease associations found in database! '
                    'Run: python manage.py load_hpo_data'
                ))

        self.stdout.write('')

        # Test API function
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'TESTING API FUNCTION: HPOLocalClient.search_gene()'))
        self.stdout.write('=' * 80)

        result = HPOLocalClient.search_gene(gene_symbol)

        if 'error' in result:
            self.stdout.write(self.style.ERROR(f'Error: {result["error"]}'))
        else:
            self.stdout.write(f'Gene Info: {result.get("gene_info")}')
            self.stdout.write(f'Phenotypes Found: {len(result.get("phenotypes", []))}')
            self.stdout.write(f'Diseases Found: {len(result.get("diseases", []))}')
            self.stdout.write('')

            if result.get('diseases'):
                self.stdout.write('Diseases from API call:')
                for i, disease in enumerate(result['diseases'][:10], 1):
                    self.stdout.write(
                        f'  {i}. {disease["disease_id"]}: {disease["disease_name"]} '
                        f'(DB: {disease["database"]})'
                    )

                if len(result['diseases']) > 10:
                    self.stdout.write(f'  ... and {len(result["diseases"]) - 10} more')
            else:
                self.stdout.write(self.style.WARNING('No diseases returned from API'))

        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('TEST COMPLETE'))
        self.stdout.write('=' * 80)
