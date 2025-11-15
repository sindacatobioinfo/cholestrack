# analysis_workflows/apps.py
from django.apps import AppConfig


class AnalysisWorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analysis_workflows'
    verbose_name = 'Analysis Workflows'
