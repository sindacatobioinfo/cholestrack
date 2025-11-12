# region_selection/views.py
"""
Views for region extraction functionality.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.utils import timezone
from users.decorators import role_confirmed_required
from files.models import AnalysisFileLocation
from .models import RegionExtractionJob
from .forms import RegionExtractionForm
from .utils import (
    get_gene_coordinates,
    extract_bam_region,
    create_bam_index,
    get_temp_directory,
    cleanup_job_files
)


@login_required
@role_confirmed_required
def create_extraction(request):
    """
    View for creating a new region extraction job.
    """
    if request.method == 'POST':
        form = RegionExtractionForm(request.POST)
        if form.is_valid():
            sample_id = form.cleaned_data['sample_id']
            region_method = form.cleaned_data['region_method']

            # Get the BAM file for this sample
            try:
                bam_file = AnalysisFileLocation.objects.get(
                    sample_id=sample_id,
                    file_type='BAM',
                    is_active=True
                )
            except AnalysisFileLocation.DoesNotExist:
                messages.error(request, f'BAM file not found for sample: {sample_id}')
                return render(request, 'region_selection/create_extraction.html', {'form': form})

            # Create the extraction job
            job = RegionExtractionJob.objects.create(
                user=request.user,
                sample_id=sample_id,
                original_bam_file=bam_file,
                gene_name=form.cleaned_data.get('gene_name'),
                chromosome=form.cleaned_data.get('chromosome'),
                start_position=form.cleaned_data.get('start_position'),
                end_position=form.cleaned_data.get('end_position'),
                status='PENDING'
            )

            # If gene name provided, convert to coordinates
            if region_method == 'gene' and job.gene_name:
                try:
                    coordinates = get_gene_coordinates(job.gene_name)
                    if coordinates:
                        job.chromosome = coordinates['chromosome']
                        job.start_position = coordinates['start']
                        job.end_position = coordinates['end']
                        job.save()
                    else:
                        job.status = 'FAILED'
                        job.error_message = f'Gene "{job.gene_name}" not found in reference database.'
                        job.save()
                        messages.error(
                            request,
                            f'Gene "{job.gene_name}" not found. Please check the gene name and try again.'
                        )
                        return redirect('region_selection:job_detail', job_id=job.job_id)
                except Exception as e:
                    job.status = 'FAILED'
                    job.error_message = str(e)
                    job.save()
                    messages.error(request, f'Error converting gene name to coordinates: {e}')
                    return redirect('region_selection:job_detail', job_id=job.job_id)

            # Start processing the extraction
            messages.success(
                request,
                f'Extraction job created successfully! Processing region extraction for sample {sample_id}.'
            )
            return redirect('region_selection:process_extraction', job_id=job.job_id)

    else:
        form = RegionExtractionForm()

    context = {
        'form': form,
        'title': 'Extract BAM Region'
    }
    return render(request, 'region_selection/create_extraction.html', context)


@login_required
@role_confirmed_required
def process_extraction(request, job_id):
    """
    Process the BAM extraction job.
    This view initiates the samtools extraction process.
    """
    job = get_object_or_404(RegionExtractionJob, job_id=job_id, user=request.user)

    if job.status not in ['PENDING', 'PROCESSING']:
        # Job already processed
        return redirect('region_selection:job_detail', job_id=job.job_id)

    # Update status to processing
    job.status = 'PROCESSING'
    job.processing_started_at = timezone.now()
    job.save()

    try:
        # Extract the region using samtools
        output_path = extract_bam_region(job)

        # Create index for the output BAM file
        create_bam_index(output_path)

        # Calculate file size
        file_size_bytes = os.path.getsize(output_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Update job with success
        job.status = 'COMPLETED'
        job.completed_at = timezone.now()
        job.output_file_path = output_path
        job.output_file_size_mb = round(file_size_mb, 2)
        job.set_expiration(minutes=10)  # Set 10-minute expiration
        job.save()

        messages.success(
            request,
            f'Region extraction completed successfully! File size: {job.output_file_size_mb} MB. '
            'The file will be available for download for 10 minutes.'
        )

    except Exception as e:
        job.status = 'FAILED'
        job.error_message = str(e)
        job.save()
        messages.error(request, f'Error during extraction: {e}')

    return redirect('region_selection:job_detail', job_id=job.job_id)


@login_required
@role_confirmed_required
def job_detail(request, job_id):
    """
    Display details of an extraction job.
    """
    job = get_object_or_404(RegionExtractionJob, job_id=job_id, user=request.user)

    # Check if job has expired
    if job.is_expired() and job.status == 'COMPLETED':
        job.status = 'EXPIRED'
        job.save()
        # Cleanup files if they exist
        if job.output_file_path and os.path.exists(job.output_file_path):
            cleanup_job_files(job)

    context = {
        'job': job,
        'title': f'Extraction Job Details - {job.job_id}'
    }
    return render(request, 'region_selection/job_detail.html', context)


@login_required
@role_confirmed_required
def download_extracted_file(request, job_id):
    """
    Download the extracted BAM file.
    After download, cleanup the temporary files.
    """
    job = get_object_or_404(RegionExtractionJob, job_id=job_id, user=request.user)

    # Verify job is completed
    if job.status != 'COMPLETED':
        messages.error(request, 'This extraction job is not completed or has expired.')
        return redirect('region_selection:job_detail', job_id=job.job_id)

    # Verify file exists
    if not job.output_file_path or not os.path.exists(job.output_file_path):
        job.status = 'FAILED'
        job.error_message = 'Output file not found.'
        job.save()
        messages.error(request, 'Output file not found.')
        return redirect('region_selection:job_detail', job_id=job.job_id)

    # Check if expired
    if job.is_expired():
        job.status = 'EXPIRED'
        job.save()
        cleanup_job_files(job)
        messages.error(request, 'This file has expired and is no longer available for download.')
        return redirect('region_selection:job_detail', job_id=job.job_id)

    try:
        # Prepare filename for download
        if job.gene_name:
            filename = f"{job.sample_id}_{job.gene_name}_extracted.bam"
        else:
            region_str = f"{job.chromosome}_{job.start_position}_{job.end_position}"
            filename = f"{job.sample_id}_{region_str}_extracted.bam"

        # Verify file exists and is readable
        if not os.path.isfile(job.output_file_path):
            raise FileNotFoundError(f"Output file is not a valid file: {job.output_file_path}")

        # Get file size
        file_size = os.path.getsize(job.output_file_path)

        # Open the file for download
        file_handle = open(job.output_file_path, 'rb')
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
            content_type='application/octet-stream'
        )
        response['Content-Length'] = file_size

        # Mark job as downloaded
        job.mark_downloaded()

        return response

    except Exception as e:
        messages.error(request, f'Error downloading file: {e}')
        return redirect('region_selection:job_detail', job_id=job.job_id)


@login_required
@role_confirmed_required
def job_list(request):
    """
    List all extraction jobs for the current user.
    """
    jobs = RegionExtractionJob.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'jobs': jobs,
        'title': 'My Region Extraction Jobs'
    }
    return render(request, 'region_selection/job_list.html', context)


@login_required
@role_confirmed_required
def job_status_api(request, job_id):
    """
    API endpoint to check job status (for AJAX polling).
    """
    try:
        job = RegionExtractionJob.objects.get(job_id=job_id, user=request.user)

        data = {
            'status': job.status,
            'error_message': job.error_message,
            'output_file_size_mb': str(job.output_file_size_mb) if job.output_file_size_mb else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'expires_at': job.expires_at.isoformat() if job.expires_at else None,
            'is_expired': job.is_expired() if job.expires_at else False
        }

        return JsonResponse(data)

    except RegionExtractionJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
