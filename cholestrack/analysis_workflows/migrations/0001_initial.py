# Generated migration file for analysis_workflows

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Descriptive name for this configuration', max_length=200, verbose_name='Configuration Name')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('aligner', models.CharField(choices=[('bwa', 'BWA-MEM'), ('dragmap', 'DRAGEN DRAGMAP'), ('minimap2', 'Minimap2')], default='bwa', max_length=20, verbose_name='Alignment Tool')),
                ('minimap2_preset', models.CharField(blank=True, choices=[('sr', 'Short reads (Illumina)'), ('map-ont', 'Oxford Nanopore'), ('map-pb', 'PacBio CLR'), ('map-hifi', 'PacBio HiFi/CCS'), ('asm5', 'Assembly-to-ref (≥95% identity)'), ('asm10', 'Assembly-to-ref (≥90% identity)'), ('asm20', 'Assembly-to-ref (≥80% identity)')], default='sr', max_length=20, verbose_name='Minimap2 Preset')),
                ('use_gatk', models.BooleanField(default=True, verbose_name='Use GATK HaplotypeCaller')),
                ('use_strelka', models.BooleanField(default=False, verbose_name='Use Strelka2')),
                ('run_annovar', models.BooleanField(default=True, verbose_name='Run ANNOVAR')),
                ('run_vep', models.BooleanField(default=False, verbose_name='Run VEP')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_configs', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Workflow Configuration',
                'verbose_name_plural': 'Workflow Configurations',
                'ordering': ['-created_at'],
            },
        ),
    ]
