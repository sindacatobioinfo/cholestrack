# analysis_workflows/urls.py
"""
URL configuration for analysis_workflows app.
"""

from django.urls import path
from . import views

app_name = 'analysis_workflows'

urlpatterns = [
    path('', views.config_builder, name='config_builder'),
    path('preview/', views.preview_config, name='preview'),
    path('download/', views.download_config, name='download'),
    path('saved/', views.saved_configs, name='saved_configs'),
    path('load/<int:config_id>/', views.load_config, name='load_config'),
]
