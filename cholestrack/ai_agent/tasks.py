"""
Celery tasks for background analysis jobs.
"""

import os
import pandas as pd
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import AnalysisJob
from .data_parser import TSVVariantParser, MultiSampleAnalyzer
from .genetic_models import GeneticModelFilter
from .report_generator import ReportGenerator
from files.models import AnalysisFileLocation


@shared_task(bind=True)
def run_statistical_analysis(self, job_id):
    """
    Run statistical analysis on variant data.

    Args:
        job_id: AnalysisJob UUID

    Returns:
        Result data dictionary
    """
    try:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_started()

        # Get sample IDs and parameters
        sample_ids = job.sample_ids
        params = job.parameters

        # Load data files
        file_paths = {}
        for sample_id in sample_ids:
            # Find the _rawdata.txt file for this sample
            file_location = AnalysisFileLocation.objects.filter(
                sample_id=sample_id,
                file_type='TSV',  # Assuming TSV files are marked as type TSV
                is_active=True
            ).first()

            if file_location:
                file_paths[sample_id] = file_location.file_location

        if not file_paths:
            raise ValueError(f"No data files found for samples: {sample_ids}")

        # Perform analysis
        if len(file_paths) == 1:
            # Single sample analysis
            sample_id, file_path = list(file_paths.items())[0]
            parser = TSVVariantParser(file_path)
            stats = parser.get_summary_statistics()
            result_data = {
                'sample_id': sample_id,
                'statistics': stats,
                'analysis_type': 'single_sample'
            }
        else:
            # Multi-sample analysis
            analyzer = MultiSampleAnalyzer(file_paths)
            stats = analyzer.get_comparative_statistics()
            result_data = {
                'statistics': stats,
                'analysis_type': 'multi_sample'
            }

        # Mark job as completed
        job.mark_completed(result_data=result_data)

        return result_data

    except Exception as e:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_failed(str(e))
        raise


@shared_task(bind=True)
def run_genetic_model_analysis(self, job_id):
    """
    Run genetic model filtering analysis.

    Args:
        job_id: AnalysisJob UUID

    Returns:
        Result data dictionary
    """
    try:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_started()

        # Get parameters
        sample_ids = job.sample_ids
        params = job.parameters
        model_type = params.get('model_type', 'autosomal_dominant')
        max_gnomad_af = params.get('max_gnomad_af', 0.001)
        min_qual = params.get('min_qual', 30)

        # Load data file (genetic models work on single samples)
        if len(sample_ids) != 1:
            raise ValueError("Genetic model analysis requires exactly one sample")

        sample_id = sample_ids[0]
        file_location = AnalysisFileLocation.objects.filter(
            sample_id=sample_id,
            file_type='TSV',
            is_active=True
        ).first()

        if not file_location:
            raise ValueError(f"No data file found for sample: {sample_id}")

        # Parse data
        parser = TSVVariantParser(file_location.file_location)
        model_filter = GeneticModelFilter(parser.df)

        # Apply genetic model filter
        if model_type == 'autosomal_dominant':
            filtered_df = model_filter.filter_autosomal_dominant(
                max_gnomad_af=max_gnomad_af,
                min_qual=min_qual
            )
        elif model_type == 'autosomal_recessive':
            filtered_df = model_filter.filter_autosomal_recessive(
                max_gnomad_af=max_gnomad_af,
                min_qual=min_qual
            )
        elif model_type == 'compound_heterozygous':
            filtered_df = model_filter.filter_compound_heterozygous(
                max_gnomad_af=max_gnomad_af,
                min_qual=min_qual
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Get gene summary
        gene_summary = model_filter.get_gene_variant_summary(filtered_df)

        result_data = {
            'sample_id': sample_id,
            'model_type': model_type,
            'total_variants_found': len(filtered_df),
            'genes_affected': len(gene_summary),
            'gene_summary': gene_summary,
        }

        # Generate report if requested
        report_format = params.get('report_format', None)
        if report_format:
            report_gen = ReportGenerator()
            output_dir = Path(settings.MEDIA_ROOT) / 'ai_agent_reports' / str(job.session.user.id)
            output_dir.mkdir(parents=True, exist_ok=True)

            report_filename = f"{sample_id}_{model_type}_{job.job_id}.{report_format}"
            report_path = output_dir / report_filename

            if report_format == 'csv':
                filtered_df.to_csv(report_path, index=False)
            elif report_format == 'xlsx':
                filtered_df.to_excel(report_path, index=False, engine='openpyxl')
            elif report_format == 'html':
                html_content = report_gen.generate_genetic_model_report(
                    filtered_df=filtered_df,
                    model_type=model_type,
                    gene_summary=gene_summary,
                    sample_id=sample_id
                )
                report_path.write_text(html_content)

            # Save report path
            job.mark_completed(
                result_data=result_data,
                result_file_path=str(report_path),
                result_file_type=report_format
            )
        else:
            job.mark_completed(result_data=result_data)

        return result_data

    except Exception as e:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_failed(str(e))
        raise


@shared_task(bind=True)
def run_comparative_analysis(self, job_id):
    """
    Run comparative analysis across multiple samples.

    Args:
        job_id: AnalysisJob UUID

    Returns:
        Result data dictionary
    """
    try:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_started()

        # Get parameters
        sample_ids = job.sample_ids
        params = job.parameters

        if len(sample_ids) < 2:
            raise ValueError("Comparative analysis requires at least 2 samples")

        # Load data files
        file_paths = {}
        for sample_id in sample_ids:
            file_location = AnalysisFileLocation.objects.filter(
                sample_id=sample_id,
                file_type='TSV',
                is_active=True
            ).first()

            if file_location:
                file_paths[sample_id] = file_location.file_location

        if len(file_paths) < 2:
            raise ValueError(f"Need at least 2 data files, found {len(file_paths)}")

        # Perform comparative analysis
        analyzer = MultiSampleAnalyzer(file_paths)

        # Find shared variants
        shared_variants = analyzer.find_shared_variants(min_samples=params.get('min_shared_samples', 2))

        # Find unique variants for each sample
        unique_variants = {}
        for sample_id in sample_ids:
            unique_df = analyzer.find_unique_variants(sample_id)
            unique_variants[sample_id] = len(unique_df)

        result_data = {
            'sample_ids': sample_ids,
            'shared_variants_count': len(shared_variants),
            'unique_variants_per_sample': unique_variants,
            'comparative_stats': analyzer.get_comparative_statistics(),
        }

        # Generate report if requested
        report_format = params.get('report_format', None)
        if report_format and report_format in ['csv', 'xlsx']:
            report_gen = ReportGenerator()
            output_dir = Path(settings.MEDIA_ROOT) / 'ai_agent_reports' / str(job.session.user.id)
            output_dir.mkdir(parents=True, exist_ok=True)

            report_filename = f"comparative_{'_'.join(sample_ids[:3])}_{job.job_id}.{report_format}"
            report_path = output_dir / report_filename

            if report_format == 'csv':
                shared_variants.to_csv(report_path, index=False)
            elif report_format == 'xlsx':
                shared_variants.to_excel(report_path, index=False, engine='openpyxl')

            job.mark_completed(
                result_data=result_data,
                result_file_path=str(report_path),
                result_file_type=report_format
            )
        else:
            job.mark_completed(result_data=result_data)

        return result_data

    except Exception as e:
        job = AnalysisJob.objects.get(job_id=job_id)
        job.mark_failed(str(e))
        raise
