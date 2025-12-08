# smart_search/api_utils.py
"""
Local database utilities for HPO (Human Phenotype Ontology).
Fetches gene-phenotype-disease relationships from the local HPO database.
Also integrates with ClinPGx API for pharmacogenomic information.
"""

from typing import Dict, List
from django.db.models import Q
import requests
import logging

logger = logging.getLogger(__name__)
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
                diseases.append({
                    'disease_id': assoc.disease.database_id,
                    'disease_name': assoc.disease.disease_name,
                    'database': assoc.disease.database
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

            return [
                {
                    'disease_id': disease.database_id,
                    'disease_name': disease.disease_name,
                    'database': disease.database
                }
                for disease in diseases
            ]

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


def fetch_clinpgx_data(gene_symbol: str) -> Dict:
    """
    Fetch pharmacogenomic data from ClinPGx API.

    Args:
        gene_symbol: Gene symbol (e.g., 'ABCC2')

    Returns:
        Dictionary with ClinPGx data or error information
    """
    try:
        url = f"https://api.clinpgx.org/v1/data/gene"
        params = {
            'symbol': gene_symbol.upper(),
            'view': 'base'
        }
        headers = {
            'accept': 'application/json'
        }

        # Make request with timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)

        # Debug: Log the actual URL and response
        logger.info(f"ClinPGx Gene API - URL: {response.url}")
        logger.info(f"ClinPGx Gene API - Status: {response.status_code}")
        logger.info(f"ClinPGx Gene API - Response: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()

            # API returns an array, take the first element if available
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    # Empty array means no results
                    return {
                        'id': None,
                        'cpicGene': False,
                        'hasNonStandardHaplotypes': False,
                        'hideHaplotypes': False,
                        'pharmVarGene': False,
                        'vipTier': None,
                        'success': False,
                        'error': f'Gene "{gene_symbol}" not found in ClinPGx database'
                    }

            # Extract relevant fields
            return {
                'id': data.get('id', None),  # ClinPGx gene ID (e.g., PA116)
                'cpicGene': data.get('cpicGene', False),
                'hasNonStandardHaplotypes': data.get('hasNonStandardHaplotypes', False),
                'hideHaplotypes': data.get('hideHaplotypes', False),
                'pharmVarGene': data.get('pharmVarGene', False),
                'vipTier': data.get('vipTier', None),
                'success': True
            }
        elif response.status_code == 404:
            # Gene not found in ClinPGx
            return {
                'id': None,
                'cpicGene': False,
                'hasNonStandardHaplotypes': False,
                'hideHaplotypes': False,
                'pharmVarGene': False,
                'vipTier': None,
                'success': False,
                'error': f'Gene "{gene_symbol}" not found in ClinPGx database'
            }
        else:
            # Other error
            return {
                'id': None,
                'cpicGene': False,
                'hasNonStandardHaplotypes': False,
                'hideHaplotypes': False,
                'pharmVarGene': False,
                'vipTier': None,
                'success': False,
                'error': f'ClinPGx API error: HTTP {response.status_code}'
            }

    except requests.exceptions.Timeout:
        return {
            'id': None,
            'cpicGene': False,
            'hasNonStandardHaplotypes': False,
            'hideHaplotypes': False,
            'pharmVarGene': False,
            'vipTier': None,
            'success': False,
            'error': 'ClinPGx API request timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'id': None,
            'cpicGene': False,
            'hasNonStandardHaplotypes': False,
            'hideHaplotypes': False,
            'pharmVarGene': False,
            'vipTier': None,
            'success': False,
            'error': f'ClinPGx API request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'id': None,
            'cpicGene': False,
            'hasNonStandardHaplotypes': False,
            'hideHaplotypes': False,
            'pharmVarGene': False,
            'vipTier': None,
            'success': False,
            'error': f'Error fetching ClinPGx data: {str(e)}'
        }


def fetch_clinpgx_variant_data(variant_id: str) -> Dict:
    """
    Fetch variant annotation data from ClinPGx API.

    Args:
        variant_id: Variant identifier (e.g., 'rs333')

    Returns:
        Dictionary with ClinPGx variant annotation data or error information
    """
    try:
        url = f"https://api.clinpgx.org/v1/data/variantAnnotation"
        params = {
            'location.fingerprint': variant_id,
            'view': 'base'
        }
        headers = {
            'accept': 'application/json'
        }

        # Make request with timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)

        # Debug: Log the actual URL and response
        logger.info(f"ClinPGx Variant API - URL: {response.url}")
        logger.info(f"ClinPGx Variant API - Status: {response.status_code}")
        logger.info(f"ClinPGx Variant API - Response: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()

            # API returns an array, take the first element if available
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    # Empty array means no results
                    return {
                        'accessionId': 'N/A',
                        'alleleGenotype': 'N/A',
                        'comparison': 'N/A',
                        'isAssociated': False,
                        'isPlural': False,
                        'relatedChemicals': [],
                        'success': False,
                        'error': f'No variant annotation found for "{variant_id}"'
                    }

            # Extract relevant fields
            return {
                'accessionId': data.get('accessionId', 'N/A'),
                'alleleGenotype': data.get('alleleGenotype', 'N/A'),
                'comparison': data.get('comparison', 'N/A'),
                'isAssociated': data.get('isAssociated', False),
                'isPlural': data.get('isPlural', False),
                'relatedChemicals': data.get('relatedChemicals', []),
                'success': True
            }
        elif response.status_code == 404:
            # Variant annotation not found in ClinPGx
            return {
                'accessionId': 'N/A',
                'alleleGenotype': 'N/A',
                'comparison': 'N/A',
                'isAssociated': False,
                'isPlural': False,
                'relatedChemicals': [],
                'success': False,
                'error': f'Variant annotation for "{variant_id}" not found in ClinPGx database'
            }
        else:
            # Other error
            return {
                'accessionId': 'N/A',
                'alleleGenotype': 'N/A',
                'comparison': 'N/A',
                'isAssociated': False,
                'isPlural': False,
                'relatedChemicals': [],
                'success': False,
                'error': f'ClinPGx API error: HTTP {response.status_code}'
            }

    except requests.exceptions.Timeout:
        return {
            'accessionId': 'N/A',
            'alleleGenotype': 'N/A',
            'comparison': 'N/A',
            'isAssociated': False,
            'isPlural': False,
            'relatedChemicals': [],
            'success': False,
            'error': 'ClinPGx API request timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'accessionId': 'N/A',
            'alleleGenotype': 'N/A',
            'comparison': 'N/A',
            'isAssociated': False,
            'isPlural': False,
            'relatedChemicals': [],
            'success': False,
            'error': f'ClinPGx API request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'accessionId': 'N/A',
            'alleleGenotype': 'N/A',
            'comparison': 'N/A',
            'isAssociated': False,
            'isPlural': False,
            'relatedChemicals': [],
            'success': False,
            'error': f'Error fetching ClinPGx variant data: {str(e)}'
        }


def fetch_gene_data(gene_symbol: str) -> Dict:
    """
    Fetch all HPO data for a gene including phenotypes and diseases from local database,
    plus pharmacogenomic data from ClinPGx API.

    Args:
        gene_symbol: Gene symbol (e.g., 'ATP8B1')

    Returns:
        Dictionary with phenotypes, diseases, gene_info, and clinpgx_data
    """
    hpo_client = HPOLocalClient()
    results = hpo_client.search_gene(gene_symbol)

    # Add ClinPGx data
    clinpgx_data = fetch_clinpgx_data(gene_symbol)
    results['clinpgx_data'] = clinpgx_data

    return results


def get_hpo_database_stats() -> Dict:
    """
    Get statistics about the local HPO database.

    Returns:
        Dictionary with database statistics
    """
    hpo_client = HPOLocalClient()
    return hpo_client.get_database_stats()


def fetch_phenotype_data(phenotype_search_term: str) -> Dict:
    """
    Fetch all data for a phenotype including associated genes and diseases from local database.

    Args:
        phenotype_search_term: Phenotype name or HPO ID (e.g., 'Abnormal heart morphology' or 'HP:0001627')

    Returns:
        Dictionary with genes, diseases, and phenotype_info
    """
    try:
        # Search for HPO term by ID or name
        hpo_term = None

        # Check if it's an HPO ID
        if phenotype_search_term.startswith('HP:'):
            hpo_term = HPOTerm.objects.filter(hpo_id=phenotype_search_term).first()
        else:
            # Search by name (case-insensitive partial match)
            hpo_term = HPOTerm.objects.filter(
                name__icontains=phenotype_search_term
            ).first()

        if not hpo_term:
            return {
                'genes': [],
                'diseases': [],
                'phenotype_info': None,
                'error': f'Phenotype "{phenotype_search_term}" not found in local HPO database. '
                         'Try searching with at least 5 characters or use autocomplete.'
            }

        # Get associated genes
        genes = []
        gene_associations = GenePhenotypeAssociation.objects.filter(
            hpo_term=hpo_term
        ).select_related('gene')

        for assoc in gene_associations:
            genes.append({
                'gene_symbol': assoc.gene.gene_symbol,
                'entrez_id': assoc.gene.entrez_id
            })

        # Get associated diseases with frequency information
        diseases = []
        disease_associations = DiseasePhenotypeAssociation.objects.filter(
            hpo_term=hpo_term
        ).select_related('disease')

        for assoc in disease_associations:
            diseases.append({
                'disease_id': assoc.disease.database_id,
                'disease_name': assoc.disease.disease_name,
                'database': assoc.disease.database,
                'frequency': assoc.frequency or 'Not specified'
            })

        # Return results
        return {
            'genes': genes,
            'diseases': diseases,
            'phenotype_info': {
                'hpo_id': hpo_term.hpo_id,
                'name': hpo_term.name,
                'definition': hpo_term.definition or 'No definition available'
            }
        }

    except Exception as e:
        print(f"Error searching local HPO database for phenotype {phenotype_search_term}: {e}")
        return {
            'genes': [],
            'diseases': [],
            'phenotype_info': None,
            'error': f'Database error: {str(e)}'
        }


def fetch_variant_data(variant_id: str) -> Dict:
    """
    Fetch variant information from Ensembl API.

    Args:
        variant_id: Variant identifier (e.g., 'rs333')

    Returns:
        Dictionary with variant data or error information
    """
    try:
        url = f"https://rest.ensembl.org/variation/human/{variant_id}"
        headers = {
            'Content-type': 'application/json'
        }

        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Extract minor allele frequency (MAF)
            maf = None
            if 'MAF' in data and data['MAF']:
                # MAF is typically the first item if it exists
                maf = data['MAF']
            elif 'minor_allele_freq' in data:
                maf = data['minor_allele_freq']

            # Filter mappings to find chromosome mapping
            chromosome_mapping = None
            if 'mappings' in data and data['mappings']:
                for mapping in data['mappings']:
                    if mapping.get('coord_system') == 'chromosome':
                        chromosome_mapping = mapping
                        break

            # Extract relevant fields from chromosome mapping
            if chromosome_mapping:
                assembly_name = chromosome_mapping.get('assembly_name', 'N/A')
                location = chromosome_mapping.get('location', 'N/A')
                allele_string = chromosome_mapping.get('allele_string', 'N/A')
                ancestral_allele = chromosome_mapping.get('ancestral_allele', 'N/A')
            else:
                # Fallback if no chromosome mapping found
                assembly_name = 'N/A'
                location = 'N/A'
                allele_string = 'N/A'
                ancestral_allele = 'N/A'

            return {
                'name': data.get('name', variant_id),
                'assembly_name': assembly_name,
                'location': location,
                'allele_string': allele_string,
                'ancestral_allele': ancestral_allele,
                'MAF': maf if maf else 'N/A',
                'most_severe_consequence': data.get('most_severe_consequence', 'N/A'),
                'success': True
            }
        elif response.status_code == 404:
            # Variant not found
            return {
                'name': variant_id,
                'assembly_name': 'N/A',
                'location': 'N/A',
                'allele_string': 'N/A',
                'ancestral_allele': 'N/A',
                'MAF': 'N/A',
                'most_severe_consequence': 'N/A',
                'success': False,
                'error': f'Variant "{variant_id}" not found in Ensembl database'
            }
        else:
            # Other error
            return {
                'name': variant_id,
                'assembly_name': 'N/A',
                'location': 'N/A',
                'allele_string': 'N/A',
                'ancestral_allele': 'N/A',
                'MAF': 'N/A',
                'most_severe_consequence': 'N/A',
                'success': False,
                'error': f'Ensembl API error: HTTP {response.status_code}'
            }

    except requests.exceptions.Timeout:
        return {
            'name': variant_id,
            'assembly_name': 'N/A',
            'location': 'N/A',
            'allele_string': 'N/A',
            'ancestral_allele': 'N/A',
            'MAF': 'N/A',
            'most_severe_consequence': 'N/A',
            'success': False,
            'error': 'Ensembl API request timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'name': variant_id,
            'assembly_name': 'N/A',
            'location': 'N/A',
            'allele_string': 'N/A',
            'ancestral_allele': 'N/A',
            'MAF': 'N/A',
            'most_severe_consequence': 'N/A',
            'success': False,
            'error': f'Ensembl API request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'name': variant_id,
            'assembly_name': 'N/A',
            'location': 'N/A',
            'allele_string': 'N/A',
            'ancestral_allele': 'N/A',
            'MAF': 'N/A',
            'most_severe_consequence': 'N/A',
            'success': False,
            'error': f'Error fetching variant data: {str(e)}'
        }


def fetch_disease_data(disease_search_term: str) -> Dict:
    """
    Fetch all data for a disease including associated genes and phenotypes from local database.

    Args:
        disease_search_term: Disease name or database ID (e.g., 'Breast cancer' or 'OMIM:114480')

    Returns:
        Dictionary with genes, phenotypes, and disease_info
    """
    try:
        # Search for disease by ID or name
        disease = None

        # Check if it's a database ID (contains a colon)
        if ':' in disease_search_term:
            disease = Disease.objects.filter(database_id=disease_search_term).first()
        else:
            # Search by name (case-insensitive partial match)
            disease = Disease.objects.filter(
                disease_name__icontains=disease_search_term
            ).first()

        if not disease:
            return {
                'genes': [],
                'phenotypes': [],
                'disease_info': None,
                'error': f'Disease "{disease_search_term}" not found in local HPO database. '
                         'Try searching with at least 5 characters or use autocomplete.'
            }

        # Get associated genes
        genes = []
        gene_associations = GeneDiseaseAssociation.objects.filter(
            disease=disease
        ).select_related('gene')

        for assoc in gene_associations:
            genes.append({
                'gene_symbol': assoc.gene.gene_symbol,
                'entrez_id': assoc.gene.entrez_id
            })

        # Get associated phenotypes with frequency information
        phenotypes = []
        phenotype_associations = DiseasePhenotypeAssociation.objects.filter(
            disease=disease
        ).select_related('hpo_term')

        for assoc in phenotype_associations:
            phenotypes.append({
                'hpo_id': assoc.hpo_term.hpo_id,
                'name': assoc.hpo_term.name,
                'definition': assoc.hpo_term.definition or 'No definition available',
                'frequency': assoc.frequency or 'Not specified'
            })

        # Return results
        return {
            'genes': genes,
            'phenotypes': phenotypes,
            'disease_info': {
                'disease_id': disease.database_id,
                'disease_name': disease.disease_name,
                'database': disease.database
            }
        }

    except Exception as e:
        print(f"Error searching local HPO database for disease {disease_search_term}: {e}")
        return {
            'genes': [],
            'phenotypes': [],
            'disease_info': None,
            'error': f'Database error: {str(e)}'
        }
