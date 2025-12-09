# Generated manually for adding clinpgx_drug_labels field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0007_add_clinpgx_variant_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='genesearchquery',
            name='clinpgx_drug_labels',
            field=models.JSONField(
                blank=True,
                help_text='Drug label annotations from ClinPGx API',
                null=True,
                verbose_name='ClinPGx Drug Labels'
            ),
        ),
    ]
