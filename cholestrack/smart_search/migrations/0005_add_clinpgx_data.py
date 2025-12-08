# Generated manually for adding ClinPGx data field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0004_genesearchquery_search_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='genesearchquery',
            name='clinpgx_data',
            field=models.JSONField(
                blank=True,
                help_text='Pharmacogenomic data from ClinPGx API',
                null=True,
                verbose_name='ClinPGx Data'
            ),
        ),
    ]
