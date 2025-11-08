# users/admin.py
from django.contrib import admin
from .models import Patient, AnalysisFileLocation
from django.contrib.auth.models import User

# 1. Registro do Modelo Patient (Paciente)
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'name', 'birth_date', 'main_exome_result')
    search_fields = ('patient_id', 'name')
    list_filter = ('main_exome_result',)
    fields = ('patient_id', 'name', 'birth_date', 'main_exome_result', 'clinical_info_json', 'responsible_user')
    readonly_fields = ('responsible_user',)

# 2. Registro do Modelo AnalysisFileLocation (Localização do Arquivo)
@admin.register(AnalysisFileLocation)
class AnalysisFileLocationAdmin(admin.ModelAdmin):
    # NOVOS CAMPOS adicionados para exibição e filtro
    list_display = ('patient', 'sample_id', 'project_name', 'data_type', 'file_type', 'server_name', 'file_path')
    # NOVOS CAMPOS para filtro
    list_filter = ('project_name', 'data_type', 'server_name', 'file_type')
    search_fields = ('patient__patient_id', 'patient__name', 'sample_id', 'file_path')