# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_workflows', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowconfiguration',
            name='project_name',
            field=models.CharField(default='workflow_test', help_text='Project name for input/output directory structure', max_length=200, verbose_name='Project Name'),
        ),
        migrations.AlterField(
            model_name='workflowconfiguration',
            name='aligner',
            field=models.CharField(choices=[('bwa', 'BWA-MEM'), ('dragmap', 'DRAGEN DRAGMAP'), ('minimap2', 'Minimap2')], default='minimap2', max_length=20, verbose_name='Alignment Tool'),
        ),
        migrations.AlterField(
            model_name='workflowconfiguration',
            name='use_strelka',
            field=models.BooleanField(default=True, verbose_name='Use Strelka2'),
        ),
        migrations.AlterField(
            model_name='workflowconfiguration',
            name='run_annovar',
            field=models.BooleanField(default=False, verbose_name='Run ANNOVAR'),
        ),
        migrations.AlterField(
            model_name='workflowconfiguration',
            name='run_vep',
            field=models.BooleanField(default=True, verbose_name='Run VEP'),
        ),
    ]
