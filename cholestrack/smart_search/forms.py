# smart_search/forms.py
"""
Forms for gene search using HPO.
"""

from django import forms


class GeneSearchForm(forms.Form):
    """
    Form for searching genes, phenotypes, or diseases in HPO database.
    """

    SEARCH_TYPE_CHOICES = [
        ('gene', 'Search by Gene'),
        ('phenotype', 'Search by Phenotype'),
        ('disease', 'Search by Disease'),
        ('variant', 'Search by Variant'),
    ]

    search_type = forms.ChoiceField(
        choices=SEARCH_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'search-type-radio'
        }),
        initial='gene',
        label='Search Type'
    )

    search_term = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter gene symbol, phenotype, disease name, or variant ID...',
            'autofocus': True,
            'id': 'search-term-input'
        }),
        label='Search Term',
        help_text='Enter a gene symbol, phenotype, disease name, or variant ID (e.g., rs333)'
    )

    def clean_search_term(self):
        """Validate and clean search term."""
        search_type = self.cleaned_data.get('search_type', 'gene')
        search_term = self.cleaned_data.get('search_term', '').strip()

        if not search_term:
            raise forms.ValidationError("Please enter a search term")

        # For gene searches, uppercase the term
        if search_type == 'gene':
            search_term = search_term.upper()
            if len(search_term) < 2:
                raise forms.ValidationError("Gene symbol must be at least 2 characters long")
        elif search_type == 'phenotype':
            # For phenotype searches, keep original case but validate length
            if len(search_term) < 3:
                raise forms.ValidationError("Phenotype search term must be at least 3 characters long")
        elif search_type == 'disease':
            # For disease searches, keep original case but validate length
            if len(search_term) < 3:
                raise forms.ValidationError("Disease search term must be at least 3 characters long")
        elif search_type == 'variant':
            # For variant searches, keep original case but validate length
            if len(search_term) < 2:
                raise forms.ValidationError("Variant ID must be at least 2 characters long")

        return search_term
