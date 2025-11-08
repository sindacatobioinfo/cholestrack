# samples/urls.py
from django.urls import path
from . import views

app_name = 'samples'

urlpatterns = [
    path('', views.sample_list, name='sample_list'),
    path('create/', views.patient_create, name='patient_create'),
    path('detail/<str:patient_id>/', views.sample_detail, name='sample_detail'),
    path('edit/<str:patient_id>/', views.patient_edit, name='patient_edit'),
    path('delete/<str:patient_id>/', views.patient_delete, name='patient_delete'),
]