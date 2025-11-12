# region_selection/apps.py
from django.apps import AppConfig


class RegionSelectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'region_selection'
    verbose_name = 'Region Selection'
