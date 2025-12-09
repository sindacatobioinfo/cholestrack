# Generated manually for adding administered_drugs field to Patient model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0003_patient_signs_and_symptoms'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='administered_drugs',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of drugs/chemicals administered to the patient",
                verbose_name='Administered Drugs'
            ),
        ),
    ]
