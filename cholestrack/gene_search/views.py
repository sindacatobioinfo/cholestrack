# gene_search/views.py
"""
Views for gene/disease/drug search functionality.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from users.decorators import role_confirmed_required
from .models import GeneSearchQuery
from .forms import GeneSearchForm
from .api_utils import fetch_all_relationships, fetch_disease_relationships


@login_required
@role_confirmed_required
def search_home(request):
    """
    Home page for gene/disease/drug search.
    Displays search form and recent searches.
    """
    if request.method == 'POST':
        form = GeneSearchForm(request.POST)
        if form.is_valid():
            search_term = form.cleaned_data['search_term']
            search_type = form.cleaned_data['search_type']

            # Check if we have a recent cached result
            cached_query = GeneSearchQuery.objects.filter(
                search_term=search_term,
                search_type=search_type,
                success=True
            ).order_by('-created_at').first()

            if cached_query and cached_query.is_cache_valid():
                # Use cached result
                messages.info(request, 'Showing cached results. Click "Refresh" to fetch new data.')
                return redirect('gene_search:search_result', query_id=cached_query.id)

            # Create new search query
            query = GeneSearchQuery.objects.create(
                user=request.user,
                search_term=search_term,
                search_type=search_type
            )

            # Redirect to processing view
            return redirect('gene_search:process_search', query_id=query.id)

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
        'title': 'Gene/Disease/Drug Search'
    }
    return render(request, 'gene_search/search_home.html', context)


@login_required
@role_confirmed_required
def process_search(request, query_id):
    """
    Process the search query and fetch data from APIs.
    """
    query = get_object_or_404(GeneSearchQuery, id=query_id, user=request.user)

    # Check if already processed
    if query.hpo_results is not None or query.omim_results is not None:
        return redirect('gene_search:search_result', query_id=query.id)

    try:
        # Get OMIM API key from settings if available
        omim_api_key = getattr(settings, 'OMIM_API_KEY', None)

        # Fetch all relationships based on search type
        if query.search_type == 'GENE':
            results = fetch_all_relationships(query.search_term, omim_api_key)

            # Store results
            query.hpo_results = results['hpo_results']
            query.omim_results = results['omim_results']
            query.pharmgkb_results = results['pharmgkb_results']
            query.is_pharmvar_gene = results.get('is_pharmvar_gene', False)
            query.success = True

            # Set cache expiration (7 days)
            query.set_cache_expiration(days=7)

            query.save()

            pharmvar_status = "This is a PharmVar gene." if query.is_pharmvar_gene else ""
            messages.success(
                request,
                f'Found {len(results["hpo_results"])} HPO terms, '
                f'{len(results["omim_results"])} OMIM diseases, and '
                f'{len(results["pharmgkb_results"])} PharmGKB entries for {query.search_term}. {pharmvar_status}'
            )

        elif query.search_type == 'DISEASE':
            results = fetch_disease_relationships(query.search_term, omim_api_key)

            # Store results
            query.hpo_results = results['hpo_results']
            query.omim_results = results.get('omim_results', [])
            query.pharmgkb_results = results['pharmgkb_results']
            query.success = True

            # Set cache expiration (7 days)
            query.set_cache_expiration(days=7)

            query.save()

            messages.success(
                request,
                f'Found {len(results["hpo_results"])} HPO terms and '
                f'{len(results["pharmgkb_results"])} PharmGKB drug associations for {query.search_term}.'
            )

        else:
            # For DRUG search type (future implementation)
            query.success = False
            query.error_message = f'{query.search_type} search is not yet implemented. Please use GENE or DISEASE search.'
            query.save()

            messages.warning(request, query.error_message)

    except Exception as e:
        query.success = False
        query.error_message = str(e)
        query.save()

        messages.error(request, f'Error during search: {e}')

    return redirect('gene_search:search_result', query_id=query.id)


@login_required
@role_confirmed_required
def search_result(request, query_id):
    """
    Display search results for a query.
    """
    query = get_object_or_404(GeneSearchQuery, id=query_id, user=request.user)

    # Check if results expired
    cache_expired = not query.is_cache_valid() if query.cache_expires_at else False

    context = {
        'query': query,
        'cache_expired': cache_expired,
        'title': f'Results for {query.search_term}'
    }
    return render(request, 'gene_search/search_result.html', context)


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
        search_term=query.search_term,
        search_type=query.search_type
    )

    messages.info(request, 'Refreshing search results...')
    return redirect('gene_search:process_search', query_id=new_query.id)


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
    return render(request, 'gene_search/search_history.html', context)
