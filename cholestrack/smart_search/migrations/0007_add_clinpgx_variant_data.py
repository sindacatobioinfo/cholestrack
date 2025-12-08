# Generated manually for adding clinpgx_variant_data field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0006_add_variant_search'),
    ]

    operations = [
        migrations.AddField(
            model_name='genesearchquery',
            name='clinpgx_variant_data',
            field=models.JSONField(
                blank=True,
                help_text='Variant annotation data from ClinPGx API',
                null=True,
                verbose_name='ClinPGx Variant Data'
            ),
        ),
    ]
