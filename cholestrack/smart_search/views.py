# smart_search/views.py
"""
Views for smart gene search functionality using HPO.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from users.decorators import role_confirmed_required
from .models import GeneSearchQuery
from .forms import GeneSearchForm
from .api_utils import fetch_gene_data


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
            search_term = form.cleaned_data['search_term']

            # Check if we have a recent cached result
            cached_query = GeneSearchQuery.objects.filter(
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
        # Fetch gene data from HPO
        results = fetch_gene_data(query.search_term)

        # Check for errors
        if 'error' in results:
            query.success = False
            query.error_message = results['error']
            query.save()
            messages.error(request, f'Error: {results["error"]}')
            return redirect('smart_search:search_result', query_id=query.id)

        # Store results
        query.phenotypes = results['phenotypes']
        query.diseases = results['diseases']
        query.gene_info = results['gene_info']
        query.success = True

        # Set cache expiration (7 days)
        query.set_cache_expiration(days=7)

        query.save()

        messages.success(
            request,
            f'Found {len(results["phenotypes"])} HPO phenotype terms and '
            f'{len(results["diseases"])} associated diseases for {query.search_term}.'
        )

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
