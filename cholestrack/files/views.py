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
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# User that owns FASTQ files and has exclusive read access
FASTQ_FILE_OWNER = 'burlo'


def read_file_as_owner(file_path, file_owner=FASTQ_FILE_OWNER):
    """
    Read a file that requires specific user permissions using sudo.

    This function is necessary for FASTQ files that are owned by a specific user
    (burlo) and not readable by the Django application user. It uses sudo to
    read the file as the owner and returns the content.

    Security notes:
    - Requires sudoers configuration to allow Django user to read specific files
    - Path is validated before use to prevent command injection
    - Only used for files in allowed directories (remote_files)

    Args:
        file_path: Path object or string of the file to read
        file_owner: Username that owns the file (default: burlo)

    Returns:
        bytes: File content

    Raises:
        PermissionError: If sudo access is not configured or file is not readable
        subprocess.CalledProcessError: If sudo command fails
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    # Validate that path doesn't contain shell metacharacters
    path_str = str(file_path)
    if any(char in path_str for char in ['&', '|', ';', '`', '$', '(', ')', '<', '>', '\n', '\r']):
        raise ValueError(f"Invalid characters in file path: {path_str}")

    try:
        # Use sudo -u to read file as the owner
        # -n flag ensures no password prompt (requires sudoers configuration)
        result = subprocess.run(
            ['sudo', '-n', '-u', file_owner, 'cat', path_str],
            capture_output=True,
            check=True,
            timeout=300  # 5 minute timeout for large files
        )

        logger.info(f"Successfully read file as {file_owner}: {file_path.name}")
        return result.stdout

    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and b'Permission denied' in e.stderr:
            raise PermissionError(f"Cannot read file as {file_owner}: {file_path}")
        elif b'sudo' in e.stderr and b'password' in e.stderr:
            raise PermissionError(
                f"Sudo is not configured to allow reading files as {file_owner}. "
                "Please configure /etc/sudoers.d/cholestrack"
            )
        else:
            logger.error(f"Error reading file as {file_owner}: {e.stderr.decode()}")
            raise
    except subprocess.TimeoutExpired:
        raise IOError(f"Timeout while reading file: {file_path}")
    except Exception as e:
        logger.error(f"Unexpected error reading file as {file_owner}: {str(e)}")
        raise


def copy_file_as_owner(file_path, file_owner=FASTQ_FILE_OWNER):
    """
    Copy a file to a temporary location using sudo, preserving permissions for reading.

    This is an alternative to read_file_as_owner for very large files where
    reading into memory is not practical. Creates a temporary copy that the
    Django user can read.

    Args:
        file_path: Path object or string of the file to copy
        file_owner: Username that owns the file (default: burlo)

    Returns:
        str: Path to temporary file (caller must delete when done)

    Raises:
        PermissionError: If sudo access is not configured
        subprocess.CalledProcessError: If copy fails
    """
    file_path = Path(file_path)

    # Validate path
    path_str = str(file_path)
    if any(char in path_str for char in ['&', '|', ';', '`', '$', '(', ')', '<', '>', '\n', '\r']):
        raise ValueError(f"Invalid characters in file path: {path_str}")

    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=file_path.suffix, prefix='fastq_download_')
    os.close(temp_fd)

    try:
        # Copy file as owner, then change permissions so Django user can read
        subprocess.run(
            ['sudo', '-n', '-u', file_owner, 'cp', path_str, temp_path],
            capture_output=True,
            check=True,
            timeout=300
        )

        # Make temp file readable by current user
        subprocess.run(
            ['sudo', '-n', 'chmod', '644', temp_path],
            capture_output=True,
            check=True,
            timeout=10
        )

        logger.info(f"Created temporary copy of {file_path.name} at {temp_path}")
        return temp_path

    except subprocess.CalledProcessError as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass

        if b'sudo' in e.stderr and b'password' in e.stderr:
            raise PermissionError(
                f"Sudo is not configured. Please configure /etc/sudoers.d/cholestrack"
            )
        logger.error(f"Error copying file as {file_owner}: {e.stderr.decode()}")
        raise
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise

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

        # Check if this is a FASTQ file that requires sudo access
        is_fastq = file_type_upper == 'FASTQ'

        # Stream file
        try:
            if is_fastq and not os.access(target_path, os.R_OK):
                # FASTQ files owned by burlo - use sudo to read
                logger.info(
                    f"Using sudo to read FASTQ file as {FASTQ_FILE_OWNER}: "
                    f"{target_path.name}"
                )
                try:
                    file_content = read_file_as_owner(target_path)
                    response = HttpResponse(file_content, content_type=content_type)
                    response['Content-Disposition'] = f'attachment; filename="{target_path.name}"'
                    response['Content-Length'] = len(file_content)
                    logger.info(
                        f"File download successful (via sudo): {target_path.name}, "
                        f"Size={len(file_content)}"
                    )
                    return response
                except PermissionError as e:
                    logger.error(
                        f"Permission error with sudo: {str(e)}, "
                        f"Path={target_path}, User={request.user.username}"
                    )
                    messages.error(
                        request,
                        'Unable to access FASTQ file. Sudo configuration may be missing. '
                        'Please contact the system administrator.'
                    )
                    return redirect('samples:sample_list')
            else:
                # Regular file access (non-FASTQ or readable FASTQ)
                file_handle = open(target_path, 'rb')
                response = FileResponse(file_handle, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{target_path.name}"'
                response['Content-Length'] = target_path.stat().st_size

            logger.info(f"File download successful: {target_path.name}, Size={target_path.stat().st_size}")
            return response
        except PermissionError as e:
            logger.error(
                f"Permission denied when opening file: Path={target_path}, "
                f"User={request.user.username}, Error={str(e)}"
            )
            messages.error(
                request,
                'Permission denied when accessing the file. '
                'Please contact the system administrator to check file permissions.'
            )
            return redirect('samples:sample_list')
        except IOError as e:
            logger.error(
                f"IO error when opening file: Path={target_path}, "
                f"User={request.user.username}, Error={str(e)}"
            )
            messages.error(request, 'Error reading the file from storage.')
            return redirect('samples:sample_list')

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
        is_fastq = file_type_upper == 'FASTQ'

        # Check file is readable (skip for FASTQ - will use sudo if needed)
        if not is_fastq and not os.access(full_file_path, os.R_OK):
            logger.error(
                f"File exists but is not readable - Permission denied: "
                f"Path={full_file_path}, User={request.user.username}"
            )
            messages.error(
                request,
                'The file exists but cannot be read due to permission restrictions. '
                'Please contact the system administrator.'
            )
            return redirect('samples:sample_list')

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

                # Check if index file is readable
                index_readable = False
                if index_file_path.exists() and index_file_path.is_file():
                    index_readable = os.access(index_file_path, os.R_OK)
                    if not index_readable:
                        logger.warning(
                            f"Index file exists but is not readable: {index_file_path}"
                        )

                # Create ZIP file in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Add main file to ZIP
                    try:
                        zip_file.write(full_file_path, arcname=original_filename)
                    except PermissionError as e:
                        logger.error(
                            f"Permission denied when adding file to ZIP: "
                            f"Path={full_file_path}, Error={str(e)}"
                        )
                        raise  # Re-raise to be caught by outer exception handler

                    # Add index file if it exists and is readable
                    if index_readable:
                        try:
                            zip_file.write(index_file_path, arcname=index_filename)
                            logger.info(
                                f"Including index file in download: {index_filename}"
                            )
                        except PermissionError as e:
                            logger.warning(
                                f"Permission denied when adding index file to ZIP: "
                                f"Path={index_file_path}, Error={str(e)}"
                            )
                            # Continue without index file
                    elif index_file_path.exists():
                        logger.warning(
                            f"Index file exists but is not readable: {index_file_path}"
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

            except PermissionError as e:
                logger.error(
                    f"Permission denied when creating ZIP: {str(e)}, "
                    f"Path={full_file_path}, User={request.user.username}"
                )
                messages.error(
                    request,
                    'Permission denied when accessing the file. '
                    'Please contact the system administrator to check file permissions.'
                )
                return redirect('samples:sample_list')
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
                if is_fastq and not os.access(full_file_path, os.R_OK):
                    # FASTQ files owned by burlo - use sudo to read
                    logger.info(
                        f"Using sudo to read FASTQ file as {FASTQ_FILE_OWNER}: "
                        f"{full_file_path.name}, Patient={file_location.patient.patient_id}"
                    )
                    try:
                        file_content = read_file_as_owner(full_file_path)
                        response = HttpResponse(file_content, content_type=content_type)
                        response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
                        response['Content-Length'] = len(file_content)

                        logger.info(
                            f"File download successful (via sudo): User={request.user.username}, "
                            f"Patient={file_location.patient.patient_id}, "
                            f"FileType={file_location.file_type}, "
                            f"Size={len(file_content)} bytes"
                        )
                        return response
                    except PermissionError as e:
                        logger.error(
                            f"Permission error with sudo: {str(e)}, "
                            f"Path={full_file_path}, User={request.user.username}"
                        )
                        messages.error(
                            request,
                            'Unable to access FASTQ file. Sudo configuration may be missing. '
                            'Please contact the system administrator.'
                        )
                        return redirect('samples:sample_list')
                else:
                    # Regular file access (non-FASTQ or readable FASTQ)
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

            except PermissionError as e:
                logger.error(
                    f"Permission denied when opening file: Path={full_file_path}, "
                    f"User={request.user.username}, Error={str(e)}"
                )
                messages.error(
                    request,
                    'Permission denied when accessing the file. '
                    'Please contact the system administrator to check file permissions.'
                )
                return redirect('samples:sample_list')
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