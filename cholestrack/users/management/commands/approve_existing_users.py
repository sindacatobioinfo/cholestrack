# users/management/commands/approve_existing_users.py
"""
Management command to approve all existing users with Administrator role.
This is a one-time migration command for users created before the RBAC and email verification system.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from users.models import UserRole, EmailVerification
from profile.models import UserProfile


class Command(BaseCommand):
    help = 'Approve all existing users with Administrator role and mark emails as verified'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        users = User.objects.all()
        role_created_count = 0
        email_created_count = 0
        already_approved_count = 0

        self.stdout.write(f'Processing {users.count()} users...\n')

        for user in users:
            user_updated = False

            # Create or update UserRole
            if not hasattr(user, 'role'):
                if not dry_run:
                    UserRole.objects.create(
                        user=user,
                        role='ADMIN',
                        confirmed_by_admin=True,
                        confirmed_at=timezone.now()
                    )
                self.stdout.write(
                    f'  ✓ Created Administrator role for user: {user.username} ({user.email})'
                )
                role_created_count += 1
                user_updated = True
            else:
                # Update existing role if not confirmed
                if not user.role.confirmed_by_admin:
                    if not dry_run:
                        user.role.role = 'ADMIN'
                        user.role.confirmed_by_admin = True
                        user.role.confirmed_at = timezone.now()
                        user.role.save()
                    self.stdout.write(
                        f'  ✓ Updated role to Administrator for user: {user.username} ({user.email})'
                    )
                    role_created_count += 1
                    user_updated = True
                else:
                    already_approved_count += 1

            # Create EmailVerification if doesn't exist
            if not hasattr(user, 'email_verification'):
                if not dry_run:
                    EmailVerification.objects.create(
                        user=user,
                        email_confirmed=True,
                        verification_token=get_random_string(64),
                        confirmed_at=timezone.now()
                    )
                self.stdout.write(
                    f'  ✓ Created email verification record for user: {user.username}'
                )
                email_created_count += 1
                user_updated = True
            else:
                # Mark as confirmed if not already
                if not user.email_verification.email_confirmed:
                    if not dry_run:
                        user.email_verification.email_confirmed = True
                        user.email_verification.confirmed_at = timezone.now()
                        user.email_verification.save()
                    self.stdout.write(
                        f'  ✓ Marked email as verified for user: {user.username}'
                    )
                    email_created_count += 1
                    user_updated = True

            # Ensure user is active
            if not user.is_active:
                if not dry_run:
                    user.is_active = True
                    user.save()
                self.stdout.write(
                    f'  ✓ Activated user account: {user.username}'
                )
                user_updated = True

            # Sync UserProfile.role with UserRole.role if they exist
            if hasattr(user, 'role') and hasattr(user, 'profile'):
                if user.profile.role != user.role.role:
                    if not dry_run:
                        user.profile.role = user.role.role
                        user.profile.save()
                    self.stdout.write(
                        f'  ✓ Synced profile role with UserRole for user: {user.username}'
                    )
                    user_updated = True

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('MIGRATION COMPLETE'))

        self.stdout.write(f'\nTotal users processed: {users.count()}')
        self.stdout.write(f'Roles created/updated: {role_created_count}')
        self.stdout.write(f'Email verifications created/updated: {email_created_count}')
        self.stdout.write(f'Already approved: {already_approved_count}')

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Successfully approved {role_created_count} existing users with Administrator role'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\nRun without --dry-run to apply these changes'
                )
            )
