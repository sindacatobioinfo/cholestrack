# Generated migration for region_selection app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('files', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RegionExtractionJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique identifier for this extraction job', unique=True, verbose_name='Job ID')),
                ('sample_id', models.CharField(help_text='Sample ID for the BAM file', max_length=50, verbose_name='Sample ID')),
                ('gene_name', models.CharField(blank=True, help_text='Gene name for region extraction (e.g., BRCA1)', max_length=50, null=True, verbose_name='Gene Name')),
                ('chromosome', models.CharField(blank=True, help_text='Chromosome (e.g., chr1, 1, X, Y)', max_length=10, null=True, verbose_name='Chromosome')),
                ('start_position', models.BigIntegerField(blank=True, help_text='Start position in base pairs', null=True, verbose_name='Start Position')),
                ('end_position', models.BigIntegerField(blank=True, help_text='End position in base pairs', null=True, verbose_name='End Position')),
                ('output_file_path', models.CharField(blank=True, help_text='Path to the extracted BAM file in temporary storage', max_length=500, null=True, verbose_name='Output File Path')),
                ('output_file_size_mb', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Output File Size (MB)')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('DOWNLOADED', 'Downloaded'), ('EXPIRED', 'Expired')], default='PENDING', max_length=20, verbose_name='Status')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='Error Message')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('processing_started_at', models.DateTimeField(blank=True, null=True, verbose_name='Processing Started At')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed At')),
                ('downloaded_at', models.DateTimeField(blank=True, null=True, verbose_name='Downloaded At')),
                ('expires_at', models.DateTimeField(blank=True, help_text='When this temporary file should be deleted (10 minutes after completion)', null=True, verbose_name='Expires At')),
                ('original_bam_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='region_extractions', to='files.analysisfilelocation', verbose_name='Original BAM File')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='region_extractions', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Region Extraction Job',
                'verbose_name_plural': 'Region Extraction Jobs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='regionextractionjob',
            index=models.Index(fields=['job_id'], name='region_sele_job_id_4a1b6c_idx'),
        ),
        migrations.AddIndex(
            model_name='regionextractionjob',
            index=models.Index(fields=['user', 'status'], name='region_sele_user_id_3d8f2a_idx'),
        ),
        migrations.AddIndex(
            model_name='regionextractionjob',
            index=models.Index(fields=['expires_at'], name='region_sele_expires_6c9e1b_idx'),
        ),
    ]
