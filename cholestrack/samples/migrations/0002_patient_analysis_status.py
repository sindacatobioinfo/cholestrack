# Generated manually for analysis_status field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='analysis_status',
            field=models.CharField(
                choices=[
                    ('AWAITING_PROCESSING', 'Awaiting Processing'),
                    ('PROCESSING_DONE', 'Processing Done'),
                    ('ANALYSIS_DONE', 'Analysis Done')
                ],
                default='AWAITING_PROCESSING',
                help_text='Current status of the genomic analysis pipeline',
                max_length=30,
                verbose_name='Analysis Status',
                db_index=True
            ),
        ),
    ]
