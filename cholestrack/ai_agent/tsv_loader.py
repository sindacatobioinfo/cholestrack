"""
Helper functions for loading and parsing TSV variant data files.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_tsv_preview(file_path: str, num_rows: int = 5) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load a preview of TSV file data.

    Args:
        file_path: Full path to the TSV file
        num_rows: Number of data rows to load (default: 5)

    Returns:
        Tuple of (DataFrame with preview data, error message if failed)
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return None, f"File not found: {file_path}"

        # Read TSV with tab delimiter
        df = pd.read_csv(
            file_path,
            sep='\t',
            nrows=num_rows,
            low_memory=False
        )

        return df, None

    except Exception as e:
        return None, f"Error reading file: {str(e)}"


def format_dataframe_for_ai(df: pd.DataFrame, max_cols: int = 50) -> str:
    """
    Format DataFrame for AI consumption - shows structure and sample data.

    Args:
        df: DataFrame to format
        max_cols: Maximum number of columns to show (default: 50)

    Returns:
        Formatted string representation
    """
    if df is None or df.empty:
        return "No data available"

    # Show first N columns if too many
    if len(df.columns) > max_cols:
        cols_to_show = list(df.columns[:max_cols])
        df_display = df[cols_to_show]
        additional_cols = len(df.columns) - max_cols
        note = f"\n[Note: Showing {max_cols} of {len(df.columns)} columns. {additional_cols} additional columns available]\n"
    else:
        df_display = df
        note = ""

    # Convert to string with proper formatting
    output = note
    output += f"Columns: {', '.join(df_display.columns)}\n\n"
    output += "Sample data:\n"
    output += df_display.to_string(index=False, max_rows=10)

    return output


def get_column_summary(df: pd.DataFrame) -> Dict[str, any]:
    """
    Get summary statistics for DataFrame columns.

    Returns:
        Dictionary with column info: dtypes, non-null counts, unique values
    """
    if df is None or df.empty:
        return {}

    summary = {
        'total_columns': len(df.columns),
        'total_rows': len(df),
        'columns': {}
    }

    for col in df.columns:
        summary['columns'][col] = {
            'dtype': str(df[col].dtype),
            'non_null': int(df[col].count()),
            'null_count': int(df[col].isna().sum()),
            'unique_values': int(df[col].nunique())
        }

    return summary


def extract_sample_from_filename(file_path: str) -> Optional[str]:
    """
    Extract sample ID from file path (usually in filename).

    Args:
        file_path: Path to the file

    Returns:
        Extracted sample ID or None
    """
    try:
        filename = Path(file_path).name
        # Common pattern: sampleID_rawdata.txt or sampleID.tsv
        if '_rawdata' in filename:
            return filename.split('_rawdata')[0]
        elif '.tsv' in filename:
            return filename.split('.tsv')[0]
        return None
    except:
        return None


# Column documentation for variant TSV files
TSV_COLUMN_DESCRIPTIONS = {
    # Core variant identification
    'chr': 'Chromosome',
    'start_bp': 'Start position (base pairs)',
    'end_bp': 'End position (base pairs)',
    'ref': 'Reference allele',
    'alt': 'Alternate allele',
    'sample': 'Sample identifier',

    # Gene annotation
    'gene_ref_gene': 'Gene symbol (RefGene)',
    'func_ref_gene': 'Functional region (RefGene): exonic, intronic, UTR, etc.',
    'exonic_func_ref_gene': 'Exonic function: synonymous, nonsynonymous, frameshift, etc.',
    'aa_change_ref_gene': 'Amino acid change',
    'gene_detail_ref_gene': 'Detailed gene annotation',

    # Population frequencies
    'x1000g2015aug_all': '1000 Genomes Project allele frequency',
    'gnomad41_genome_af': 'gnomAD v4.1 genome allele frequency (all populations)',
    'gnomad41_genome_af_afr': 'gnomAD v4.1 African/African American',
    'gnomad41_genome_af_amr': 'gnomAD v4.1 Latino/Admixed American',
    'gnomad41_genome_af_asj': 'gnomAD v4.1 Ashkenazi Jewish',
    'gnomad41_genome_af_eas': 'gnomAD v4.1 East Asian',
    'gnomad41_genome_af_fin': 'gnomAD v4.1 Finnish',
    'gnomad41_genome_af_nfe': 'gnomAD v4.1 Non-Finnish European',
    'gnomad41_genome_af_sas': 'gnomAD v4.1 South Asian',
    'ex_ac_all': 'ExAC allele frequency (all populations)',

    # Clinical significance
    'clnsig': 'ClinVar clinical significance',
    'clndn': 'ClinVar disease name',
    'clndisdb': 'ClinVar disease database references',
    'clnrevstat': 'ClinVar review status',

    # Pathogenicity predictions
    'sift_pred': 'SIFT prediction: D(amaging), T(olerated)',
    'sift_score': 'SIFT score (0-1, lower = more deleterious)',
    'polyphen2_hdiv_pred': 'PolyPhen2 HDIV prediction',
    'polyphen2_hvar_pred': 'PolyPhen2 HVAR prediction',
    'cadd_phred': 'CADD Phred-scaled score (higher = more deleterious)',
    'revel_score': 'REVEL score for missense variants',
    'meta_svm_pred': 'MetaSVM ensemble prediction',
    'meta_lr_pred': 'MetaLR ensemble prediction',

    # Conservation scores
    'gerp_rs': 'GERP++ RS score (conservation)',
    'phylo_p100way_vertebrate': 'PhyloP 100-way vertebrate conservation',
    'phast_cons100way_vertebrate': 'PhastCons 100-way vertebrate conservation',

    # Genotype information
    'GT': 'Genotype (0/0, 0/1, 1/1)',
    'genotype': 'Genotype classification',
    'DP': 'Read depth',
    'GQ': 'Genotype quality',
    'AD': 'Allelic depths',
    'AB': 'Allele balance',

    # Quality metrics
    'filter': 'Variant filter status (PASS, etc.)',
    'FT': 'Filter tag',

    # Database IDs
    'avsnp154': 'dbSNP rs identifier',
    'cosmic101': 'COSMIC database identifier',
}
