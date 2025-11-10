"""
Custom Django management command to import TSV data into cholestrack database.
Place this file in: cholestrack/management/commands/import_data.py
"""

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime, parse_date
from samples.models import Patient
from files.models import AnalysisFileLocation
import csv
import json
from pathlib import Path


class Command(BaseCommand):
    help = 'Import data from TSV files into cholestrack database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples',
            type=str,
            help='Path to samples_patient.tsv file',
            required=False,
            default=None
        )
        parser.add_argument(
            '--files',
            type=str,
            help='Path to files_analysisfilelocation.tsv file',
            required=False,
            default=None
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing (use with caution!)'
        )

    def handle(self, *args, **options):
        samples_path = options['samples']
        files_path = options['files']
        
        # Check that at least one file path was provided
        if not samples_path and not files_path:
            self.stdout.write(self.style.ERROR(
                'Error: You must provide at least one file to import (--samples or --files)'
            ))
            return
        
        # Verify that provided files exist
        if samples_path and not Path(samples_path).exists():
            self.stdout.write(self.style.ERROR(f'Samples file not found: {samples_path}'))
            return
        
        if files_path and not Path(files_path).exists():
            self.stdout.write(self.style.ERROR(f'Files file not found: {files_path}'))
            return

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            if files_path:
                AnalysisFileLocation.objects.all().delete()
            if samples_path:
                Patient.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared'))

        # Import samples if provided
        if samples_path:
            self.import_samples(samples_path)
        else:
            self.stdout.write(self.style.WARNING('Skipping samples import (no file provided)'))
        
        # Import files if provided
        if files_path:
            self.import_files(files_path)
        else:
            self.stdout.write(self.style.WARNING('Skipping files import (no file provided)'))
        
        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))

    def import_samples(self, filepath):
        """Import samples_patient data"""
        self.stdout.write(f'Importing samples from {filepath}...')
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                try:
                    # Check if record already exists
                    record_id = int(row['id'])
                    if Patient.objects.filter(pk=record_id).exists():
                        self.stdout.write(self.style.WARNING(
                            f'Sample with ID {record_id} already exists, skipping...'
                        ))
                        skipped += 1
                        continue
                    
                    # Parse date and timestamps
                    birth_date = parse_date(row['birth_date']) if row['birth_date'] else None
                    created_at = parse_datetime(row['created_at']) if row['created_at'] else None
                    updated_at = parse_datetime(row['updated_at']) if row['updated_at'] else None
                    
                    # Handle JSON field - convert string to actual dict/list object
                    try:
                        clinical_info = json.loads(row['clinical_info_json']) if row['clinical_info_json'] and row['clinical_info_json'].strip() else {}
                    except json.JSONDecodeError:
                        clinical_info = {}
                    
                    # Handle foreign key - responsible_user_id
                    responsible_user_id = int(row['responsible_user_id']) if row['responsible_user_id'] else None
                    
                    # Create the record
                    sample = Patient(
                        id=record_id,
                        patient_id=row['patient_id'],
                        name=row['name'],
                        birth_date=birth_date,
                        clinical_info_json=clinical_info,
                        main_exome_result=row['main_exome_result'] if row['main_exome_result'] else '',
                        notes=row['notes'] if row['notes'] else '',
                        created_at=created_at,
                        updated_at=updated_at,
                        responsible_user_id=responsible_user_id,
                    )
                    
                    # Use force_insert to preserve the original ID and bypass auto-generation
                    sample.save(force_insert=True)
                    
                    # If your model has auto_now=True on updated_at, we need to update it manually
                    # This bypasses the auto_now behavior
                    if updated_at:
                        Patient.objects.filter(id=record_id).update(
                            updated_at=updated_at
                        )
                    
                    imported += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Error importing sample ID {row.get("id", "unknown")}: {str(e)}'
                    ))
                    errors += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Samples import complete: {imported} imported, {skipped} skipped, {errors} errors'
        ))

    def import_files(self, filepath):
        """Import files_analysisfilelocation data"""
        self.stdout.write(f'Importing files from {filepath}...')
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                try:
                    # Check if record already exists
                    record_id = int(row['id'])
                    if AnalysisFileLocation.objects.filter(pk=record_id).exists():
                        self.stdout.write(self.style.WARNING(
                            f'File with ID {record_id} already exists, skipping...'
                        ))
                        skipped += 1
                        continue
                    
                    # Parse timestamps
                    created_at = parse_datetime(row['created_at']) if row['created_at'] else None
                    updated_at = parse_datetime(row['updated_at']) if row['updated_at'] else None
                    
                    # Handle the patient foreign key
                    try:
                        patient = Patient.objects.get(pk=int(row['patient_id']))
                    except Patient.DoesNotExist:
                        self.stdout.write(self.style.ERROR(
                            f'Patient with ID {row["patient_id"]} not found for file {record_id}, skipping...'
                        ))
                        errors += 1
                        continue
                    
                    # Handle file_size_mb - could be NULL or a number
                    file_size_mb = None
                    if row['file_size_mb'] and row['file_size_mb'].upper() != 'NULL':
                        try:
                            file_size_mb = float(row['file_size_mb'])
                        except ValueError:
                            file_size_mb = None
                    
                    # Handle boolean field
                    is_active = row['is_active'].upper() == 'TRUE' if row['is_active'] else False
                    
                    # Handle uploaded_by_id foreign key
                    uploaded_by_id = int(row['uploaded_by_id']) if row['uploaded_by_id'] else None
                    
                    # Create the record
                    file_record = AnalysisFileLocation(
                        id=record_id,
                        project_name=row['project_name'],
                        batch_id=row['batch_id'],
                        sample_id=row['sample_id'],
                        data_type=row['data_type'],
                        server_name=row['server_name'],
                        file_path=row['file_path'],
                        file_type=row['file_type'],
                        file_size_mb=file_size_mb,
                        checksum=row['checksum'],
                        is_active=is_active,
                        created_at=created_at,
                        updated_at=updated_at,
                        patient=patient,  # ForeignKey relationship
                        uploaded_by_id=uploaded_by_id,
                    )
                    
                    # Use force_insert to preserve the original ID and bypass auto-generation
                    file_record.save(force_insert=True)
                    
                    # If your model has auto_now=True on updated_at, we need to update it manually
                    if updated_at:
                        AnalysisFileLocation.objects.filter(id=record_id).update(
                            updated_at=updated_at
                        )
                    
                    imported += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Error importing file ID {row.get("id", "unknown")}: {str(e)}'
                    ))
                    errors += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Files import complete: {imported} imported, {skipped} skipped, {errors} errors'
        ))