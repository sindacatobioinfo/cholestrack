# users/models.py
from django.db import models
from django.contrib.auth.models import User

class Patient(models.Model):
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    patient_id = models.CharField(max_length=50, unique=True, verbose_name="ID do Paciente")
    name = models.CharField(max_length=100, verbose_name="Nome Completo")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    clinical_info_json = models.JSONField(
        default=dict,
        verbose_name="Informações Clínicas (JSON)",
        help_text="Dados clínicos não estruturados em formato JSON."
    )
    main_exome_result = models.CharField(max_length=255, default="Aguardando Análise", verbose_name="Resultado Principal")

    def __str__(self):
        return f"{self.patient_id} - {self.name}"

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

class AnalysisFileLocation(models.Model):
    patient = models.ForeignKey(
        Patient, 
        on_delete=models.CASCADE, 
        related_name='file_locations',
        verbose_name="Paciente"
    )
    
    # NOVAS COLUNAS SOLICITADAS: project, batch, sample_id, data_type
    project_name = models.CharField(max_length=50, verbose_name="Projeto")
    batch_id = models.CharField(max_length=50, verbose_name="Batch")
    sample_id = models.CharField(max_length=50, verbose_name="ID da Amostra")
    
    DATA_TYPE_CHOICES = [
        ('WGS', 'WGS'),
        ('WES', 'WES'),
        ('RNA', 'RNA-Seq'),
        ('OTHER', 'Outro'),
    ]
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES, default='WES', verbose_name="Tipo de Dado")
    
    SERVER_CHOICES = [
        ('SERVER1', 'Servidor BioHub Principal'),
        ('SERVER2', 'Servidor Burlo Garofolo (Arquivo Morto)'),
        ('SERVER3', 'Servidor de Backup/FTP'),
    ]
    server_name = models.CharField(max_length=10, choices=SERVER_CHOICES, verbose_name="Servidor")
    file_path = models.CharField(max_length=255, verbose_name="Caminho do Arquivo")
    file_type = models.CharField(max_length=10, default="VCF", verbose_name="Tipo de Arquivo")
    
    def __str__(self):
        return f"{self.patient.patient_id} - {self.sample_id} ({self.data_type}) - {self.file_type}"

    class Meta:
        verbose_name = "Localização do Arquivo de Análise"
        verbose_name_plural = "Localizações dos Arquivos de Análise"