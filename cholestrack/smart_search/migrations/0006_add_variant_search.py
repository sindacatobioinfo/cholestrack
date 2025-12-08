# Generated manually for adding variant search type and variant_data field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0005_add_clinpgx_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='genesearchquery',
            name='variant_data',
            field=models.JSONField(
                blank=True,
                help_text='Variant information from Ensembl API',
                null=True,
                verbose_name='Variant Data'
            ),
        ),
        migrations.AlterField(
            model_name='genesearchquery',
            name='search_type',
            field=models.CharField(
                choices=[('gene', 'Gene'), ('phenotype', 'Phenotype'), ('disease', 'Disease'), ('variant', 'Variant')],
                default='gene',
                help_text='Type of search: gene, phenotype, disease, or variant',
                max_length=20,
                verbose_name='Search Type'
            ),
        ),
    ]
