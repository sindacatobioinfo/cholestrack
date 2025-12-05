# Generated manually for signs_and_symptoms field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0002_patient_analysis_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='signs_and_symptoms',
            field=models.JSONField(
                default=list,
                blank=True,
                verbose_name='Signs and Symptoms (HPO)',
                help_text="List of HPO phenotype terms describing patient's signs and symptoms"
            ),
        ),
    ]
