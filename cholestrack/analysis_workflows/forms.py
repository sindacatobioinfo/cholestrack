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
            'model_type',
            'aligner',
            'minimap2_preset',
            'use_gatk',
            'use_strelka',
            'use_deepvariant',
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

    def clean(self):
        """
        Validate that at least one variant caller and one annotation tool are selected.
        """
        cleaned_data = super().clean()

        # Validate variant callers - at least one must be selected
        use_gatk = cleaned_data.get('use_gatk', False)
        use_strelka = cleaned_data.get('use_strelka', False)
        use_deepvariant = cleaned_data.get('use_deepvariant', False)

        if not (use_gatk or use_strelka or use_deepvariant):
            raise forms.ValidationError(
                'You must select at least one variant caller (GATK HaplotypeCaller, Strelka2, or DeepVariant).'
            )

        # Validate annotation tools - at least one must be selected
        run_annovar = cleaned_data.get('run_annovar', False)
        run_vep = cleaned_data.get('run_vep', False)

        if not (run_annovar or run_vep):
            raise forms.ValidationError(
                'You must select at least one annotation tool (ANNOVAR or VEP).'
            )

        return cleaned_data
