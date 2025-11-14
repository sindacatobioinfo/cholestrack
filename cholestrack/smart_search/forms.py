# smart_search/forms.py
"""
Forms for gene search using HPO.
"""

from django import forms


class GeneSearchForm(forms.Form):
    """
    Form for searching genes in HPO database.
    """

    search_term = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter gene symbol (e.g., ATP8B1, BRCA1)...',
            'autofocus': True
        }),
        label='Gene Symbol',
        help_text='Enter a gene symbol to search for associated HPO phenotypes and diseases'
    )

    def clean_search_term(self):
        """Validate and clean search term."""
        search_term = self.cleaned_data.get('search_term', '').strip().upper()

        if not search_term:
            raise forms.ValidationError("Please enter a gene symbol")

        if len(search_term) < 2:
            raise forms.ValidationError("Gene symbol must be at least 2 characters long")

        return search_term
