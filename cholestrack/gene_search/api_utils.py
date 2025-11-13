# gene_search/api_utils.py
"""
API integration utilities for HPO, OMIM, and PharmGKB.
Fetches gene-disease-drug relationships from external databases.
"""

import requests
import time
from typing import Dict, List, Optional


class HPOClient:
    """
    Client for Human Phenotype Ontology (HPO) API.
    Documentation: https://hpo.jax.org/api/hpo/docs/
    """
    BASE_URL = "https://ontology.jax.org/api"

    @staticmethod
    def search_gene_phenotypes(gene_symbol: str) -> List[Dict]:
        """
        Search for phenotypes associated with a gene.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1', 'BRCA1')

        Returns:
            List of phenotype dictionaries with HPO terms
        """
        try:
            # Search for gene first
            search_url = f"{HPOClient.BASE_URL}/hpo/search"
            params = {
                'q': gene_symbol,
                'category': 'genes'
            }

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            search_results = response.json()

            if not search_results or 'genes' not in search_results:
                return []

            genes = search_results.get('genes', [])
            if not genes:
                return []

            # Get the first matching gene
            gene = genes[0]
            gene_id = gene.get('dbGeneId') or gene.get('entrezGeneId')

            if not gene_id:
                return []

            # Get phenotypes for this gene
            phenotype_url = f"{HPOClient.BASE_URL}/hpo/gene/{gene_id}"
            pheno_response = requests.get(phenotype_url, timeout=10)
            pheno_response.raise_for_status()

            pheno_data = pheno_response.json()

            phenotypes = []
            if 'termAssoc' in pheno_data:
                for term in pheno_data['termAssoc']:
                    phenotypes.append({
                        'hpo_id': term.get('ontologyId'),
                        'name': term.get('name'),
                        'definition': term.get('definition', 'No definition available')
                    })

            return phenotypes

        except requests.RequestException as e:
            print(f"Error fetching HPO data for {gene_symbol}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in HPO search: {e}")
            return []


