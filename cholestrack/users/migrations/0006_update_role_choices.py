# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userrole',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrator'),
                    ('DATA_MANAGER', 'Data Manager'),
                    ('RESEARCHER', 'Researcher'),
                    ('CLINICIAN', 'Clinician')
                ],
                default='CLINICIAN',
                max_length=20,
                verbose_name='Role'
            ),
        ),
    ]
