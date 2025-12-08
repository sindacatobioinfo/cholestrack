# smart_search/views.py
"""
Views for smart gene search functionality using HPO.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from users.decorators import role_confirmed_required
from .models import GeneSearchQuery, HPOTerm, Disease
from .forms import GeneSearchForm
from .api_utils import fetch_gene_data, fetch_phenotype_data, fetch_disease_data, fetch_variant_data, fetch_clinpgx_variant_data


@login_required
@role_confirmed_required
def search_home(request):
    """
    Home page for gene search.
    Displays search form and recent searches.
    """
    if request.method == 'POST':
        form = GeneSearchForm(request.POST)
        if form.is_valid():
            search_type = form.cleaned_data['search_type']
            search_term = form.cleaned_data['search_term']

            # Check if we have a recent cached result
            cached_query = GeneSearchQuery.objects.filter(
                search_type=search_type,
                search_term=search_term,
                success=True
            ).order_by('-created_at').first()

            if cached_query and cached_query.is_cache_valid():
                # Use cached result
                messages.info(request, 'Showing cached results. Click "Refresh" to fetch new data.')
                return redirect('smart_search:search_result', query_id=cached_query.id)

            # Create new search query
            query = GeneSearchQuery.objects.create(
                user=request.user,
                search_type=search_type,
                search_term=search_term
            )

            # Redirect to processing view
            return redirect('smart_search:process_search', query_id=query.id)

    else:
        form = GeneSearchForm()

    # Get user's recent searches (last 10)
    recent_searches = GeneSearchQuery.objects.filter(
        user=request.user,
        success=True
    ).order_by('-created_at')[:10]

    context = {
        'form': form,
        'recent_searches': recent_searches,
        'title': 'Smart Search (HPO)'
    }
    return render(request, 'smart_search/search_home.html', context)


@login_required
@role_confirmed_required
def process_search(request, query_id):
    """
    Process the search query and fetch data from HPO API.
    """
    query = get_object_or_404(GeneSearchQuery, id=query_id, user=request.user)

    # Check if already processed
    if query.phenotypes is not None or query.diseases is not None:
        return redirect('smart_search:search_result', query_id=query.id)

    try:
        # Fetch data based on search type
        if query.search_type == 'gene':
            results = fetch_gene_data(query.search_term)
        elif query.search_type == 'phenotype':
            results = fetch_phenotype_data(query.search_term)
        elif query.search_type == 'disease':
            results = fetch_disease_data(query.search_term)
        elif query.search_type == 'variant':
            results = fetch_variant_data(query.search_term)
        else:
            # Default to gene search for backward compatibility
            results = fetch_gene_data(query.search_term)

        # Check for errors
        if 'error' in results:
            query.success = False
            query.error_message = results['error']
            query.save()
            messages.error(request, f'Error: {results["error"]}')
            return redirect('smart_search:search_result', query_id=query.id)

        # Store results based on search type
        if query.search_type == 'gene':
            query.phenotypes = results['phenotypes']
            query.diseases = results['diseases']
            query.gene_info = results['gene_info']
            query.clinpgx_data = results.get('clinpgx_data')  # Store ClinPGx data
            success_msg = (f'Found {len(results["phenotypes"])} HPO phenotype terms and '
                          f'{len(results["diseases"])} associated diseases for gene {query.search_term}.')
        elif query.search_type == 'phenotype':
            query.phenotypes = results['genes']  # Store genes in phenotypes field for phenotype searches
            query.diseases = results['diseases']
            query.gene_info = results['phenotype_info']  # Store phenotype info in gene_info field
            success_msg = (f'Found {len(results["genes"])} associated genes and '
                          f'{len(results["diseases"])} associated diseases for phenotype "{query.search_term}".')
        elif query.search_type == 'disease':
            query.phenotypes = results['phenotypes']  # Store phenotypes for disease
            query.diseases = results['genes']  # Store genes in diseases field for disease searches
            query.gene_info = results['disease_info']  # Store disease info in gene_info field
            success_msg = (f'Found {len(results["phenotypes"])} associated phenotypes and '
                          f'{len(results["genes"])} associated genes for disease "{query.search_term}".')
        else:  # variant search
            query.variant_data = results  # Store variant data

            # Fetch ClinPGx variant annotation data
            clinpgx_variant_results = fetch_clinpgx_variant_data(query.search_term)
            query.clinpgx_variant_data = clinpgx_variant_results  # Store ClinPGx variant data

            success_msg = f'Retrieved variant information for "{query.search_term}".'

        query.success = True

        # Set cache expiration (7 days)
        query.set_cache_expiration(days=7)

        query.save()

        messages.success(request, success_msg)

    except Exception as e:
        query.success = False
        query.error_message = str(e)
        query.save()

        messages.error(request, f'Error during search: {e}')

    return redirect('smart_search:search_result', query_id=query.id)


@login_required
@role_confirmed_required
def search_result(request, query_id):
    """
    Display search results for a query with pagination.
    """
    query = get_object_or_404(GeneSearchQuery, id=query_id, user=request.user)

    # Check if results expired
    cache_expired = not query.is_cache_valid() if query.cache_expires_at else False

    # Paginate phenotypes (10 per page)
    phenotypes_list = query.phenotypes if query.phenotypes else []
    phenotypes_paginator = Paginator(phenotypes_list, 10)
    phenotypes_page_number = request.GET.get('phenotypes_page', 1)

    try:
        phenotypes_page_obj = phenotypes_paginator.get_page(phenotypes_page_number)
    except (PageNotAnInteger, EmptyPage):
        phenotypes_page_obj = phenotypes_paginator.get_page(1)

    # Paginate diseases (10 per page)
    diseases_list = query.diseases if query.diseases else []
    diseases_paginator = Paginator(diseases_list, 10)
    diseases_page_number = request.GET.get('diseases_page', 1)

    try:
        diseases_page_obj = diseases_paginator.get_page(diseases_page_number)
    except (PageNotAnInteger, EmptyPage):
        diseases_page_obj = diseases_paginator.get_page(1)

    context = {
        'query': query,
        'cache_expired': cache_expired,
        'title': f'Results for {query.search_term}',
        'phenotypes_page_obj': phenotypes_page_obj,
        'diseases_page_obj': diseases_page_obj,
        'phenotypes_total_count': len(phenotypes_list),
        'diseases_total_count': len(diseases_list),
    }
    return render(request, 'smart_search/search_result.html', context)


@login_required
@role_confirmed_required
def refresh_search(request, query_id):
    """
    Refresh cached search results.
    """
    query = get_object_or_404(GeneSearchQuery, id=query_id, user=request.user)

    # Create new search query with same parameters
    new_query = GeneSearchQuery.objects.create(
        user=request.user,
        search_type=query.search_type,
        search_term=query.search_term
    )

    messages.info(request, 'Refreshing search results...')
    return redirect('smart_search:process_search', query_id=new_query.id)


@login_required
@role_confirmed_required
def search_history(request):
    """
    Display user's search history.
    """
    searches = GeneSearchQuery.objects.filter(user=request.user).order_by('-created_at')[:50]

    context = {
        'searches': searches,
        'title': 'Search History'
    }
    return render(request, 'smart_search/search_history.html', context)


@login_required
@role_confirmed_required
def autocomplete_phenotypes(request):
    """
    AJAX endpoint for phenotype autocomplete.
    Returns matching HPO terms based on partial input (minimum 5 characters).
    """
    query = request.GET.get('q', '').strip()

    # Minimum 5 characters to trigger autocomplete
    if len(query) < 5:
        return JsonResponse({'results': []})

    try:
        # Case-insensitive search in HPOTerm name field
        phenotypes = HPOTerm.objects.filter(
            name__icontains=query
        ).order_by('name')[:10]  # Limit to 10 results

        results = [
            {
                'hpo_id': phenotype.hpo_id,
                'name': phenotype.name,
                'display': f"{phenotype.name} ({phenotype.hpo_id})"
            }
            for phenotype in phenotypes
        ]

        return JsonResponse({'results': results})

    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})


@login_required
@role_confirmed_required
def autocomplete_diseases(request):
    """
    AJAX endpoint for disease autocomplete.
    Returns matching Disease terms based on partial input (minimum 5 characters).
    """
    query = request.GET.get('q', '').strip()

    # Minimum 5 characters to trigger autocomplete
    if len(query) < 5:
        return JsonResponse({'results': []})

    try:
        # Case-insensitive search in Disease name field
        diseases = Disease.objects.filter(
            disease_name__icontains=query
        ).order_by('disease_name')[:10]  # Limit to 10 results

        results = [
            {
                'disease_id': disease.database_id,
                'name': disease.disease_name,
                'display': f"{disease.disease_name} ({disease.database_id})"
            }
            for disease in diseases
        ]

        return JsonResponse({'results': results})

    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})
