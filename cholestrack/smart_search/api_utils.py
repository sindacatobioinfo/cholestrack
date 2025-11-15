# smart_search/api_utils.py
"""
Local database utilities for HPO (Human Phenotype Ontology).
Fetches gene-phenotype-disease relationships from the local HPO database.
"""

from typing import Dict, List
from django.db.models import Q
from .models import (
    HPOTerm, Gene, Disease,
    GenePhenotypeAssociation,
    DiseasePhenotypeAssociation,
    GeneDiseaseAssociation
)


class HPOLocalClient:
    """
    Client for querying local HPO database.
    Uses Django ORM to query HPO annotation data stored locally.
    """

    @staticmethod
    def search_gene(gene_symbol: str) -> Dict:
        """
        Search for phenotypes and diseases associated with a gene in local database.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1', 'BRCA1')

        Returns:
            Dictionary with:
            - phenotypes: List of HPO phenotype terms
            - diseases: List of associated diseases
            - gene_info: Gene information
        """
        try:
            # Search for gene (case-insensitive)
            gene = Gene.objects.filter(
                gene_symbol__iexact=gene_symbol
            ).first()

            if not gene:
                return {
                    'phenotypes': [],
                    'diseases': [],
                    'gene_info': None,
                    'error': f'Gene "{gene_symbol}" not found in local HPO database. '
                             'Please run "python manage.py load_hpo_data" to populate the database.'
                }

            # Get phenotypes for this gene
            phenotypes = []
            gene_phenotype_associations = GenePhenotypeAssociation.objects.filter(
                gene=gene
            ).select_related('hpo_term')

            for assoc in gene_phenotype_associations:
                phenotypes.append({
                    'hpo_id': assoc.hpo_term.hpo_id,
                    'name': assoc.hpo_term.name,
                    'definition': assoc.hpo_term.definition or 'No definition available'
                })

            # Get diseases for this gene
            diseases = []
            gene_disease_associations = GeneDiseaseAssociation.objects.filter(
                gene=gene
            ).select_related('disease')

            for assoc in gene_disease_associations:
                # Extract database name from database_id (substring before ':')
                database_id = assoc.disease.database_id
                database_name = database_id.split(':')[0] if ':' in database_id else 'Unknown'

                diseases.append({
                    'disease_id': database_id,
                    'disease_name': assoc.disease.disease_name,
                    'database': database_name
                })

            # Return results
            return {
                'phenotypes': phenotypes,
                'diseases': diseases,
                'gene_info': {
                    'gene_symbol': gene.gene_symbol,
                    'entrez_id': gene.entrez_id
                }
            }

        except Exception as e:
            print(f"Error searching local HPO database for {gene_symbol}: {e}")
            return {
                'phenotypes': [],
                'diseases': [],
                'gene_info': None,
                'error': f'Database error: {str(e)}'
            }

    @staticmethod
    def get_phenotype_details(hpo_id: str) -> Dict:
        """
        Get details for a specific HPO term.

        Args:
            hpo_id: HPO term ID (e.g., 'HP:0000001')

        Returns:
            Dictionary with HPO term details
        """
        try:
            hpo_term = HPOTerm.objects.get(hpo_id=hpo_id)

            # Get associated genes
            genes = Gene.objects.filter(
                phenotype_associations__hpo_term=hpo_term
            ).distinct()

            # Get associated diseases
            diseases = Disease.objects.filter(
                phenotype_associations__hpo_term=hpo_term
            ).distinct()

            return {
                'hpo_id': hpo_term.hpo_id,
                'name': hpo_term.name,
                'definition': hpo_term.definition,
                'gene_count': genes.count(),
                'disease_count': diseases.count(),
                'genes': [gene.gene_symbol for gene in genes[:10]],  # Limit to 10
                'diseases': [disease.disease_name for disease in diseases[:10]]  # Limit to 10
            }

        except HPOTerm.DoesNotExist:
            return {
                'error': f'HPO term "{hpo_id}" not found in local database'
            }
        except Exception as e:
            return {
                'error': f'Database error: {str(e)}'
            }

    @staticmethod
    def search_genes_by_phenotype(hpo_id: str) -> List[Dict]:
        """
        Search for genes associated with a specific phenotype.

        Args:
            hpo_id: HPO term ID (e.g., 'HP:0000001')

        Returns:
            List of gene dictionaries
        """
        try:
            hpo_term = HPOTerm.objects.get(hpo_id=hpo_id)

            genes = Gene.objects.filter(
                phenotype_associations__hpo_term=hpo_term
            ).distinct()

            return [
                {
                    'gene_symbol': gene.gene_symbol,
                    'entrez_id': gene.entrez_id
                }
                for gene in genes
            ]

        except HPOTerm.DoesNotExist:
            return []
        except Exception as e:
            print(f"Error searching genes by phenotype: {e}")
            return []

    @staticmethod
    def search_diseases_by_gene(gene_symbol: str) -> List[Dict]:
        """
        Search for diseases associated with a gene.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1')

        Returns:
            List of disease dictionaries
        """
        try:
            gene = Gene.objects.filter(
                gene_symbol__iexact=gene_symbol
            ).first()

            if not gene:
                return []

            diseases = Disease.objects.filter(
                gene_associations__gene=gene
            ).distinct()

            result = []
            for disease in diseases:
                # Extract database name from database_id (substring before ':')
                database_id = disease.database_id
                database_name = database_id.split(':')[0] if ':' in database_id else 'Unknown'

                result.append({
                    'disease_id': database_id,
                    'disease_name': disease.disease_name,
                    'database': database_name
                })

            return result

        except Exception as e:
            print(f"Error searching diseases by gene: {e}")
            return []

    @staticmethod
    def get_database_stats() -> Dict:
        """
        Get statistics about the local HPO database.

        Returns:
            Dictionary with database statistics
        """
        try:
            return {
                'hpo_terms': HPOTerm.objects.count(),
                'genes': Gene.objects.count(),
                'diseases': Disease.objects.count(),
                'gene_phenotype_associations': GenePhenotypeAssociation.objects.count(),
                'disease_phenotype_associations': DiseasePhenotypeAssociation.objects.count(),
                'gene_disease_associations': GeneDiseaseAssociation.objects.count(),
            }
        except Exception as e:
            return {
                'error': f'Database error: {str(e)}'
            }


def fetch_gene_data(gene_symbol: str) -> Dict:
    """
    Fetch all HPO data for a gene including phenotypes and diseases from local database.

    Args:
        gene_symbol: Gene symbol (e.g., 'ATP8B1')

    Returns:
        Dictionary with phenotypes, diseases, and gene_info
    """
    hpo_client = HPOLocalClient()
    results = hpo_client.search_gene(gene_symbol)

    return results


def get_hpo_database_stats() -> Dict:
    """
    Get statistics about the local HPO database.

    Returns:
        Dictionary with database statistics
    """
    hpo_client = HPOLocalClient()
    return hpo_client.get_database_stats()
