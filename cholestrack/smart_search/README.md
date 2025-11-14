# Smart Search - HPO Local Database

This app provides gene search functionality using a local Human Phenotype Ontology (HPO) database.

## Overview

The Smart Search app allows users to search for genes and retrieve associated:
- **HPO Phenotype Terms**: Clinical phenotypes associated with the gene
- **Diseases**: Diseases linked to the gene through HPO annotations

All data is stored locally in the PostgreSQL database, eliminating the need for external API calls.

## Database Models

The app uses the following models to store HPO data:

- **HPOTerm**: HPO phenotype terms (e.g., HP:0000001)
- **Gene**: Gene information (NCBI Entrez ID and gene symbol)
- **Disease**: Disease information from various databases (OMIM, ORPHA, etc.)
- **GenePhenotypeAssociation**: Links genes to HPO terms
- **DiseasePhenotypeAssociation**: Links diseases to HPO terms
- **GeneDiseaseAssociation**: Links genes to diseases (derived from shared phenotypes)

## Setup Instructions

### 1. Run Migrations

First, create and apply the database migrations:

```bash
cd cholestrack
python manage.py makemigrations smart_search
python manage.py migrate smart_search
```

### 2. Load HPO Data

Download and load HPO annotation data into the database:

```bash
# Load data from HPO GitHub (recommended)
python manage.py load_hpo_data

# Or load from local files
python manage.py load_hpo_data \
    --genes-file /path/to/genes_to_phenotype.txt \
    --disease-file /path/to/phenotype.hpoa

# Clear existing data and reload
python manage.py load_hpo_data --clear
```

### Command Options

- `--clear`: Clear existing HPO data before loading
- `--genes-file PATH`: Path to local genes_to_phenotype.txt file
- `--disease-file PATH`: Path to local phenotype.hpoa file
- `--genes-url URL`: Custom URL for genes_to_phenotype.txt (default: HPO GitHub latest release)
- `--disease-url URL`: Custom URL for phenotype.hpoa (default: HPO GitHub latest release)
- `--skip-genes`: Skip loading gene-phenotype data
- `--skip-diseases`: Skip loading disease-phenotype data

### 3. Verify Data

After loading, verify the data was imported correctly:

```python
from smart_search.api_utils import get_hpo_database_stats

stats = get_hpo_database_stats()
print(stats)
# Expected output:
# {
#     'hpo_terms': 15000+,
#     'genes': 4000+,
#     'diseases': 7000+,
#     'gene_phenotype_associations': 120000+,
#     'disease_phenotype_associations': 250000+,
#     'gene_disease_associations': 30000+
# }
```

## Data Sources

The HPO annotation files are downloaded from the official HPO GitHub repository:
- https://github.com/obophenotype/human-phenotype-ontology/releases

### Files Used

1. **genes_to_phenotype.txt**
   - Format: Tab-separated values
   - Columns: Entrez Gene ID, Gene Symbol, HPO Term Name, HPO Term ID
   - Contains gene-to-phenotype associations

2. **phenotype.hpoa**
   - Format: Tab-separated values
   - Columns: DatabaseID, DiseaseName, HPO_ID, Frequency, etc.
   - Contains disease-to-phenotype associations

## Usage Example

### Searching for a Gene

```python
from smart_search.api_utils import fetch_gene_data

# Search for ATP8B1 gene
results = fetch_gene_data('ATP8B1')

# Access phenotypes
for phenotype in results['phenotypes']:
    print(f"{phenotype['hpo_id']}: {phenotype['name']}")

# Access diseases
for disease in results['diseases']:
    print(f"{disease['disease_id']}: {disease['disease_name']}")
```

### Web Interface

Users can access the search interface at:
```
http://your-domain/smart-search/
```

Features:
- Search by gene symbol
- View associated phenotypes and diseases
- Search history
- Cached results (7-day expiration)

## Maintenance

### Updating HPO Data

HPO releases new data monthly. To update:

```bash
# Clear old data and load new data
python manage.py load_hpo_data --clear
```

### Database Performance

The models include indexes on frequently queried fields:
- Gene symbol and Entrez ID
- HPO term ID
- Disease database ID
- Association foreign keys

For large datasets, consider:
- Regular database vacuuming
- Index maintenance
- Query optimization with `select_related()` and `prefetch_related()`

## Troubleshooting

### "Gene not found" Error

If you get this error when searching:
```
Gene "ATP8B1" not found in local HPO database.
Please run "python manage.py load_hpo_data" to populate the database.
```

**Solution**: Run the `load_hpo_data` command to populate the database.

### Download Fails

If the automatic download fails:
1. Manually download files from: https://github.com/obophenotype/human-phenotype-ontology/releases/latest
2. Load using local files:
   ```bash
   python manage.py load_hpo_data \
       --genes-file /path/to/genes_to_phenotype.txt \
       --disease-file /path/to/phenotype.hpoa
   ```

### Slow Queries

If searches are slow:
1. Verify database indexes exist:
   ```bash
   python manage.py sqlmigrate smart_search 0001
   ```
2. Analyze query performance:
   ```python
   from django.db import connection
   from django.test.utils import override_settings

   @override_settings(DEBUG=True)
   def debug_query():
       # Your query here
       print(len(connection.queries))
       for query in connection.queries:
           print(query['sql'])
   ```

## Architecture

```
smart_search/
├── models.py              # Database models (HPOTerm, Gene, Disease, etc.)
├── api_utils.py           # HPOLocalClient for querying local database
├── views.py               # Django views for web interface
├── forms.py               # Gene search form
├── urls.py                # URL routing
├── admin.py               # Django admin configuration
├── management/
│   └── commands/
│       └── load_hpo_data.py  # Management command to load HPO data
└── README.md              # This file
```

## API Reference

### `fetch_gene_data(gene_symbol: str) -> Dict`

Main function to search for gene data.

**Parameters:**
- `gene_symbol`: Gene symbol (e.g., 'ATP8B1', 'BRCA1')

**Returns:**
```python
{
    'phenotypes': [
        {
            'hpo_id': 'HP:0000001',
            'name': 'Phenotype name',
            'definition': 'Description...'
        },
        ...
    ],
    'diseases': [
        {
            'disease_id': 'OMIM:123456',
            'disease_name': 'Disease name',
            'database': 'OMIM'
        },
        ...
    ],
    'gene_info': {
        'gene_symbol': 'ATP8B1',
        'entrez_id': 5205
    },
    'error': 'Error message (if any)'
}
```

### `get_hpo_database_stats() -> Dict`

Get statistics about the local HPO database.

**Returns:**
```python
{
    'hpo_terms': 15000,
    'genes': 4000,
    'diseases': 7000,
    'gene_phenotype_associations': 120000,
    'disease_phenotype_associations': 250000,
    'gene_disease_associations': 30000
}
```

## License

This app uses data from the Human Phenotype Ontology (HPO):
- HPO Website: https://hpo.jax.org/
- HPO License: https://hpo.jax.org/app/license

Please cite HPO in any publications using this data:
> Köhler S, et al. The Human Phenotype Ontology in 2024: phenotypes around the world.
> Nucleic Acids Res. 2024 Jan 5;52(D1):D1333-D1346.
