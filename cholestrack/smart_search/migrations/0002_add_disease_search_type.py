# Generated manually for adding disease search type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genesearchquery',
            name='search_type',
            field=models.CharField(
                choices=[('gene', 'Gene'), ('phenotype', 'Phenotype'), ('disease', 'Disease')],
                default='gene',
                help_text='Type of search: gene, phenotype, or disease',
                max_length=20,
                verbose_name='Search Type'
            ),
        ),
    ]
