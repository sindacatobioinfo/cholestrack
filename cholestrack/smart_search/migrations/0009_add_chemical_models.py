# Generated manually for adding Chemical and ChemicalRelationship models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smart_search', '0008_add_clinpgx_drug_labels'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chemical',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chemical_id', models.CharField(db_index=True, help_text='Chemical identifier (e.g., PA449015)', max_length=200, unique=True, verbose_name='Chemical ID')),
                ('chemical_name', models.CharField(help_text='Name of the chemical/drug', max_length=500, verbose_name='Chemical Name')),
            ],
            options={
                'verbose_name': 'Chemical',
                'verbose_name_plural': 'Chemicals',
                'ordering': ['chemical_name'],
                'indexes': [
                    models.Index(fields=['chemical_id'], name='smart_searc_chemica_idx1'),
                    models.Index(fields=['chemical_name'], name='smart_searc_chemica_idx2'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ChemicalRelationship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity1_id', models.CharField(max_length=200, verbose_name='Entity 1 ID')),
                ('entity1_name', models.CharField(max_length=500, verbose_name='Entity 1 Name')),
                ('entity1_type', models.CharField(max_length=100, verbose_name='Entity 1 Type')),
                ('entity2_id', models.CharField(max_length=200, verbose_name='Entity 2 ID')),
                ('entity2_name', models.CharField(max_length=500, verbose_name='Entity 2 Name')),
                ('entity2_type', models.CharField(max_length=100, verbose_name='Entity 2 Type')),
                ('evidence', models.TextField(blank=True, null=True, verbose_name='Evidence')),
                ('association', models.CharField(blank=True, max_length=200, null=True, verbose_name='Association')),
                ('pharmacokinetics', models.CharField(blank=True, max_length=200, null=True, verbose_name='Pharmacokinetics (PK)')),
                ('pharmacodynamics', models.CharField(blank=True, max_length=200, null=True, verbose_name='Pharmacodynamics (PD)')),
            ],
            options={
                'verbose_name': 'Chemical Relationship',
                'verbose_name_plural': 'Chemical Relationships',
                'indexes': [
                    models.Index(fields=['entity1_type'], name='smart_searc_entity1_idx1'),
                    models.Index(fields=['entity2_type'], name='smart_searc_entity2_idx1'),
                    models.Index(fields=['entity1_id'], name='smart_searc_entity1_idx2'),
                    models.Index(fields=['entity2_id'], name='smart_searc_entity2_idx2'),
                ],
            },
        ),
    ]
