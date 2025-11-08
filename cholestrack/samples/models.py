# samples/models.py
from django.db import models
from django.contrib.auth.models import User

class Patient(models.Model):
    """
    Patient model for storing cholestasis patient information and clinical data.
    This model focuses on the clinical and research aspects of patient records,
    while file management is delegated to the files application.
    """
    responsible_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Responsible User",
        help_text="The researcher or clinician responsible for this patient's data"
    )
    patient_id = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Patient ID",
        help_text="Unique identifier for the patient",
        db_index=True
    )
    name = models.CharField(
        max_length=100, 
        verbose_name="Full Name",
        help_text="Patient's full name (use anonymized ID if required by ethics protocols)"
    )
    birth_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Birth Date"
    )
    clinical_info_json = models.JSONField(
        default=dict,
        verbose_name="Clinical Information (JSON)",
        help_text="Unstructured clinical data in JSON format (e.g., diagnosis, symptoms, lab results, phenotype)"
    )
    main_exome_result = models.CharField(
        max_length=255, 
        default="Awaiting Analysis", 
        verbose_name="Main Exome Result",
        help_text="Summary of the main genomic finding or current analysis status"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Research Notes",
        help_text="Additional notes or observations about the patient or case"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        return f"{self.patient_id} - {self.name}"
    
    def get_file_count(self):
        """Returns the total number of analysis files associated with this patient."""
        return self.file_locations.filter(is_active=True).count()

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ['-created_at']