# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_workflows', '0002_update_defaults_add_project_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowconfiguration',
            name='model_type',
            field=models.CharField(choices=[('WES', 'Whole Exome Sequencing'), ('WGS', 'Whole Genome Sequencing')], default='WES', max_length=3, verbose_name='Analysis Type'),
        ),
    ]
