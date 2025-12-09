# smart_search/management/commands/load_chemical_data.py
"""
Management command to download and load ClinPGx chemical relationships data.

Usage:
    python manage.py load_chemical_data

This command:
1. Downloads relationships.zip from ClinPGx API
2. Extracts and processes the data
3. Populates Chemical table with distinct chemicals
4. Populates ChemicalRelationship table with full data
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
                # Assuming the TSV file is named relationships.tsv or similar
                # List all files in the ZIP to find the right one
                file_list = zip_file.namelist()
                self.stdout.write(f'Files in ZIP: {file_list}')

                # Find the TSV file (usually relationships.tsv)
                tsv_file = None
                for filename in file_list:
                    if filename.endswith('.tsv') or filename.endswith('.txt'):
                        tsv_file = filename
                        break

                if not tsv_file:
                    raise CommandError('No TSV file found in relationships.zip')

                self.stdout.write(f'Processing file: {tsv_file}')

                # Read the TSV file
                with zip_file.open(tsv_file) as f:
                    # Read with pandas
                    df_full = pd.read_csv(f, sep='\t', dtype=str, na_filter=False)

        except Exception as e:
            raise CommandError(f'Failed to extract ZIP file: {e}')

        self.stdout.write(f'Loaded {len(df_full)} rows from relationships file')
        self.stdout.write(f'Columns: {list(df_full.columns)}')

        # Process chemicals for the Chemical table
        self.stdout.write('Processing chemicals...')

        # Filter Entity1_type == "Chemical"
        df_entity1 = df_full[df_full['Entity1_type'] == 'Chemical'][['Entity1_id', 'Entity1_name']].copy()
        df_entity1.columns = ['chemical_id', 'chemical_name']

        # Filter Entity2_type == "Chemical"
        df_entity2 = df_full[df_full['Entity2_type'] == 'Chemical'][['Entity2_id', 'Entity2_name']].copy()
        df_entity2.columns = ['chemical_id', 'chemical_name']

        # Concatenate both dataframes
        df_chemicals = pd.concat([df_entity1, df_entity2], ignore_index=True)

        # Keep only distinct values
        df_chemicals = df_chemicals.drop_duplicates(subset=['chemical_id', 'chemical_name'])

        self.stdout.write(f'Found {len(df_chemicals)} distinct chemicals')

        # Load data into database
        self.stdout.write('Loading data into database...')

        with transaction.atomic():
            # Clear existing data
            self.stdout.write('Clearing existing chemical data...')
            Chemical.objects.all().delete()
            ChemicalRelationship.objects.all().delete()

            # Load chemicals
            self.stdout.write('Loading Chemical table...')
            chemicals_to_create = []
            for _, row in df_chemicals.iterrows():
                chemicals_to_create.append(Chemical(
                    chemical_id=row['chemical_id'],
                    chemical_name=row['chemical_name']
                ))

            # Bulk create chemicals
            Chemical.objects.bulk_create(chemicals_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'Created {len(chemicals_to_create)} chemicals'))

            # Load full relationships
            self.stdout.write('Loading ChemicalRelationship table...')
            relationships_to_create = []
            for _, row in df_full.iterrows():
                relationships_to_create.append(ChemicalRelationship(
                    entity1_id=row['Entity1_id'],
                    entity1_name=row['Entity1_name'],
                    entity1_type=row['Entity1_type'],
                    entity2_id=row['Entity2_id'],
                    entity2_name=row['Entity2_name'],
                    entity2_type=row['Entity2_type'],
                    evidence=row.get('Evidence', ''),
                    association=row.get('Association', ''),
                    pharmacokinetics=row.get('PK', ''),
                    pharmacodynamics=row.get('PD', '')
                ))

            # Bulk create relationships
            ChemicalRelationship.objects.bulk_create(relationships_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'Created {len(relationships_to_create)} relationships'))

        # Final statistics
        self.stdout.write(self.style.SUCCESS('\nDatabase loading complete!'))
        self.stdout.write(self.style.SUCCESS(f'Total chemicals: {Chemical.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total relationships: {ChemicalRelationship.objects.count()}'))
