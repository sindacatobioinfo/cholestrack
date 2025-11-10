# samples/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Patient
from .forms import PatientForm
from files.models import AnalysisFileLocation
import json

@login_required
@never_cache
def sample_list(request):
    """
    Display all patient samples and their associated genomic analysis files.
    This view serves as the main dashboard for sample data management,
    presenting a comprehensive table of patients and available analysis files.
    Includes pagination (10 rows per page).
    """
    all_patients = Patient.objects.all().prefetch_related('file_locations')
    patient_data = []

    for patient in all_patients:
        available_files = {}
        file_metadata = {
            'project': 'N/D',
            'batch': 'N/D',
            'sample_id': 'N/D',
            'data_type': 'N/D'
        }

        # Get only active file locations
        locations = list(patient.file_locations.filter(is_active=True))

        if locations:
            first_location = locations[0]
            file_metadata['project'] = getattr(first_location, 'project_name', 'N/D')
            file_metadata['batch'] = getattr(first_location, 'batch_id', 'N/D')
            file_metadata['sample_id'] = getattr(first_location, 'sample_id', 'N/D')
            file_metadata['data_type'] = getattr(first_location, 'data_type', 'N/D').upper()

            for location in locations:
                available_files[location.file_type] = {
                    'id': location.id,
                    'server': location.server_name
                }

        # Safely handle clinical_info_json which might be a dict, string, or None
        clinical_info = patient.clinical_info_json
        if isinstance(clinical_info, str):
            try:
                clinical_info = json.loads(clinical_info)
            except (json.JSONDecodeError, TypeError):
                clinical_info = {}
        elif not clinical_info:
            clinical_info = {}

        patient_data.append({
            'patient_id': patient.patient_id,
            'name': patient.name,
            'main_result': getattr(patient, 'main_exome_result', 'N/D'),
            'analysis_status': patient.get_analysis_status_display(),
            'analysis_status_raw': patient.analysis_status,
            'clinical_preview': patient.clinical_info_json.get('diagnostico', 'N/D') if patient.clinical_info_json else 'N/D',
            'files': available_files,
            'project': file_metadata['project'],
            'batch': file_metadata['batch'],
            'sample_id': file_metadata['sample_id'],
            'data_type': file_metadata['data_type'],
        })

    # Pagination: 10 rows per page
    paginator = Paginator(patient_data, 10)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'patient_list': page_obj.object_list,
        'user_name': request.user.username,
        'total_count': paginator.count,
    }

    return render(request, 'samples/sample_list.html', context)


@login_required
def sample_detail(request, patient_id):
    """
    Display detailed information for a specific patient sample.
    This view presents comprehensive clinical information and complete analysis file history.
    """
    try:
        patient = Patient.objects.get(patient_id=patient_id)
        file_locations = patient.file_locations.filter(is_active=True).order_by('-created_at')
        
        context = {
            'patient': patient,
            'file_locations': file_locations,
        }
        
        return render(request, 'samples/sample_detail.html', context)
        
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('samples:sample_list')


@login_required
def patient_create(request):
    """
    View for creating a new patient record.
    Handles both patient information and clinical data entry.
    """
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.patient_id} has been created successfully.')
            return redirect('samples:sample_detail', patient_id=patient.patient_id)
    else:
        form = PatientForm()

    context = {
        'form': form,
        'title': 'Create New Patient Record'
    }
    return render(request, 'samples/patient_create.html', context)


@login_required
def patient_edit(request, patient_id):
    """
    View for editing an existing patient record.
    Updates patient information and clinical data.
    """
    try:
        patient = Patient.objects.get(patient_id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('samples:sample_list')

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.patient_id} has been updated successfully.')
            return redirect('samples:sample_detail', patient_id=patient.patient_id)
    else:
        form = PatientForm(instance=patient)

    context = {
        'form': form,
        'patient': patient,
        'title': 'Edit Patient Record'
    }
    return render(request, 'samples/patient_edit.html', context)


@login_required
def patient_delete(request, patient_id):
    """
    View for deleting a patient record.
    Requires confirmation before deletion.
    """
    try:
        patient = Patient.objects.get(patient_id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('samples:sample_list')

    if request.method == 'POST':
        patient_id_display = patient.patient_id
        patient.delete()
        messages.success(request, f'Patient {patient_id_display} has been deleted successfully.')
        return redirect('samples:sample_list')

    # Count associated files
    file_count = patient.file_locations.filter(is_active=True).count()

    context = {
        'patient': patient,
        'file_count': file_count,
    }
    return render(request, 'samples/patient_delete_confirm.html', context)