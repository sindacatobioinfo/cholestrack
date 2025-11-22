"""
Genetic inheritance model filters for variant analysis.
Supports autosomal dominant, autosomal recessive, and compound heterozygous models.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class GeneticModelFilter:
    """
    Filter variants according to genetic inheritance models.
    """

    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize with variant DataFrame.

        Args:
            dataframe: Pandas DataFrame with variant data
        """
        self.df = dataframe.copy()
        self._validate_columns()

    def _validate_columns(self):
        """Validate that required columns exist."""
        required = ['CHROM', 'POS', 'REF', 'ALT']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _parse_genotype(self, gt_string: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse genotype string into alleles.

        Args:
            gt_string: Genotype string (e.g., '0/1', '1/1', '0|1')

        Returns:
            Tuple of (allele1, allele2) or (None, None) if invalid
        """
        if pd.isna(gt_string) or gt_string == './.':
            return None, None

        # Handle both / and | separators
        gt_string = str(gt_string).replace('|', '/')

        try:
            alleles = gt_string.split('/')
            if len(alleles) == 2:
                return alleles[0], alleles[1]
        except:
            pass

        return None, None

    def _is_heterozygous(self, gt_string: str) -> bool:
        """
        Check if genotype is heterozygous.

        Args:
            gt_string: Genotype string

        Returns:
            True if heterozygous (e.g., '0/1')
        """
        allele1, allele2 = self._parse_genotype(gt_string)
        if allele1 is None or allele2 is None:
            return False

        return allele1 != allele2 and '0' in [allele1, allele2]

    def _is_homozygous_alt(self, gt_string: str) -> bool:
        """
        Check if genotype is homozygous alternate.

        Args:
            gt_string: Genotype string

        Returns:
            True if homozygous alt (e.g., '1/1')
        """
        allele1, allele2 = self._parse_genotype(gt_string)
        if allele1 is None or allele2 is None:
            return False

        return allele1 == allele2 and allele1 != '0'

    def filter_autosomal_dominant(
        self,
        max_gnomad_af: float = 0.001,
        min_qual: float = 30,
        impacts: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter for autosomal dominant inheritance pattern.

        Criteria:
        - Heterozygous variants (0/1)
        - Rare in population (low gnomAD AF)
        - High/Moderate impact preferred
        - Good quality scores

        Args:
            max_gnomad_af: Maximum gnomAD allele frequency
            min_qual: Minimum variant quality
            impacts: List of acceptable impacts (default: HIGH, MODERATE)

        Returns:
            Filtered DataFrame
        """
        if impacts is None:
            impacts = ['HIGH', 'MODERATE']

        filtered = self.df.copy()

        # Must have GT column
        if 'GT' not in filtered.columns:
            raise ValueError("GT (genotype) column not found in data")

        # Filter to heterozygous variants
        filtered = filtered[filtered['GT'].apply(self._is_heterozygous)]

        # Rare variants
        if 'gnomAD_AF' in filtered.columns:
            filtered = filtered[
                (filtered['gnomAD_AF'].isna()) |
                (filtered['gnomAD_AF'] <= max_gnomad_af)
            ]

        # Quality filter
        if 'QUAL' in filtered.columns:
            filtered = filtered[filtered['QUAL'] >= min_qual]

        # Impact filter
        if 'IMPACT' in filtered.columns:
            filtered = filtered[filtered['IMPACT'].isin(impacts)]

        return filtered

    def filter_autosomal_recessive(
        self,
        max_gnomad_af: float = 0.01,
        min_qual: float = 30,
        impacts: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter for autosomal recessive inheritance pattern.

        Criteria:
        - Homozygous alternate variants (1/1)
        - Rare to uncommon in population
        - High/Moderate impact
        - Good quality scores

        Args:
            max_gnomad_af: Maximum gnomAD allele frequency
            min_qual: Minimum variant quality
            impacts: List of acceptable impacts (default: HIGH, MODERATE)

        Returns:
            Filtered DataFrame
        """
        if impacts is None:
            impacts = ['HIGH', 'MODERATE']

        filtered = self.df.copy()

        # Must have GT column
        if 'GT' not in filtered.columns:
            raise ValueError("GT (genotype) column not found in data")

        # Filter to homozygous alternate variants
        filtered = filtered[filtered['GT'].apply(self._is_homozygous_alt)]

        # Frequency filter (can be slightly higher for recessive)
        if 'gnomAD_AF' in filtered.columns:
            filtered = filtered[
                (filtered['gnomAD_AF'].isna()) |
                (filtered['gnomAD_AF'] <= max_gnomad_af)
            ]

        # Quality filter
        if 'QUAL' in filtered.columns:
            filtered = filtered[filtered['QUAL'] >= min_qual]

        # Impact filter
        if 'IMPACT' in filtered.columns:
            filtered = filtered[filtered['IMPACT'].isin(impacts)]

        return filtered

    def filter_compound_heterozygous(
        self,
        max_gnomad_af: float = 0.01,
        min_qual: float = 30,
        impacts: Optional[List[str]] = None,
        require_both_variants: bool = True
    ) -> pd.DataFrame:
        """
        Filter for compound heterozygous inheritance pattern.

        Criteria:
        - Two or more heterozygous variants in the same gene
        - Both variants are rare
        - High/Moderate impact
        - Good quality scores

        Args:
            max_gnomad_af: Maximum gnomAD allele frequency
            min_qual: Minimum variant quality
            impacts: List of acceptable impacts (default: HIGH, MODERATE)
            require_both_variants: Require at least 2 variants per gene

        Returns:
            DataFrame with compound heterozygous candidates
        """
        if impacts is None:
            impacts = ['HIGH', 'MODERATE']

        if 'GENE' not in self.df.columns:
            raise ValueError("GENE column not found in data")

        if 'GT' not in self.df.columns:
            raise ValueError("GT (genotype) column not found in data")

        # Start with heterozygous variants
        het_variants = self.df[self.df['GT'].apply(self._is_heterozygous)].copy()

        # Apply frequency filter
        if 'gnomAD_AF' in het_variants.columns:
            het_variants = het_variants[
                (het_variants['gnomAD_AF'].isna()) |
                (het_variants['gnomAD_AF'] <= max_gnomad_af)
            ]

        # Quality filter
        if 'QUAL' in het_variants.columns:
            het_variants = het_variants[het_variants['QUAL'] >= min_qual]

        # Impact filter
        if 'IMPACT' in het_variants.columns:
            het_variants = het_variants[het_variants['IMPACT'].isin(impacts)]

        # Group by gene and find genes with 2+ variants
        gene_counts = het_variants['GENE'].value_counts()
        compound_het_genes = gene_counts[gene_counts >= 2].index.tolist()

        # Filter to variants in genes with multiple hits
        compound_het_candidates = het_variants[het_variants['GENE'].isin(compound_het_genes)]

        # Add metadata about number of variants per gene
        compound_het_candidates['variants_in_gene'] = compound_het_candidates['GENE'].map(gene_counts)

        return compound_het_candidates.sort_values(['GENE', 'POS'])

    def get_gene_variant_summary(self, filtered_df: Optional[pd.DataFrame] = None) -> Dict[str, Dict]:
        """
        Get summary of variants per gene.

        Args:
            filtered_df: DataFrame to summarize (default: self.df)

        Returns:
            Dict mapping gene to variant summary
        """
        df = filtered_df if filtered_df is not None else self.df

        if 'GENE' not in df.columns:
            return {}

        summary = {}
        for gene in df['GENE'].unique():
            if pd.isna(gene):
                continue

            gene_variants = df[df['GENE'] == gene]

            summary[gene] = {
                'total_variants': len(gene_variants),
                'chromosomes': gene_variants['CHROM'].unique().tolist() if 'CHROM' in gene_variants.columns else [],
                'impacts': gene_variants['IMPACT'].value_counts().to_dict() if 'IMPACT' in gene_variants.columns else {},
                'genotypes': gene_variants['GT'].value_counts().to_dict() if 'GT' in gene_variants.columns else {},
            }

        return summary

    def annotate_inheritance_pattern(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Add inheritance pattern annotations to variants.

        Args:
            df: DataFrame to annotate (default: self.df)

        Returns:
            DataFrame with added 'inheritance_patterns' column
        """
        data = df.copy() if df is not None else self.df.copy()

        if 'GT' not in data.columns:
            data['inheritance_patterns'] = 'Unknown'
            return data

        def classify_pattern(row):
            patterns = []

            if self._is_heterozygous(row['GT']):
                # Could be AD or part of compound het
                gnomad_af = row.get('gnomAD_AF', None)
                if pd.isna(gnomad_af) or gnomad_af <= 0.001:
                    patterns.append('AD_candidate')
                if pd.isna(gnomad_af) or gnomad_af <= 0.01:
                    patterns.append('CompHet_candidate')

            elif self._is_homozygous_alt(row['GT']):
                # Could be AR
                gnomad_af = row.get('gnomAD_AF', None)
                if pd.isna(gnomad_af) or gnomad_af <= 0.01:
                    patterns.append('AR_candidate')

            return ','.join(patterns) if patterns else 'Not_candidate'

        data['inheritance_patterns'] = data.apply(classify_pattern, axis=1)
        return data
