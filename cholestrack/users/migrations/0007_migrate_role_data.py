# Generated manually - Data migration to update role values

from django.db import migrations


def migrate_role_data(apps, schema_editor):
    """
    Migrate existing role data:
    - MANAGER -> DATA_MANAGER
    - VIEWER -> CLINICIAN
    """
    UserRole = apps.get_model('users', 'UserRole')

    # Update MANAGER to DATA_MANAGER
    manager_count = UserRole.objects.filter(role='MANAGER').update(role='DATA_MANAGER')
    print(f"  → Migrated {manager_count} MANAGER roles to DATA_MANAGER")

    # Update VIEWER to CLINICIAN
    viewer_count = UserRole.objects.filter(role='VIEWER').update(role='CLINICIAN')
    print(f"  → Migrated {viewer_count} VIEWER roles to CLINICIAN")

    print(f"  ✓ Role data migration complete: {manager_count + viewer_count} roles updated")


def reverse_migrate_role_data(apps, schema_editor):
    """
    Reverse migration:
    - DATA_MANAGER -> MANAGER
    - CLINICIAN -> VIEWER
    """
    UserRole = apps.get_model('users', 'UserRole')

    # Reverse DATA_MANAGER to MANAGER
    UserRole.objects.filter(role='DATA_MANAGER').update(role='MANAGER')

    # Reverse CLINICIAN to VIEWER
    UserRole.objects.filter(role='CLINICIAN').update(role='VIEWER')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_update_role_choices'),
    ]

    operations = [
        migrations.RunPython(migrate_role_data, reverse_migrate_role_data),
    ]
