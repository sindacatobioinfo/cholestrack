# files/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, FileResponse
from django.contrib import messages
from django.conf import settings
from users.decorators import role_required
from .models import AnalysisFileLocation
from .forms import FileLocationForm
import logging
import os
import zipfile
import io
from pathlib import Path

logger = logging.getLogger(__name__)

@login_required
def download_single_file(request, file_location_id, file_part='main'):
    """
    Download a single file component (main file or paired file) separately.

    Supports:
    - BAM files: 'main' downloads .bam, 'pair' downloads .bai
    - VCF files: 'main' downloads .vcf/.vcf.gz, 'pair' downloads .tbi
    - FASTQ files: 'main' downloads _1.fastq.gz, 'pair' downloads _2.fastq.gz

    Args:
        request: HTTP request object
        file_location_id: Primary key of AnalysisFileLocation
        file_part: 'main' for primary file, 'pair' for paired file

    Returns:
        FileResponse with individual file or redirect on error
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid download request method.')
        return redirect('samples:sample_list')

    try:
        file_location = AnalysisFileLocation.objects.select_related('patient').get(
            id=file_location_id,
            is_active=True
        )

        logger.info(
            f"Single file download initiated: User={request.user.username}, "
            f"Patient={file_location.patient.patient_id}, "
            f"FileType={file_location.file_type}, Part={file_part}"
        )

        # Construct file path
        remote_files_root = getattr(settings, 'REMOTE_FILES_ROOT', settings.MEDIA_ROOT / 'remote_files')
        file_path_relative = file_location.file_path
        full_file_path = Path(remote_files_root) / file_path_relative

        # Security: Path validation
        try:
            full_file_path = full_file_path.resolve()
            remote_files_root_resolved = Path(remote_files_root).resolve()

            if not str(full_file_path).startswith(str(remote_files_root_resolved)):
                logger.error(f"Security violation - Path traversal: User={request.user.username}")
                messages.error(request, 'Invalid file path.')
                return redirect('samples:sample_list')
        except (ValueError, OSError) as e:
            logger.error(f"Path resolution error: {str(e)}")
            messages.error(request, 'Invalid file path.')
            return redirect('samples:sample_list')

        # Determine target file based on type and part
        file_type_upper = file_location.file_type.upper()

        if file_part == 'pair':
            if file_type_upper == 'VCF':
                target_path = Path(str(full_file_path) + '.tbi')
            elif file_type_upper == 'BAM':
                target_path = Path(str(full_file_path).replace('.bam', '.bai'))
            elif file_type_upper == 'FASTQ':
                if '_1.fastq.gz' in str(full_file_path):
                    target_path = Path(str(full_file_path).replace('_1.fastq.gz', '_2.fastq.gz'))
                else:
                    messages.error(request, 'Paired FASTQ file not found.')
                    return redirect('samples:sample_list')
            else:
                messages.error(request, f'Paired file not applicable for {file_type_upper}.')
                return redirect('samples:sample_list')
        else:
            target_path = full_file_path

        # Check file exists
        if not target_path.exists() or not target_path.is_file():
            logger.warning(f"File not found: {target_path}")
            messages.error(request, 'The requested file could not be found on the server.')
            return redirect('samples:sample_list')

        # Determine content type
        content_type_map = {
            '.bai': 'application/octet-stream',
            '.tbi': 'application/octet-stream',
            '.vcf': 'text/plain',
            '.vcf.gz': 'application/gzip',
            '.bam': 'application/octet-stream',
            '.fastq.gz': 'application/gzip',
        }

        file_ext = ''.join(target_path.suffixes)
        content_type = content_type_map.get(file_ext.lower(), 'application/octet-stream')

        # Stream file
        file_handle = open(target_path, 'rb')
        response = FileResponse(file_handle, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{target_path.name}"'
        response['Content-Length'] = target_path.stat().st_size

        logger.info(f"File download successful: {target_path.name}, Size={target_path.stat().st_size}")
        return response

    except AnalysisFileLocation.DoesNotExist:
        logger.warning(f"File location not found: ID={file_location_id}")
        messages.error(request, 'File not found.')
        return redirect('samples:sample_list')
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        messages.error(request, 'Download error occurred.')
        return redirect('samples:sample_list')


@login_required
def download_file(request, file_location_id):
    """
    Secure file download handler that serves genomic analysis files from mounted network storage.

    This view implements the security layer between users and file storage infrastructure.
    It verifies permissions, validates file existence, and streams files from the mounted
    remote directory without exposing internal server paths to the client.

    Special handling:
    - VCF files: Downloads as ZIP containing the VCF file + .tbi index file
    - BAM files: Downloads as ZIP containing the BAM file + .bai index file
    - Other files: Downloads with original filename

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

        # Use original filename only
        original_filename = full_file_path.name

        # Check if this is a VCF or BAM file that needs index file included
        file_type_upper = file_location.file_type.upper()
        needs_index = file_type_upper in ['VCF', 'BAM']

        if needs_index:
            # For VCF and BAM files, create a ZIP with the main file and index
            try:
                # Determine index file path
                if file_type_upper == 'VCF':
                    # VCF index: same name + .tbi extension
                    index_file_path = Path(str(full_file_path) + '.tbi')
                    index_filename = original_filename + '.tbi'
                elif file_type_upper == 'BAM':
                    # BAM index: replace .bam with .bai
                    index_file_path = Path(str(full_file_path).replace('.bam', '.bai'))
                    index_filename = original_filename.replace('.bam', '.bai')

                # Create ZIP file in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Add main file to ZIP
                    zip_file.write(full_file_path, arcname=original_filename)

                    # Add index file if it exists
                    if index_file_path.exists() and index_file_path.is_file():
                        zip_file.write(index_file_path, arcname=index_filename)
                        logger.info(
                            f"Including index file in download: {index_filename}"
                        )
                    else:
                        logger.warning(
                            f"Index file not found, downloading main file only: "
                            f"Expected path={index_file_path}"
                        )

                # Prepare ZIP for download
                zip_buffer.seek(0)

                # Create ZIP filename (replace extension with .zip)
                base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
                zip_filename = f"{base_name}.zip"

                response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                response['Content-Length'] = len(zip_buffer.getvalue())

                logger.info(
                    f"File download successful (with index): User={request.user.username}, "
                    f"Patient={file_location.patient.patient_id}, "
                    f"FileType={file_location.file_type}, "
                    f"ZipSize={len(zip_buffer.getvalue())} bytes"
                )

                return response

            except Exception as e:
                logger.error(
                    f"Error creating ZIP with index file: {str(e)}, "
                    f"falling back to single file download"
                )
                # Fall through to regular download if ZIP creation fails
                needs_index = False

        # Regular download for non-VCF/BAM files or if ZIP creation failed
        if not needs_index:
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
                response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
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
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def file_upload(request):
    """
    View for registering new analysis file locations in the system.
    This doesn't handle actual file uploads - files are managed separately on servers.
    This view only registers file metadata and locations.

    Permissions: ADMIN, DATA_MANAGER, RESEARCHER only
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
@role_required(['ADMIN', 'DATA_MANAGER', 'RESEARCHER'])
def file_edit(request, file_location_id):
    """
    View for editing file location metadata.
    Allows updating file information without changing the actual file.

    Permissions: ADMIN, DATA_MANAGER, RESEARCHER only
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
@role_required(['ADMIN', 'DATA_MANAGER'])
def file_delete(request, file_location_id):
    """
    View for soft-deleting a file location record.
    Sets is_active=False instead of permanently deleting.

    Permissions: ADMIN, DATA_MANAGER only (delete operation)
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