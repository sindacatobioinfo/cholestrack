# region_selection/utils.py
"""
Utility functions for BAM region extraction.
"""

import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from django.conf import settings


def get_temp_directory():
    """
    Get or create a temporary directory for BAM extraction.
    Returns a path to a temporary directory.
    """
    temp_base = getattr(settings, 'REGION_EXTRACTION_TEMP_DIR', None)

    if not temp_base:
        # Use system temp directory if not configured
        temp_base = os.path.join(tempfile.gettempdir(), 'cholestrack_extractions')

    # Create the directory if it doesn't exist
    os.makedirs(temp_base, exist_ok=True)

    return temp_base


def get_gene_coordinates(gene_name):
    """
    Convert gene name to genomic coordinates based on GRCh38/hg38 reference genome.

    Args:
        gene_name (str): Gene symbol (e.g., 'BRCA1', 'TP53')

    Returns:
        dict: Dictionary with 'chromosome', 'start', 'end' keys, or None if not found

    Note:
        This is a placeholder implementation. In production, you would:
        1. Use a gene annotation database (e.g., UCSC genes, GENCODE)
        2. Query a REST API (e.g., MyGene.info, Ensembl REST API)
        3. Use a local gene annotation file (GTF/GFF)

    All coordinates are based on GRCh38/hg38 reference genome.
    """

    # TODO: Replace this with actual gene database lookup
    # This is a small example dataset for demonstration
    # All coordinates are for GRCh38/hg38 reference genome
    COMMON_GENES = {
        'BRCA1': {'chromosome': 'chr17', 'start': 43044295, 'end': 43125483},
        'BRCA2': {'chromosome': 'chr13', 'start': 32315474, 'end': 32400266},
        'TP53': {'chromosome': 'chr17', 'start': 7661779, 'end': 7687550},
        'CFTR': {'chromosome': 'chr7', 'start': 117480025, 'end': 117668665},
        'APOE': {'chromosome': 'chr19', 'start': 44905791, 'end': 44909393},
        'EGFR': {'chromosome': 'chr7', 'start': 55086714, 'end': 55275031},
        'KRAS': {'chromosome': 'chr12', 'start': 25205246, 'end': 25250929},
        'MYC': {'chromosome': 'chr8', 'start': 127735434, 'end': 127742951},
        'HBB': {'chromosome': 'chr11', 'start': 5225464, 'end': 5229395},
        'DMD': {'chromosome': 'chrX', 'start': 31119222, 'end': 33339388},
    }

    gene_upper = gene_name.upper().strip()

    if gene_upper in COMMON_GENES:
        return COMMON_GENES[gene_upper]

    # If not found in predefined list, try to load from a gene annotation file
    gene_db_path = getattr(settings, 'GENE_DATABASE_PATH', None)
    if gene_db_path and os.path.exists(gene_db_path):
        try:
            # Assume JSON format: {"GENE_NAME": {"chromosome": "chr1", "start": 123, "end": 456}}
            with open(gene_db_path, 'r') as f:
                gene_db = json.load(f)
                if gene_upper in gene_db:
                    return gene_db[gene_upper]
        except Exception as e:
            print(f"Error loading gene database: {e}")

    return None