class OMIMClient:
    """
    Client for OMIM (Online Mendelian Inheritance in Man) API.
    Note: OMIM requires API key for full access.
    Documentation: https://omim.org/api
    """
    BASE_URL = "https://api.omim.org/api"

    @staticmethod
    def search_gene_diseases(gene_symbol: str, api_key: Optional[str] = None) -> List[Dict]:
        """
        Search for diseases associated with a gene in OMIM.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1')
            api_key: OMIM API key (required for full access)

        Returns:
            List of disease dictionaries with OMIM IDs and names
        """
        try:
            if not api_key:
                # Use public OMIM web search as fallback
                return OMIMClient._search_omim_web(gene_symbol)

            # Use official API if key provided
            search_url = f"{OMIMClient.BASE_URL}/entry/search"
            params = {
                'search': f'approved_gene_symbol:{gene_symbol}',
                'format': 'json',
                'apiKey': api_key,
                'include': 'geneMap'
            }

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            diseases = []
            if 'omim' in data and 'searchResponse' in data['omim']:
                entries = data['omim']['searchResponse'].get('entryList', [])

                for entry in entries:
                    entry_data = entry.get('entry', {})
                    omim_id = entry_data.get('mimNumber')
                    titles = entry_data.get('titles', {})
                    preferred_title = titles.get('preferredTitle', 'Unknown')

                    if omim_id:
                        diseases.append({
                            'omim_id': omim_id,
                            'name': preferred_title,
                            'gene_symbol': gene_symbol
                        })

            return diseases

        except requests.RequestException as e:
            print(f"Error fetching OMIM data for {gene_symbol}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in OMIM search: {e}")
            return []

    @staticmethod
    def _search_omim_web(gene_symbol: str) -> List[Dict]:
        """
        Fallback method using MyGene.info which aggregates OMIM data.

        Args:
            gene_symbol: Gene symbol

        Returns:
            List of disease associations
        """
        try:
            # Use MyGene.info API as a free alternative
            url = "https://mygene.info/v3/query"
            params = {
                'q': f'symbol:{gene_symbol}',
                'fields': 'MIM,name,symbol',
                'species': 'human'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            diseases = []

            if 'hits' in data and data['hits']:
                for hit in data['hits']:
                    if 'MIM' in hit:
                        mim_data = hit['MIM']

                        # MIM can be a single ID or list
                        if isinstance(mim_data, list):
                            for mim_id in mim_data:
                                diseases.append({
                                    'omim_id': mim_id,
                                    'name': hit.get('name', 'Unknown'),
                                    'gene_symbol': gene_symbol
                                })
                        elif isinstance(mim_data, (int, str)):
                            diseases.append({
                                'omim_id': str(mim_data),
                                'name': hit.get('name', 'Unknown'),
                                'gene_symbol': gene_symbol
                            })

            return diseases

        except Exception as e:
            print(f"Error in OMIM web search fallback: {e}")
            return []


class PharmGKBClient:
    """
    Client for PharmGKB (Pharmacogenomics Knowledge Base) API.
    Documentation: https://www.pharmgkb.org/page/dataApiIntro
    """
    BASE_URL = "https://api.pharmgkb.org/v1/data"

    @staticmethod
    def search_gene_drugs(gene_symbol: str) -> List[Dict]:
        """
        Search for drug-gene relationships and ADME genes.

        Args:
            gene_symbol: Gene symbol (e.g., 'ATP8B1')

        Returns:
            List of pharmacogenetics associations
        """
        try:
            # Search for gene
            gene_url = f"{PharmGKBClient.BASE_URL}/gene/{gene_symbol}"

            response = requests.get(gene_url, timeout=10)

            # PharmGKB may return 404 if gene not found
            if response.status_code == 404:
                return []

            response.raise_for_status()
            gene_data = response.json()

            pharmgkb_data = []

            # Get clinical annotations
            if 'clinicalAnnotations' in gene_data:
                for annotation in gene_data['clinicalAnnotations']:
                    pharmgkb_data.append({
                        'type': 'Clinical Annotation',
                        'gene': gene_symbol,
                        'drug': annotation.get('drug', {}).get('name', 'Unknown'),
                        'phenotype': annotation.get('phenotype', 'Unknown'),
                        'significance': annotation.get('significance', 'Unknown'),
                        'pmid': annotation.get('pmid', [])
                    })

            # Get variant annotations
            if 'variantAnnotations' in gene_data:
                for variant in gene_data['variantAnnotations']:
                    pharmgkb_data.append({
                        'type': 'Variant Annotation',
                        'gene': gene_symbol,
                        'variant': variant.get('variant', {}).get('name', 'Unknown'),
                        'drug': variant.get('drug', {}).get('name', 'Unknown'),
                        'effect': variant.get('effect', 'Unknown')
                    })

            return pharmgkb_data

        except requests.RequestException as e:
            print(f"Error fetching PharmGKB data for {gene_symbol}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in PharmGKB search: {e}")
            return []

    @staticmethod
    def search_gene_drugs_alternative(gene_symbol: str) -> List[Dict]:
        """
        Alternative method using PubChem and DrugBank APIs for drug-gene relationships.

        Args:
            gene_symbol: Gene symbol

        Returns:
            List of drug-gene associations
        """
        try:
            # Use MyGene.info which aggregates pharmgkb data
            url = "https://mygene.info/v3/query"
            params = {
                'q': f'symbol:{gene_symbol}',
                'fields': 'pharmgkb,pathway.pharmgkb',
                'species': 'human'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            drug_associations = []

            if 'hits' in data and data['hits']:
                for hit in data['hits']:
                    if 'pharmgkb' in hit:
                        drug_associations.append({
                            'type': 'PharmGKB Association',
                            'gene': gene_symbol,
                            'pharmgkb_id': hit.get('pharmgkb'),
                            'source': 'MyGene.info aggregation'
                        })

            return drug_associations

        except Exception as e:
            print(f"Error in alternative PharmGKB search: {e}")
            return []


def fetch_all_relationships(gene_symbol: str, omim_api_key: Optional[str] = None) -> Dict:
    """
    Fetch all relationships for a gene from HPO, OMIM, and PharmGKB.

    Args:
        gene_symbol: Gene symbol (e.g., 'ATP8B1')
        omim_api_key: Optional OMIM API key

    Returns:
        Dictionary with hpo_results, omim_results, and pharmgkb_results
    """
    results = {
        'hpo_results': [],
        'omim_results': [],
        'pharmgkb_results': []
    }

    # Fetch HPO phenotypes
    hpo_client = HPOClient()
    results['hpo_results'] = hpo_client.search_gene_phenotypes(gene_symbol)

    # Small delay to avoid rate limiting
    time.sleep(0.5)

    # Fetch OMIM diseases
    omim_client = OMIMClient()
    results['omim_results'] = omim_client.search_gene_diseases(gene_symbol, omim_api_key)

    # Small delay to avoid rate limiting
    time.sleep(0.5)

    # Fetch PharmGKB drug associations
    pharmgkb_client = PharmGKBClient()
    pharmgkb_results = pharmgkb_client.search_gene_drugs(gene_symbol)

    # If primary method fails, try alternative
    if not pharmgkb_results:
        pharmgkb_results = pharmgkb_client.search_gene_drugs_alternative(gene_symbol)

    results['pharmgkb_results'] = pharmgkb_results

    return results
