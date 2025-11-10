# files/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, FileResponse
from django.contrib import messages
from django.conf import settings
from .models import AnalysisFileLocation
from .forms import FileLocationForm
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@login_required
def download_file(request, file_location_id):
    """
    Secure file download handler that serves genomic analysis files from mounted network storage.

    This view implements the security layer between users and file storage infrastructure.
    It verifies permissions, validates file existence, and streams files from the mounted
    remote directory without exposing internal server paths to the client.

    Security features:
    - Requires POST request to prevent CSRF attacks
    - Validates user authentication via @login_required decorator
    - Logs all download attempts for audit purposes
    - Returns generic error messages to prevent information disclosure
    - Validates file path to prevent directory traversal attacks

    Args:
        request: The HTTP request object
        file_location_id: Primary key of the AnalysisFileLocation record

    Returns:
        FileResponse with file attachment or redirect to sample list on error
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid download request method.')
        return redirect('samples:sample_list')

    try:
        file_location = AnalysisFileLocation.objects.select_related('patient').get(
            id=file_location_id,
            is_active=True
        )

        # TODO: Implement granular permission checking
        # Current implementation assumes all authenticated users have access
        # Future enhancement should verify:
        # - User has permission to access this specific patient's data
        # - User's role permits downloading this file type
        # - File access has been approved by responsible researcher

        # Example permission check (implement as needed):
        # if not request.user.has_perm('files.download_file'):
        #     messages.error(request, 'You do not have permission to download files.')
        #     return redirect('samples:sample_list')

        # Log the download attempt for audit trail
        logger.info(
            f"File download initiated: User={request.user.username}, "
            f"Patient={file_location.patient.patient_id}, "
            f"FileType={file_location.file_type}, "
            f"Sample={file_location.sample_id}"
        )

        # Construct the full file path from mounted network storage
        # file_path in database doesn't start with "/", so we construct it directly
        remote_files_root = getattr(settings, 'REMOTE_FILES_ROOT', settings.MEDIA_ROOT / 'remote_files')
        file_path_relative = file_location.file_path  # Path from database (no leading /)

        # Construct full path: MEDIA_ROOT/remote_files/<file_path>
        full_file_path = Path(remote_files_root) / file_path_relative

        # Security: Resolve the path and ensure it's within the allowed directory
        # This prevents directory traversal attacks (e.g., ../../etc/passwd)
        try:
            full_file_path = full_file_path.resolve()
            remote_files_root_resolved = Path(remote_files_root).resolve()

            # Check if the resolved path is within the allowed directory
            if not str(full_file_path).startswith(str(remote_files_root_resolved)):
                logger.error(
                    f"Security violation - Path traversal attempt: "
                    f"User={request.user.username}, Path={file_path_relative}"
                )
                messages.error(request, 'Invalid file path.')
                return redirect('samples:sample_list')
        except (ValueError, OSError) as e:
            logger.error(f"Path resolution error: {str(e)}")
            messages.error(request, 'Invalid file path.')
            return redirect('samples:sample_list')

        # Check if file exists
        if not full_file_path.exists():
            logger.warning(
                f"File download failed - File not found on disk: "
                f"Path={full_file_path}, FileLocationID={file_location_id}, "
                f"User={request.user.username}"
            )
            messages.error(request, 'The requested file could not be found on the server.')
            return redirect('samples:sample_list')

        # Check if it's a file (not a directory)
        if not full_file_path.is_file():
            logger.error(
                f"File download failed - Path is not a file: "
                f"Path={full_file_path}, User={request.user.username}"
            )
            messages.error(request, 'Invalid file path.')
            return redirect('samples:sample_list')

        # Determine the download filename
        # Use the original filename from the path, or construct a descriptive name
        original_filename = full_file_path.name
        download_filename = f"{file_location.patient.patient_id}_{file_location.sample_id}_{file_location.file_type}_{original_filename}"

        # Determine content type based on file extension
        content_type_map = {
            '.vcf': 'text/plain',
            '.vcf.gz': 'application/gzip',
            '.bam': 'application/octet-stream',
            '.fastq': 'text/plain',
            '.fastq.gz': 'application/gzip',
            '.pdf': 'application/pdf',
            '.tsv': 'text/tab-separated-values',
            '.cram': 'application/octet-stream',
            '.txt': 'text/plain',
        }

        # Get file extension and determine content type
        file_ext = ''.join(full_file_path.suffixes)  # Handles .vcf.gz
        content_type = content_type_map.get(file_ext.lower(), 'application/octet-stream')

        # Open and stream the file
        try:
            file_handle = open(full_file_path, 'rb')
            response = FileResponse(file_handle, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
            response['Content-Length'] = full_file_path.stat().st_size

            logger.info(
                f"File download successful: User={request.user.username}, "
                f"Patient={file_location.patient.patient_id}, "
                f"FileType={file_location.file_type}, "
                f"Size={full_file_path.stat().st_size} bytes"
            )

            return response

        except IOError as e:
            logger.error(
                f"File read error: Path={full_file_path}, "
                f"User={request.user.username}, Error={str(e)}"
            )
            messages.error(request, 'Error reading the file from storage.')
            return redirect('samples:sample_list')

    except AnalysisFileLocation.DoesNotExist:
        logger.warning(
            f"File download failed - File record not found: "
            f"FileLocationID={file_location_id}, User={request.user.username}"
        )
        messages.error(request, 'The requested file could not be found or has been removed.')
        return redirect('samples:sample_list')

    except Exception as e:
        logger.error(
            f"File download error: FileLocationID={file_location_id}, "
            f"User={request.user.username}, Error={str(e)}"
        )
        messages.error(request, 'An error occurred while processing your download request.')
        return redirect('samples:sample_list')


@login_required
def file_info(request, file_location_id):
    """
    Display detailed information about a specific analysis file.
    This view provides metadata without initiating a download.
    """
    try:
        file_location = AnalysisFileLocation.objects.select_related('patient', 'uploaded_by').get(
            id=file_location_id,
            is_active=True
        )
        
        context = {
            'file_location': file_location,
        }
        
        return render(request, 'files/file_info.html', context)
        
    except AnalysisFileLocation.DoesNotExist:
        messages.error(request, 'File information not available.')
        return redirect('samples:sample_list')


@login_required
def file_upload(request):
    """
    View for registering new analysis file locations in the system.
    This doesn't handle actual file uploads - files are managed separately on servers.
    This view only registers file metadata and locations.
    """
    if request.method == 'POST':
        form = FileLocationForm(request.POST, current_user=request.user)
        if form.is_valid():
            file_location = form.save()
            messages.success(
                request,
                f'File location registered successfully for patient {file_location.patient.patient_id}'
            )
            return redirect('samples:sample_detail', patient_id=file_location.patient.patient_id)
    else:
        form = FileLocationForm(current_user=request.user)

    context = {
        'form': form,
        'title': 'Register Analysis File Location'
    }
    return render(request, 'files/file_upload.html', context)


@login_required
def file_edit(request, file_location_id):
    """
    View for editing file location metadata.
    Allows updating file information without changing the actual file.
    """
    try:
        file_location = AnalysisFileLocation.objects.select_related('patient').get(
            id=file_location_id,
            is_active=True
        )
    except AnalysisFileLocation.DoesNotExist:
        messages.error(request, 'File location not found.')
        return redirect('samples:sample_list')

    if request.method == 'POST':
        form = FileLocationForm(request.POST, instance=file_location, current_user=request.user)
        if form.is_valid():
            file_location = form.save()
            messages.success(request, 'File location metadata has been updated successfully.')
            return redirect('files:file_info', file_location_id=file_location.id)
    else:
        form = FileLocationForm(instance=file_location, current_user=request.user)

    context = {
        'form': form,
        'file_location': file_location,
        'title': 'Edit File Location Metadata'
    }
    return render(request, 'files/file_edit.html', context)


@login_required
def file_delete(request, file_location_id):
    """
    View for soft-deleting a file location record.
    Sets is_active=False instead of permanently deleting.
    """
    try:
        file_location = AnalysisFileLocation.objects.select_related('patient').get(
            id=file_location_id,
            is_active=True
        )
    except AnalysisFileLocation.DoesNotExist:
        messages.error(request, 'File location not found.')
        return redirect('samples:sample_list')

    if request.method == 'POST':
        # Soft delete - set is_active to False
        file_location.is_active = False
        file_location.save()
        messages.success(request, 'File location has been removed from the system.')
        return redirect('samples:sample_detail', patient_id=file_location.patient.patient_id)

    context = {
        'file_location': file_location,
    }
    return render(request, 'files/file_delete_confirm.html', context)