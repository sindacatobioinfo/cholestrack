# region_selection/urls.py
"""
URL configuration for region_selection app.
"""

from django.urls import path
from . import views

app_name = 'region_selection'

urlpatterns = [
    # Main views
    path('', views.job_list, name='job_list'),
    path('create/', views.create_extraction, name='create_extraction'),
    path('job/<uuid:job_id>/', views.job_detail, name='job_detail'),
    path('job/<uuid:job_id>/process/', views.process_extraction, name='process_extraction'),
    path('job/<uuid:job_id>/download/', views.download_extracted_file, name='download_file'),
    path('job/<uuid:job_id>/download/<str:file_part>/', views.download_single_extracted_file, name='download_single_file'),

    # API endpoints
    path('api/job/<uuid:job_id>/status/', views.job_status_api, name='job_status_api'),
]
