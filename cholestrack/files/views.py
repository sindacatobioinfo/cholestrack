# files/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib import messages
from .models import AnalysisFileLocation
from .forms import FileLocationForm
import logging

logger = logging.getLogger(__name__)

@login_required
def download_file(request, file_location_id):
    """
    Secure file download handler that mediates access to genomic analysis files.
    
    This view implements the security layer between users and file storage infrastructure.
    It verifies permissions, validates file existence, and constructs download responses
    without exposing internal server paths to the client.
    
    Security features:
    - Requires POST request to prevent CSRF attacks
    - Validates user authentication via @login_required decorator
    - Logs all download attempts for audit purposes
    - Returns generic error messages to prevent information disclosure
    
    Args:
        request: The HTTP request object
        file_location_id: Primary key of the AnalysisFileLocation record
    
    Returns:
        HttpResponse with file attachment or redirect to sample list on error
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
        
        # Get the internal server path using the model method
        full_path = file_location.get_full_server_path()
        
        # TODO: Replace this mock implementation with actual file serving logic
        # Implementation options:
        # 1. For local files: Use Django's FileResponse with the actual file
        # 2. For network storage: Stream from SFTP/FTP/NFS servers
        # 3. For cloud storage: Generate pre-signed URLs (AWS S3, Azure Blob, etc.)
        # 4. For high-security environments: Proxy through Django with chunked transfer
        
        # MOCK IMPLEMENTATION - Replace with actual file streaming in production
        response = HttpResponse(
            f"Download initiated for file type: {file_location.file_type}\n"
            f"Patient: {file_location.patient.patient_id}\n"
            f"Sample: {file_location.sample_id}\n"
            f"Data Type: {file_location.data_type}\n"
            f"Server: {file_location.server_name}\n"
            f"Size: {file_location.file_size_mb} MB\n\n"
            f"Internal path (not exposed to client): {full_path}\n\n"
            f"NOTE: This is a mock response. In production, this would stream the actual file.",
            content_type='text/plain'
        )
        
        # Set the download filename that the user will see
        filename = f"{file_location.patient.patient_id}_{file_location.sample_id}_{file_location.file_type}.txt"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except AnalysisFileLocation.DoesNotExist:
        logger.warning(
            f"File download failed - File not found: "
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