# gene_search/forms.py
"""
Forms for gene/disease/drug search.
"""

from django import forms


class GeneSearchForm(forms.Form):
    """
    Form for searching genes, diseases, or drugs.
    """
    SEARCH_TYPE_CHOICES = [
        ('GENE', 'Gene'),
        ('DISEASE', 'Disease'),
        ('DRUG', 'Drug'),
    ]

    search_type = forms.ChoiceField(
        choices=SEARCH_TYPE_CHOICES,
        initial='GENE',
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio h-4 w-4 text-blue-600'
        }),
        label='Search Type'
    )

    search_term = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter gene name (e.g., ATP8B1, BRCA1), disease name, or drug name...',
            'autofocus': True
        }),
        label='Search Term',
        help_text='Enter a gene symbol (e.g., ATP8B1), disease name, or drug name'
    )

    def clean_search_term(self):
        """Validate and clean search term."""
        search_term = self.cleaned_data.get('search_term', '').strip().upper()

        if not search_term:
            raise forms.ValidationError("Please enter a search term")

        if len(search_term) < 2:
            raise forms.ValidationError("Search term must be at least 2 characters long")

        return search_term