def extract_bam_region(job):
    """
    Extract a specific region from a BAM file using samtools.
    Uses the file_path from files app to locate the BAM file.

    Args:
        job (RegionExtractionJob): The extraction job object

    Returns:
        str: Path to the extracted BAM file

    Raises:
        Exception: If extraction fails
    """

    # Get the original BAM file path from files app
    # Use file_path field which contains relative path
    remote_files_root = getattr(settings, 'REMOTE_FILES_ROOT', settings.MEDIA_ROOT / 'remote_files')
    file_path_relative = job.original_bam_file.file_path

    # Construct full path to original BAM
    original_bam_path = Path(remote_files_root) / file_path_relative

    # Security: Resolve the path and ensure it's within allowed directory
    try:
        original_bam_path = original_bam_path.resolve()
        remote_files_root_resolved = Path(remote_files_root).resolve()

        if not str(original_bam_path).startswith(str(remote_files_root_resolved)):
            raise ValueError("Invalid file path - security violation")
    except (ValueError, OSError) as e:
        raise Exception(f"Path resolution error: {e}")

    # Check if original BAM file exists
    if not original_bam_path.exists():
        raise FileNotFoundError(f"Original BAM file not found: {original_bam_path}")

    if not original_bam_path.is_file():
        raise ValueError(f"Path is not a file: {original_bam_path}")

    # Get region specification
    region = job.get_region_string()
    if not region:
        raise ValueError("Invalid region specification")

    # Create temporary directory for this job
    temp_dir = get_temp_directory()
    job_temp_dir = os.path.join(temp_dir, str(job.job_id))
    os.makedirs(job_temp_dir, exist_ok=True)

    # Temporary copy of original BAM (for processing)
    temp_original_bam = os.path.join(job_temp_dir, "original_temp.bam")

    # Output file path
    output_bam_path = os.path.join(job_temp_dir, f"{job.sample_id}_extracted.bam")

    try:
        # Check if samtools is available
        check_samtools()

        # Copy original BAM to temp directory
        # Note: For large files over network, this may take time
        print(f"Copying BAM file to temp directory: {original_bam_path} -> {temp_original_bam}")
        shutil.copy2(original_bam_path, temp_original_bam)

        # Also copy BAM index if it exists (.bai)
        original_bai_path = Path(str(original_bam_path).replace('.bam', '.bai'))
        temp_original_bai = os.path.join(job_temp_dir, "original_temp.bai")
        if original_bai_path.exists():
            print(f"Copying BAM index to temp directory: {original_bai_path} -> {temp_original_bai}")
            shutil.copy2(original_bai_path, temp_original_bai)

        # Run samtools view to extract the region
        print(f"Extracting region {region} from BAM file...")
        cmd = [
            'samtools', 'view',
            '-b',  # Output BAM format
            '-h',  # Include header
            temp_original_bam,
            region,
            '-o', output_bam_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"Samtools extraction failed: {result.stderr}")

        # Verify output file was created
        if not os.path.exists(output_bam_path) or os.path.getsize(output_bam_path) == 0:
            raise Exception("Extraction produced no output. The region may be empty or invalid.")

        # Delete the temporary original BAM file to save space
        if os.path.exists(temp_original_bam):
            os.remove(temp_original_bam)
            print(f"Deleted temporary original BAM: {temp_original_bam}")

        # Delete the temporary original BAI file if it exists
        if os.path.exists(temp_original_bai):
            os.remove(temp_original_bai)
            print(f"Deleted temporary original BAI: {temp_original_bai}")

        return output_bam_path

    except Exception as e:
        # Cleanup on failure
        if os.path.exists(job_temp_dir):
            shutil.rmtree(job_temp_dir, ignore_errors=True)
        raise e


def create_bam_index(bam_file_path):
    """
    Create a BAM index file using samtools.

    Args:
        bam_file_path (str): Path to the BAM file

    Returns:
        str: Path to the index file (.bai)

    Raises:
        Exception: If indexing fails
    """

    if not os.path.exists(bam_file_path):
        raise FileNotFoundError(f"BAM file not found: {bam_file_path}")

    index_path = f"{bam_file_path}.bai"

    try:
        # Run samtools index
        cmd = ['samtools', 'index', bam_file_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"Samtools indexing failed: {result.stderr}")

        # Verify index file was created
        if not os.path.exists(index_path):
            raise Exception("Index file was not created")

        return index_path

    except Exception as e:
        raise Exception(f"Failed to create BAM index: {e}")


def check_samtools():
    """
    Check if samtools is available in the system.

    Raises:
        Exception: If samtools is not available
    """
    try:
        result = subprocess.run(
            ['samtools', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            raise Exception("Samtools not found or not working properly")

    except FileNotFoundError:
        raise Exception(
            "Samtools is not installed or not in PATH. "
            "Please install samtools to use this feature."
        )
    except Exception as e:
        raise Exception(f"Error checking samtools: {e}")


def cleanup_job_files(job):
    """
    Clean up temporary files for a completed/downloaded job.

    Args:
        job (RegionExtractionJob): The job to clean up

    Returns:
        bool: True if cleanup was successful
    """
    if not job.output_file_path:
        return False

    # Get the job's temporary directory
    job_temp_dir = os.path.dirname(job.output_file_path)

    if os.path.exists(job_temp_dir):
        try:
            shutil.rmtree(job_temp_dir)
            return True
        except Exception as e:
            print(f"Error cleaning up job {job.job_id}: {e}")
            return False

    return False


def get_file_size_mb(file_path):
    """
    Get file size in megabytes.

    Args:
        file_path (str): Path to the file

    Returns:
        float: File size in MB
    """
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    return 0.0
