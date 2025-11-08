# profile/migrations/000X_create_profiles_for_existing_users.py
from django.db import migrations

def create_missing_profiles(apps, schema_editor):
    """
    Creates UserProfile records for all User instances that do not have an associated profile.
    This addresses the situation where users were created before the UserProfile model existed.
    """
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('profile', 'UserProfile')
    
    # Get all users
    users = User.objects.all()
    
    for user in users:
        # Check if this user already has a profile
        if not UserProfile.objects.filter(user=user).exists():
            # Create a profile with default values
            UserProfile.objects.create(
                user=user,
                role='RESEARCHER',  # Default role
                team='LAB_DADAMO',  # Default team
                profile_completed=False,  # They need to complete their profile
                approved=True  # Existing users are pre-approved
            )
            print(f"Created profile for user: {user.username}")

def reverse_migration(apps, schema_editor):
    """
    Reverse operation: This is optional and would only be used if rolling back the migration.
    In this case, we do nothing on reverse since we don't want to delete profiles.
    """
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0001_initial'),  # Adjust this to match your actual initial migration
        ('auth', '0012_alter_user_first_name_max_length'),  # Ensures User model is available
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, reverse_migration),
    ]