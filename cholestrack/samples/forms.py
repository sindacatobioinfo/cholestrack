# samples/forms.py
from django import forms
from .models import Patient
from django.contrib.auth.models import User
import json


class PatientForm(forms.ModelForm):
    """
    Form for creating and editing patient records.
    Includes custom handling for JSON clinical information.
    """
    # Additional fields for JSON clinical data (common fields)
    diagnosis = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter primary diagnosis or clinical presentation'
        }),
        label='Diagnosis',
        help_text='Primary clinical diagnosis or symptoms'
    )

    phenotype = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Describe phenotype characteristics'
        }),
        label='Phenotype',
        help_text='Observable characteristics and traits'
    )

    additional_clinical_info = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Any additional clinical information, lab results, family history, etc.'
        }),
        label='Additional Clinical Information',
        help_text='Other relevant clinical details'
    )

    class Meta:
        model = Patient
        fields = [
            'patient_id',
            'name',
            'birth_date',
            'main_exome_result',
            'analysis_status',
            'responsible_user',
            'notes'
        ]
        widgets = {
            'patient_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PAT-2025-001'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter patient full name or anonymized ID'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'main_exome_result': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Awaiting Analysis, Positive, Negative'
            }),
            'analysis_status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'responsible_user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Research notes or additional observations'
            }),
        }
        labels = {
            'patient_id': 'Patient ID',
            'name': 'Full Name',
            'birth_date': 'Date of Birth',
            'main_exome_result': 'Main Exome Result',
            'analysis_status': 'Analysis Status',
            'responsible_user': 'Responsible Researcher',
            'notes': 'Research Notes',
        }
        help_texts = {
            'patient_id': 'Unique identifier for the patient',
            'name': 'Use anonymized ID if required by ethics protocols',
            'birth_date': 'Patient date of birth',
            'main_exome_result': 'Summary of main genomic finding or current status',
            'analysis_status': 'Current status of the genomic analysis pipeline',
            'responsible_user': 'The researcher or clinician managing this case',
            'notes': 'Additional notes about the patient or case',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing an existing patient, populate clinical JSON fields
        if self.instance and self.instance.pk and self.instance.clinical_info_json:
            clinical_data = self.instance.clinical_info_json
            if isinstance(clinical_data, dict):
                self.fields['diagnosis'].initial = clinical_data.get('diagnostico', '')
                self.fields['phenotype'].initial = clinical_data.get('fenótipo', '')
                self.fields['additional_clinical_info'].initial = clinical_data.get('info_adicional', '')

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Build clinical_info_json from form fields
        clinical_info = {}

        if self.cleaned_data.get('diagnosis'):
            clinical_info['diagnostico'] = self.cleaned_data['diagnosis']

        if self.cleaned_data.get('phenotype'):
            clinical_info['fenótipo'] = self.cleaned_data['phenotype']

        if self.cleaned_data.get('additional_clinical_info'):
            clinical_info['info_adicional'] = self.cleaned_data['additional_clinical_info']

        instance.clinical_info_json = clinical_info

        if commit:
            instance.save()

        return instance
