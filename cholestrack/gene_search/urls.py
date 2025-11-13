# gene_search/urls.py
"""
URL patterns for gene search app.
"""

from django.urls import path
from . import views

app_name = 'gene_search'

urlpatterns = [
    path('', views.search_home, name='search_home'),
    path('process/<int:query_id>/', views.process_search, name='process_search'),
    path('result/<int:query_id>/', views.search_result, name='search_result'),
    path('refresh/<int:query_id>/', views.refresh_search, name='refresh_search'),
    path('history/', views.search_history, name='search_history'),
]
