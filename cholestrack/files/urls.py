# files/urls.py
from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('download/<int:file_location_id>/', views.download_file, name='download_file'),
    path('info/<int:file_location_id>/', views.file_info, name='file_info'),
]