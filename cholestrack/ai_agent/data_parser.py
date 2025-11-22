"""
TSV data parser and analysis tools for variant data files.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class TSVVariantParser:
    """
    Parser for TSV variant data files (_rawdata.txt files).
    """

    def __init__(self, file_path: str):
        """
        Initialize parser with file path.

        Args:
            file_path: Path to TSV file
        """
        self.file_path = Path(file_path)
        self.df = None
        self._load_data()

    def _load_data(self):
        """Load TSV data into pandas DataFrame."""
        try:
            self.df = pd.read_csv(self.file_path, sep='\t', low_memory=False)
            # Strip whitespace from column names
            self.df.columns = self.df.columns.str.strip()
        except Exception as e:
            raise ValueError(f"Error loading TSV file {self.file_path}: {str(e)}")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the variant data.

        Returns:
            Dictionary with summary stats
        """
        stats = {
            'total_variants': len(self.df),
            'chromosomes': self.df['CHROM'].unique().tolist() if 'CHROM' in self.df.columns else [],
            'variant_types': {},
            'impact_distribution': {},
            'quality_metrics': {},
        }

        # Variant types (SNV, INDEL, etc.)
        if 'REF' in self.df.columns and 'ALT' in self.df.columns:
            def classify_variant(row):
                ref_len = len(str(row['REF']))
                alt_len = len(str(row['ALT']))
                if ref_len == 1 and alt_len == 1:
                    return 'SNV'
                elif ref_len != alt_len:
                    return 'INDEL'
                else:
                    return 'COMPLEX'

            variant_types = self.df.apply(classify_variant, axis=1).value_counts().to_dict()
            stats['variant_types'] = variant_types

        # Impact distribution
        if 'IMPACT' in self.df.columns:
            stats['impact_distribution'] = self.df['IMPACT'].value_counts().to_dict()

        # Quality metrics
        if 'QUAL' in self.df.columns:
            stats['quality_metrics']['mean_qual'] = float(self.df['QUAL'].mean())
            stats['quality_metrics']['median_qual'] = float(self.df['QUAL'].median())

        if 'DP' in self.df.columns:
            stats['quality_metrics']['mean_depth'] = float(self.df['DP'].mean())
            stats['quality_metrics']['median_depth'] = float(self.df['DP'].median())

        return stats

    def filter_by_quality(
        self,
        min_qual: Optional[float] = None,
        min_depth: Optional[int] = None,
        min_gq: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Filter variants by quality metrics.

        Args:
            min_qual: Minimum QUAL score
            min_depth: Minimum depth (DP)
            min_gq: Minimum genotype quality (GQ)

        Returns:
            Filtered DataFrame
        """
        filtered_df = self.df.copy()

        if min_qual is not None and 'QUAL' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['QUAL'] >= min_qual]

        if min_depth is not None and 'DP' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['DP'] >= min_depth]

        if min_gq is not None and 'GQ' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['GQ'] >= min_gq]

        return filtered_df

    def filter_by_impact(self, impacts: List[str]) -> pd.DataFrame:
        """
        Filter variants by impact level.

        Args:
            impacts: List of impact levels (e.g., ['HIGH', 'MODERATE'])

        Returns:
            Filtered DataFrame
        """
        if 'IMPACT' not in self.df.columns:
            return self.df.copy()

        return self.df[self.df['IMPACT'].isin(impacts)]

    def filter_by_frequency(
        self,
        max_gnomad_af: Optional[float] = None,
        max_af: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Filter variants by allele frequency.

        Args:
            max_gnomad_af: Maximum gnomAD allele frequency
            max_af: Maximum allele frequency

        Returns:
            Filtered DataFrame
        """
        filtered_df = self.df.copy()

        if max_gnomad_af is not None and 'gnomAD_AF' in filtered_df.columns:
            # Handle NaN values (treat as rare)
            filtered_df = filtered_df[
                (filtered_df['gnomAD_AF'].isna()) |
                (filtered_df['gnomAD_AF'] <= max_gnomad_af)
            ]

        if max_af is not None and 'AF' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['AF'].isna()) |
                (filtered_df['AF'] <= max_af)
            ]

        return filtered_df

    def filter_by_genes(self, gene_list: List[str]) -> pd.DataFrame:
        """
        Filter variants to specific genes.

        Args:
            gene_list: List of gene symbols

        Returns:
            Filtered DataFrame
        """
        if 'GENE' not in self.df.columns:
            return pd.DataFrame()  # Empty if no gene column

        # Handle multiple genes in one field (comma-separated)
        mask = self.df['GENE'].apply(
            lambda x: any(gene in str(x).split(',') for gene in gene_list) if pd.notna(x) else False
        )

        return self.df[mask]

    def get_variants_by_chromosome(self, chromosome: str) -> pd.DataFrame:
        """
        Get all variants on a specific chromosome.

        Args:
            chromosome: Chromosome name (e.g., 'chr1', '1')

        Returns:
            Filtered DataFrame
        """
        if 'CHROM' not in self.df.columns:
            return pd.DataFrame()

        # Handle both 'chr1' and '1' formats
        mask = (self.df['CHROM'] == chromosome) | (self.df['CHROM'] == f'chr{chromosome}')
        return self.df[mask]

    def get_gene_list(self) -> List[str]:
        """
        Get list of unique genes in dataset.

        Returns:
            List of gene symbols
        """
        if 'GENE' not in self.df.columns:
            return []

        genes = set()
        for gene_str in self.df['GENE'].dropna():
            # Handle comma-separated genes
            genes.update(str(gene_str).split(','))

        return sorted([g.strip() for g in genes if g.strip()])

    def export_to_csv(self, output_path: str, dataframe: Optional[pd.DataFrame] = None):
        """
        Export data to CSV file.

        Args:
            output_path: Output file path
            dataframe: DataFrame to export (defaults to self.df)
        """
        df_to_export = dataframe if dataframe is not None else self.df
        df_to_export.to_csv(output_path, index=False)

    def export_to_excel(self, output_path: str, dataframe: Optional[pd.DataFrame] = None):
        """
        Export data to Excel file.

        Args:
            output_path: Output file path
            dataframe: DataFrame to export (defaults to self.df)
        """
        df_to_export = dataframe if dataframe is not None else self.df
        df_to_export.to_excel(output_path, index=False, engine='openpyxl')


