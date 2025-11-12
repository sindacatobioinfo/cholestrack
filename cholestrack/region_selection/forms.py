# region_selection/forms.py
"""
Forms for region extraction input.
"""

from django import forms
from files.models import AnalysisFileLocation


class RegionExtractionForm(forms.Form):
    """
    Form for specifying region extraction parameters.
    Users can either provide a gene name OR genomic coordinates.
    """

    # Sample selection
    sample_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Sample ID (e.g., SAMPLE001)',
            'autocomplete': 'off'
        }),
        label='Sample ID',
        help_text='Enter the sample ID associated with the BAM file'
    )

    # Region specification method
    REGION_METHOD_CHOICES = [
        ('gene', 'Gene Name'),
        ('coordinates', 'Genomic Coordinates'),
    ]

    region_method = forms.ChoiceField(
        choices=REGION_METHOD_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Region Specification Method',
        initial='coordinates'
    )

    # Gene name (if using gene method)
    gene_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Gene Name (e.g., BRCA1, TP53)',
            'autocomplete': 'off'
        }),
        label='Gene Name',
        help_text='Official gene symbol (HGNC nomenclature recommended)'
    )

    # Genomic coordinates (if using coordinates method)
    chromosome = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., chr1, 1, X, Y',
            'autocomplete': 'off'
        }),
        label='Chromosome',
        help_text='Chromosome name (with or without "chr" prefix)'
    )

    start_position = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 100000',
            'autocomplete': 'off'
        }),
        label='Start Position (bp)',
        help_text='Start position in base pairs'
    )

    end_position = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 200000',
            'autocomplete': 'off'
        }),
        label='End Position (bp)',
        help_text='End position in base pairs'
    )

    def clean(self):
        """
        Validate that either gene name or coordinates are provided, but not both.
        """
        cleaned_data = super().clean()
        region_method = cleaned_data.get('region_method')
        gene_name = cleaned_data.get('gene_name')
        chromosome = cleaned_data.get('chromosome')
        start_position = cleaned_data.get('start_position')
        end_position = cleaned_data.get('end_position')

        if region_method == 'gene':
            # Gene method selected - require gene name
            if not gene_name:
                raise forms.ValidationError(
                    "Please provide a gene name when using the Gene Name method."
                )
            # Clear coordinate fields
            cleaned_data['chromosome'] = None
            cleaned_data['start_position'] = None
            cleaned_data['end_position'] = None

        elif region_method == 'coordinates':
            # Coordinates method selected - require all coordinate fields
            if not all([chromosome, start_position, end_position]):
                raise forms.ValidationError(
                    "Please provide chromosome, start position, and end position when using the Genomic Coordinates method."
                )

            # Validate that start < end
            if start_position >= end_position:
                raise forms.ValidationError(
                    "Start position must be less than end position."
                )

            # Clear gene name field
            cleaned_data['gene_name'] = None

        return cleaned_data

    def clean_sample_id(self):
        """
        Validate that the sample ID exists and has an associated BAM file.
        """
        sample_id = self.cleaned_data.get('sample_id')

        # Check if BAM file exists for this sample
        bam_files = AnalysisFileLocation.objects.filter(
            sample_id=sample_id,
            file_type='BAM',
            is_active=True
        )

        if not bam_files.exists():
            raise forms.ValidationError(
                f"No active BAM file found for sample ID: {sample_id}. "
                "Please check the sample ID and try again."
            )

        return sample_id

    def clean_chromosome(self):
        """
        Normalize chromosome names.
        """
        chromosome = self.cleaned_data.get('chromosome')
        if chromosome:
            # Normalize chromosome name
            chromosome = chromosome.strip().upper()
            # Add 'chr' prefix if not present and not a number, X, Y, M
            if not chromosome.startswith('CHR') and chromosome not in ['X', 'Y', 'M', 'MT']:
                if chromosome.isdigit():
                    chromosome = f'chr{chromosome}'
            return chromosome
        return chromosome
