# analysis_workflows/forms.py
"""
Forms for workflow configuration.
"""

from django import forms
from .models import WorkflowConfiguration


class WorkflowConfigForm(forms.ModelForm):
    """
    Form for configuring workflow parameters.
    """
    class Meta:
        model = WorkflowConfiguration
        fields = [
            'name',
            'project_name',
            'aligner',
            'minimap2_preset',
            'use_gatk',
            'use_strelka',
            'run_annovar',
            'run_vep',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My WES Analysis'
            }),
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., workflow_test'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make name field optional for quick config generation
        self.fields['name'].required = False