class MultiSampleAnalyzer:
    """
    Analyze and compare variants across multiple samples.
    """

    def __init__(self, sample_file_paths: Dict[str, str]):
        """
        Initialize with multiple sample files.

        Args:
            sample_file_paths: Dict mapping sample_id to file path
        """
        self.parsers = {}
        for sample_id, file_path in sample_file_paths.items():
            self.parsers[sample_id] = TSVVariantParser(file_path)

    def get_comparative_statistics(self) -> Dict[str, Any]:
        """
        Get comparative statistics across all samples.

        Returns:
            Dictionary with comparative stats
        """
        stats = {}
        for sample_id, parser in self.parsers.items():
            stats[sample_id] = parser.get_summary_statistics()

        return stats

    def find_shared_variants(
        self,
        min_samples: int = 2,
        position_tolerance: int = 0
    ) -> pd.DataFrame:
        """
        Find variants present in multiple samples.

        Args:
            min_samples: Minimum number of samples that must share the variant
            position_tolerance: Position tolerance for matching (bp)

        Returns:
            DataFrame of shared variants
        """
        if len(self.parsers) < 2:
            return pd.DataFrame()

        # Collect all variants from all samples
        variant_locations = defaultdict(list)

        for sample_id, parser in self.parsers.items():
            if 'CHROM' in parser.df.columns and 'POS' in parser.df.columns:
                for _, row in parser.df.iterrows():
                    chrom = row['CHROM']
                    pos = row['POS']
                    key = f"{chrom}:{pos}"
                    variant_locations[key].append(sample_id)

        # Filter to variants in at least min_samples
        shared = {k: v for k, v in variant_locations.items() if len(v) >= min_samples}

        # Build result DataFrame
        results = []
        for location, samples in shared.items():
            chrom, pos = location.split(':')
            results.append({
                'CHROM': chrom,
                'POS': int(pos),
                'num_samples': len(samples),
                'sample_ids': ','.join(samples)
            })

        return pd.DataFrame(results)

    def find_unique_variants(self, sample_id: str) -> pd.DataFrame:
        """
        Find variants unique to a specific sample.

        Args:
            sample_id: Sample to find unique variants for

        Returns:
            DataFrame of unique variants
        """
        if sample_id not in self.parsers:
            return pd.DataFrame()

        target_parser = self.parsers[sample_id]
        other_parsers = {sid: p for sid, p in self.parsers.items() if sid != sample_id}

        if not other_parsers:
            return target_parser.df.copy()

        # Build set of variant positions from other samples
        other_positions = set()
        for parser in other_parsers.values():
            if 'CHROM' in parser.df.columns and 'POS' in parser.df.columns:
                for _, row in parser.df.iterrows():
                    other_positions.add(f"{row['CHROM']}:{row['POS']}")

        # Filter target sample to positions not in others
        if 'CHROM' in target_parser.df.columns and 'POS' in target_parser.df.columns:
            unique_mask = target_parser.df.apply(
                lambda row: f"{row['CHROM']}:{row['POS']}" not in other_positions,
                axis=1
            )
            return target_parser.df[unique_mask]

        return pd.DataFrame()
