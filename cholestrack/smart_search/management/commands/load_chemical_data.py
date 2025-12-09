# smart_search/management/commands/load_chemical_data.py
"""
Management command to download and load ClinPGx chemical and relationships data.

Usage:
    python manage.py load_chemical_data

This command:
1. Downloads drugs.zip from ClinPGx API
   - Extracts drugs.tsv (first 2 columns: PharmGKB Accession Id, Name)
   - Populates Chemical table with drug data for autocomplete
2. Downloads relationships.zip from ClinPGx API
   - Extracts relationships.tsv
   - Populates ChemicalRelationship table with full relationship data
"""

import os
import io
import csv
import zipfile
import requests
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from smart_search.models import Chemical, ChemicalRelationship


class Command(BaseCommand):
    help = 'Download and load ClinPGx chemical relationships data'

    def handle(self, *args, **options):
        """Main command execution."""
        self.stdout.write(self.style.SUCCESS('Starting ClinPGx chemical data load...'))

        # ============================================================
        # PART 1: Download and load drugs from drugs.zip
        # ============================================================
        self.stdout.write('\n' + '='*60)
        self.stdout.write('PART 1: Loading Chemical/Drug data from drugs.zip')
        self.stdout.write('='*60)

        drugs_url = 'https://api.clinpgx.org/v1/download/file/data/drugs.zip'
        self.stdout.write(f'Downloading from {drugs_url}...')

        try:
            response = requests.get(drugs_url, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Failed to download drugs.zip: {e}')

        # Extract drugs.tsv from the ZIP file
        self.stdout.write('Extracting drugs.tsv from ZIP file...')
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # List all files in the ZIP
                file_list = zip_file.namelist()
                self.stdout.write(f'Files in ZIP: {file_list}')

                # Look specifically for drugs.tsv
                tsv_file = 'drugs.tsv'
                if tsv_file not in file_list:
                    # Try to find it with different casing or path
                    found = False
                    for filename in file_list:
                        if filename.lower().endswith('drugs.tsv'):
                            tsv_file = filename
                            found = True
                            break

                    if not found:
                        raise CommandError(f'drugs.tsv not found in ZIP. Available files: {file_list}')

                self.stdout.write(f'Processing file: {tsv_file}')

                # Read the TSV file - only first two columns
                with zip_file.open(tsv_file) as f:
                    # Read with pandas, only first 2 columns
                    df_drugs = pd.read_csv(f, sep='\t', dtype=str, na_filter=False, usecols=[0, 1])

        except Exception as e:
            raise CommandError(f'Failed to extract drugs.zip file: {e}')

        self.stdout.write(f'Loaded {len(df_drugs)} drugs from file')
        self.stdout.write(f'Columns: {list(df_drugs.columns)}')

        # Rename columns to our standard names
        df_drugs.columns = ['chemical_id', 'chemical_name']

        # Remove duplicates based on chemical_id
        df_drugs = df_drugs.drop_duplicates(subset=['chemical_id'], keep='first')
        self.stdout.write(f'Found {len(df_drugs)} distinct chemicals after deduplication')

        # ============================================================
        # PART 2: Download and load relationships from relationships.zip
        # ============================================================
        self.stdout.write('\n' + '='*60)
        self.stdout.write('PART 2: Loading Chemical relationships from relationships.zip')
        self.stdout.write('='*60)

        # Download the relationships.zip file
        url = 'https://api.clinpgx.org/v1/download/file/data/relationships.zip'
        self.stdout.write(f'Downloading from {url}...')

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Failed to download relationships.zip: {e}')

        # Extract the ZIP file
        self.stdout.write('Extracting ZIP file...')
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # List all files in the ZIP
                file_list = zip_file.namelist()
                self.stdout.write(f'Files in ZIP: {file_list}')

                # Look specifically for relationships.tsv
                tsv_file = 'relationships.tsv'
                if tsv_file not in file_list:
                    # Try to find it with different casing or path
                    found = False
                    for filename in file_list:
                        if filename.lower().endswith('relationships.tsv'):
                            tsv_file = filename
                            found = True
                            break

                    if not found:
                        raise CommandError(f'relationships.tsv not found in ZIP. Available files: {file_list}')

                self.stdout.write(f'Processing file: {tsv_file}')

                # Read the TSV file
                with zip_file.open(tsv_file) as f:
                    # Read with pandas
                    df_full = pd.read_csv(f, sep='\t', dtype=str, na_filter=False)

        except Exception as e:
            raise CommandError(f'Failed to extract ZIP file: {e}')

        self.stdout.write(f'Loaded {len(df_full)} rows from relationships file')
        self.stdout.write(f'Columns: {list(df_full.columns)}')

        # Check actual column names and map them
        # Common variations: Entity1_type vs Entity 1_type vs entity1_type
        column_mapping = {}
        for col in df_full.columns:
            col_lower = col.lower().replace(' ', '_')
            if 'entity' in col_lower and '1' in col_lower:
                if 'type' in col_lower:
                    column_mapping['entity1_type'] = col
                elif 'id' in col_lower:
                    column_mapping['entity1_id'] = col
                elif 'name' in col_lower:
                    column_mapping['entity1_name'] = col
            elif 'entity' in col_lower and '2' in col_lower:
                if 'type' in col_lower:
                    column_mapping['entity2_type'] = col
                elif 'id' in col_lower:
                    column_mapping['entity2_id'] = col
                elif 'name' in col_lower:
                    column_mapping['entity2_name'] = col

        self.stdout.write(f'Column mapping: {column_mapping}')

        # Verify we have all required columns
        required_keys = ['entity1_type', 'entity1_id', 'entity1_name', 'entity2_type', 'entity2_id', 'entity2_name']
        missing_keys = [key for key in required_keys if key not in column_mapping]
        if missing_keys:
            raise CommandError(f'Missing required columns: {missing_keys}. Available columns: {list(df_full.columns)}')

        # ============================================================
        # PART 3: Load data into database
        # ============================================================
        self.stdout.write('\n' + '='*60)
        self.stdout.write('PART 3: Loading data into database')
        self.stdout.write('='*60)
        self.stdout.write('Loading data into database...')

        with transaction.atomic():
            # Clear existing data
            self.stdout.write('Clearing existing chemical data...')
            Chemical.objects.all().delete()
            ChemicalRelationship.objects.all().delete()

            # Load chemicals from drugs.tsv
            self.stdout.write('Loading Chemical table from drugs.tsv data...')
            chemicals_to_create = []
            for _, row in df_drugs.iterrows():
                chemicals_to_create.append(Chemical(
                    chemical_id=row['chemical_id'],
                    chemical_name=row['chemical_name']
                ))

            # Bulk create chemicals
            Chemical.objects.bulk_create(chemicals_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'Created {len(chemicals_to_create)} chemicals from drugs.tsv'))

            # Load full relationships
            self.stdout.write('Loading ChemicalRelationship table...')

            # Map additional column names for Evidence, Association, PK, PD
            optional_mapping = {}
            for col in df_full.columns:
                col_lower = col.lower()
                if 'evidence' in col_lower:
                    optional_mapping['evidence'] = col
                elif 'association' in col_lower:
                    optional_mapping['association'] = col
                elif col_lower == 'pk':
                    optional_mapping['pk'] = col
                elif col_lower == 'pd':
                    optional_mapping['pd'] = col

            relationships_to_create = []
            for _, row in df_full.iterrows():
                relationships_to_create.append(ChemicalRelationship(
                    entity1_id=row[column_mapping['entity1_id']],
                    entity1_name=row[column_mapping['entity1_name']],
                    entity1_type=row[column_mapping['entity1_type']],
                    entity2_id=row[column_mapping['entity2_id']],
                    entity2_name=row[column_mapping['entity2_name']],
                    entity2_type=row[column_mapping['entity2_type']],
                    evidence=row.get(optional_mapping.get('evidence', 'Evidence'), ''),
                    association=row.get(optional_mapping.get('association', 'Association'), ''),
                    pharmacokinetics=row.get(optional_mapping.get('pk', 'PK'), ''),
                    pharmacodynamics=row.get(optional_mapping.get('pd', 'PD'), '')
                ))

            # Bulk create relationships
            ChemicalRelationship.objects.bulk_create(relationships_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'Created {len(relationships_to_create)} relationships'))

        # Final statistics
        self.stdout.write(self.style.SUCCESS('\nDatabase loading complete!'))
        self.stdout.write(self.style.SUCCESS(f'Total chemicals: {Chemical.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total relationships: {ChemicalRelationship.objects.count()}'))
