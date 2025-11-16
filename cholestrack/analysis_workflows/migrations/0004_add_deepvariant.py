# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_workflows', '0003_add_model_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowconfiguration',
            name='use_deepvariant',
            field=models.BooleanField(default=False, verbose_name='Use DeepVariant'),
        ),
    ]
