# smart_search/api_utils.py
"""
API integration utilities for HPO (Human Phenotype Ontology).
Fetches gene-phenotype-disease relationships from the HPO API.
"""

import requests
from typing import Dict, List


class HPOClient:
    """
    Client for Human Phenotype Ontology (HPO) API.
    Documentation: https://hpo.jax.org/api/hpo/docs/
    """
    BASE_URL = "https://ontology.jax.org/api"

    @staticmethod
    def search_gene(gene_symbol: str) -> Dict:
        """
        Search for phenotypes and diseases associated with a gene.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1', 'BRCA1')

        Returns:
            Dictionary with:
            - phenotypes: List of HPO phenotype terms
            - diseases: List of associated diseases
            - gene_info: Gene information from HPO
        """
        try:
            # Step 1: Search for gene first
            search_url = f"{HPOClient.BASE_URL}/hpo/search"
            params = {
                'q': gene_symbol,
                'category': 'genes'
            }

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            search_results = response.json()

            if not search_results or 'genes' not in search_results:
                return {
                    'phenotypes': [],
                    'diseases': [],
                    'gene_info': None,
                    'error': 'Gene not found in HPO database'
                }

            genes = search_results.get('genes', [])
            if not genes:
                return {
                    'phenotypes': [],
                    'diseases': [],
                    'gene_info': None,
                    'error': 'Gene not found in HPO database'
                }

            # Get the first matching gene
            gene = genes[0]
            gene_id = gene.get('dbGeneId') or gene.get('entrezGeneId')

            if not gene_id:
                return {
                    'phenotypes': [],
                    'diseases': [],
                    'gene_info': gene,
                    'error': 'Gene ID not available'
                }

            # Step 2: Get detailed gene information including phenotypes and diseases
            gene_url = f"{HPOClient.BASE_URL}/hpo/gene/{gene_id}"
            gene_response = requests.get(gene_url, timeout=10)
            gene_response.raise_for_status()

            gene_data = gene_response.json()

            # Extract phenotypes (HPO terms)
            phenotypes = []
            if 'termAssoc' in gene_data:
                for term in gene_data['termAssoc']:
                    phenotypes.append({
                        'hpo_id': term.get('ontologyId'),
                        'name': term.get('name'),
                        'definition': term.get('definition', 'No definition available')
                    })

            # Extract diseases from gene data
            diseases = []
            if 'diseaseAssoc' in gene_data:
                for disease in gene_data['diseaseAssoc']:
                    diseases.append({
                        'disease_id': disease.get('diseaseId'),
                        'disease_name': disease.get('diseaseName'),
                        'database': disease.get('db', 'HPO')
                    })

            # If diseaseAssoc is not available, try to get diseases from dbDiseases
            if not diseases and 'dbDiseases' in gene_data:
                for disease in gene_data['dbDiseases']:
                    diseases.append({
                        'disease_id': disease.get('diseaseId') or f"{disease.get('db')}:{disease.get('dbId')}",
                        'disease_name': disease.get('diseaseName'),
                        'database': disease.get('db', 'HPO')
                    })

            return {
                'phenotypes': phenotypes,
                'diseases': diseases,
                'gene_info': {
                    'gene_symbol': gene.get('geneSymbol') or gene_symbol,
                    'gene_id': gene_id,
                    'entrez_id': gene.get('entrezGeneId')
                }
            }

        except requests.RequestException as e:
            print(f"Error fetching HPO data for {gene_symbol}: {e}")
            return {
                'phenotypes': [],
                'diseases': [],
                'gene_info': None,
                'error': f'API request failed: {str(e)}'
            }
        except Exception as e:
            print(f"Unexpected error in HPO search: {e}")
            return {
                'phenotypes': [],
                'diseases': [],
                'gene_info': None,
                'error': f'Unexpected error: {str(e)}'
            }


def fetch_gene_data(gene_symbol: str) -> Dict:
    """
    Fetch all HPO data for a gene including phenotypes and diseases.

    Args:
        gene_symbol: Gene symbol (e.g., 'ATP8B1')

    Returns:
        Dictionary with phenotypes, diseases, and gene_info
    """
    hpo_client = HPOClient()
    results = hpo_client.search_gene(gene_symbol)

    return results
