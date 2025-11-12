# region_selection/management/commands/cleanup_expired_extractions.py
"""
Management command to clean up expired region extraction jobs.

Usage:
    python manage.py cleanup_expired_extractions

This command should be run periodically (e.g., every 5 minutes) via cron:
    */5 * * * * cd /path/to/cholestrack && python manage.py cleanup_expired_extractions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from region_selection.models import RegionExtractionJob
from region_selection.utils import cleanup_job_files


class Command(BaseCommand):
    help = 'Clean up expired region extraction temporary files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually deleting files',
        )
        parser.add_argument(
            '--all-downloaded',
            action='store_true',
            help='Also clean up files that have been downloaded (not just expired)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clean_downloaded = options['all_downloaded']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be deleted'))

        now = timezone.now()
        cleaned_count = 0
        failed_count = 0

        # Find expired jobs
        expired_jobs = RegionExtractionJob.objects.filter(
            status='COMPLETED',
            expires_at__lte=now
        )

        self.stdout.write(f'\nFound {expired_jobs.count()} expired jobs to clean up')

        for job in expired_jobs:
            self.stdout.write(f'  Processing job {job.job_id} (Sample: {job.sample_id})...')

            if not dry_run:
                # Update status
                job.status = 'EXPIRED'
                job.save()

                # Clean up files
                if cleanup_job_files(job):
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Cleaned up expired job {job.job_id}'))
                    cleaned_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'    ✗ Failed to clean up job {job.job_id}'))
                    failed_count += 1
            else:
                self.stdout.write(f'    Would clean up job {job.job_id}')
                cleaned_count += 1

        # Optionally clean up downloaded files
        if clean_downloaded:
            downloaded_jobs = RegionExtractionJob.objects.filter(
                status='DOWNLOADED'
            )

            self.stdout.write(f'\nFound {downloaded_jobs.count()} downloaded jobs to clean up')

            for job in downloaded_jobs:
                self.stdout.write(f'  Processing downloaded job {job.job_id}...')

                if not dry_run:
                    if cleanup_job_files(job):
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Cleaned up downloaded job {job.job_id}'))
                        cleaned_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'    ✗ Failed to clean up job {job.job_id}'))
                        failed_count += 1
                else:
                    self.stdout.write(f'    Would clean up job {job.job_id}')
                    cleaned_count += 1

        # Summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No files were deleted'))
            self.stdout.write(f'\nWould clean up: {cleaned_count} jobs')
        else:
            self.stdout.write(self.style.SUCCESS('CLEANUP COMPLETE'))
            self.stdout.write(f'\nSuccessfully cleaned: {cleaned_count} jobs')
            if failed_count > 0:
                self.stdout.write(self.style.WARNING(f'Failed to clean: {failed_count} jobs'))
