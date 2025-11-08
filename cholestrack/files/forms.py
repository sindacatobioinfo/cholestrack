# files/forms.py
from django import forms
from .models import AnalysisFileLocation
from samples.models import Patient


class FileLocationForm(forms.ModelForm):
    """
    Form for registering new analysis file locations in the system.
    This form handles metadata entry without actual file upload (files remain on servers).
    """
    class Meta:
        model = AnalysisFileLocation
        fields = [
            'patient',
            'project_name',
            'batch_id',
            'sample_id',
            'data_type',
            'file_type',
            'server_name',
            'file_path',
            'file_size_mb',
            'checksum',
            'uploaded_by',
        ]
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CHOLESTASIS2025'
            }),
            'batch_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BATCH-001'
            }),
            'sample_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SAMPLE-001'
            }),
            'data_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'server_name': forms.Select(attrs={
                'class': 'form-control'
            }),
            'file_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., /projects/cholestasis/samples/sample001.vcf'
            }),
            'file_size_mb': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'File size in megabytes',
                'step': '0.01'
            }),
            'checksum': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MD5 hash for file integrity verification'
            }),
            'uploaded_by': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'patient': 'Patient',
            'project_name': 'Project Name',
            'batch_id': 'Batch ID',
            'sample_id': 'Sample ID',
            'data_type': 'Data Type',
            'file_type': 'File Type',
            'server_name': 'Server Location',
            'file_path': 'File Path (on server)',
            'file_size_mb': 'File Size (MB)',
            'checksum': 'MD5 Checksum',
            'uploaded_by': 'Uploaded By',
        }
        help_texts = {
            'patient': 'Select the patient this file belongs to',
            'project_name': 'Research project or study identifier',
            'batch_id': 'Sequencing batch identifier',
            'sample_id': 'Laboratory sample identifier',
            'data_type': 'Type of genomic sequencing data',
            'file_type': 'File format type',
            'server_name': 'Physical server where file is stored',
            'file_path': 'Relative path to the file on the server (internal use only)',
            'file_size_mb': 'File size in megabytes for tracking storage usage',
            'checksum': 'MD5 hash for file integrity verification (optional)',
            'uploaded_by': 'User who registered this file',
        }

    def __init__(self, *args, **kwargs):
        # Get the current user from kwargs if provided
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Set uploaded_by to current user by default
        if self.current_user:
            self.fields['uploaded_by'].initial = self.current_user
