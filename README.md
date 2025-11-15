# CholesTrack - Genomic Data Management Platform

## Project Overview

CholesTrack is a Django-based web application for managing genomic data, particularly focused on cholestasis-related genetic analysis. The platform provides tools for patient sample management, BAM file region extraction, and gene-phenotype-disease association searches using the Human Phenotype Ontology (HPO).

**Technology Stack:**
- **Framework**: Django 5.2.8
- **Database**: PostgreSQL (configured via environment variables)
- **Web Server**: Gunicorn + Nginx (production)
- **Python Version**: 3.11+
- **External Tools**: Samtools (for BAM file manipulation)

## Project Structure

```
cholestrack/
├── cholestrack/               # Main Django project directory
│   ├── project/              # Project settings and configuration
│   ├── users/                # User authentication and management
│   ├── profile/              # User profile management
│   ├── samples/              # Patient sample tracking
│   ├── files/                # File upload and management
│   ├── home/                 # Homepage and dashboard
│   ├── region_selection/     # BAM region extraction tool
│   ├── smart_search/         # HPO gene/phenotype/disease search
│   ├── templates/            # Shared HTML templates
│   ├── staticfiles/          # Collected static files
│   ├── manage.py             # Django management script
│   └── requirements.txt      # Python dependencies
├── create_run_commands.sh    # Setup and management commands
└── .gitignore               # Git ignore rules
```

## Django Apps

### 1. **users** - User Management
- Custom user authentication and authorization
- Role-based access control (Admin, Clinician, Researcher, etc.)
- User approval workflow
- Login/logout/registration views

**Key Models:**
- Custom User model (extends Django's AbstractUser)
- User roles and permissions

**Important Commands:**
```bash
python manage.py createsuperuser
python manage.py approve_existing_users
```

### 2. **profile** - User Profiles
- Extended user information
- User preferences and settings
- Profile management views

**Key Models:**
- UserProfile (one-to-one with User)

### 3. **samples** - Sample Management
- Patient sample tracking
- Sample metadata and analysis status
- Sample filtering and search

**Key Models:**
- Patient
- Sample (linked to patients)

**Key Features:**
- Import samples from TSV files
- Filter samples by various criteria
- Track analysis status

**Important Commands:**
```bash
python manage.py import_data --samples /path/to/samples.tsv --files /path/to/files.tsv
```

### 4. **files** - File Management
- BAM file location tracking
- File type management (BAM, VCF, etc.)
- File upload and validation
- Integration with sample data

**Key Models:**
- AnalysisFileLocation

**Features:**
- Track file paths and metadata
- Link files to samples
- Support for multiple file types

### 5. **home** - Dashboard
- Landing page
- Quick access to key features
- User dashboard

### 6. **region_selection** - BAM Region Extraction
Extract specific genomic regions from BAM files.

**Key Models:**
- RegionExtractionJob

**Features:**
- **Flexible Region Specification:**
  - By gene name (e.g., BRCA1, ATP8B1)
  - By coordinates (chr:start-end)
- **Automatic Processing:** Uses samtools to extract regions
- **Temporary File Management:** Auto-cleanup after 10 minutes
- **Download Tracking:** Monitors file downloads
- **BAI Index Generation:** Automatically creates index files

**Important Commands:**
```bash
python manage.py cleanup_expired_extractions        # Clean up expired files
python manage.py cleanup_expired_extractions --dry-run
```

**Prerequisites:**
- Samtools must be installed and in PATH

**Typical Workflow:**
1. User selects sample and specifies region (gene or coordinates)
2. System creates extraction job
3. Samtools extracts region from BAM file
4. BAI index is generated
5. User downloads extracted BAM + BAI
6. Files auto-delete after download or 10 minutes

### 7. **smart_search** - HPO Gene Search
Gene-phenotype-disease association search using local HPO database.

**Key Models:**
- **HPOTerm**: HPO phenotype terms (e.g., HP:0000001)
- **Gene**: Gene information (Entrez ID, gene symbol)
- **Disease**: Disease information (OMIM, ORPHA, etc.)
- **GenePhenotypeAssociation**: Gene ↔ HPO term links
- **DiseasePhenotypeAssociation**: Disease ↔ HPO term links
- **GeneDiseaseAssociation**: Gene ↔ Disease links
- **GeneSearchQuery**: Cached search results (7-day expiration)

**Features:**
- **Local HPO Database:** No external API calls needed
- **Search by Gene Symbol:** Find phenotypes and diseases
- **Cached Results:** 7-day cache to reduce load
- **Pagination:** 10 results per page for phenotypes/diseases
- **Rich Data:**
  - HPO phenotype terms with definitions
  - Associated diseases from multiple databases
  - Direct links to HPO website

**Important Commands:**
```bash
# Load HPO data from GitHub (recommended)
python manage.py load_hpo_data

# Clear and reload all data
python manage.py load_hpo_data --clear

# Load from local files
python manage.py load_hpo_data \
    --genes-to-phenotype-file /path/to/genes_to_phenotype.txt \
    --genes-to-disease-file /path/to/genes_to_disease.txt \
    --phenotype-to-genes-file /path/to/phenotype_to_genes.txt \
    --disease-file /path/to/phenotype.hpoa

# Specify HPO release version
python manage.py load_hpo_data --release v2025-10-22

# Clear cached searches
python manage.py clear_search_cache --all
python manage.py clear_search_cache --gene BRCA1

# Test gene search
python manage.py test_gene_search --gene ATP8B1

# Fix database field for existing records
python manage.py fix_disease_database_field
python manage.py fix_disease_database_field --dry-run
```

**Data Sources:**
- HPO annotation files from: https://github.com/obophenotype/human-phenotype-ontology/releases

**File Formats:**
1. **genes_to_phenotype.txt**: Gene → Phenotype associations
   - Columns: entrez-gene-id, gene-symbol, HPO-ID, HPO-Name
2. **genes_to_disease.txt**: Gene → Disease associations
   - Columns: entrez-gene-id, gene-symbol, disease-name, disease-ID
3. **phenotype_to_genes.txt**: Phenotype → Gene associations
   - Columns: HPO-ID, HPO-Name, entrez-gene-id, gene-symbol
4. **phenotype.hpoa**: Disease → Phenotype associations
   - Columns: database-id, disease-name, HPO-ID, frequency, etc.

**Typical Workflow:**
1. Load HPO data into local database (run once, update monthly)
2. User searches for gene (e.g., "BRCA1")
3. System queries local database
4. Results cached for 7 days
5. User views paginated phenotypes and diseases

## Setup Instructions

### 1. Initial Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load HPO data (for smart_search)
python manage.py load_hpo_data
```

### 2. Environment Configuration

Create a `.env` file in `/home/user/cholestrack/cholestrack/` with:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DATABASE=cholestrack_db
POSTGRES_HOST=localhost
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_PORT=5432

# Optional: Region extraction settings
REGION_EXTRACTION_TEMP_DIR=/tmp/cholestrack_extractions
GENE_DATABASE_PATH=/path/to/gene_database.json
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Production Deployment

```bash
# Restart services after code changes
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## Common Management Commands

### Database Operations
```bash
# Show migrations status
python manage.py showmigrations

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Database shell
python manage.py dbshell
```

### Data Import/Export
```bash
# Import samples and files
python manage.py import_data \
    --samples /path/to/samples.tsv \
    --files /path/to/files.tsv \
    --clear  # Optional: clear existing data
```

### HPO Data Management
```bash
# Load HPO data (first time setup)
python manage.py load_hpo_data

# Update HPO data (monthly recommended)
python manage.py load_hpo_data --clear

# Clear search cache after HPO update
python manage.py clear_search_cache --all

# Test gene search
python manage.py test_gene_search --gene BRCA1
```

### File Cleanup
```bash
# Clean up expired region extraction files
python manage.py cleanup_expired_extractions

# Dry run to see what would be deleted
python manage.py cleanup_expired_extractions --dry-run

# Also clean downloaded files
python manage.py cleanup_expired_extractions --all-downloaded
```

### User Management
```bash
# Create superuser
python manage.py createsuperuser

# Approve existing users
python manage.py approve_existing_users
```

## Key Features

### 1. Role-Based Access Control
- User roles: Admin, Clinician, Researcher, Lab Technician
- Role confirmation required for access
- User approval workflow

### 2. Sample Management
- Track patient samples
- Link samples to analysis files
- Import data from TSV files
- Advanced filtering and search

### 3. BAM Region Extraction
- Extract genomic regions by gene name or coordinates
- Automatic samtools processing
- Temporary file management with auto-cleanup
- Download extracted BAM + BAI files

### 4. HPO Gene Search
- Local HPO database (no external API calls)
- Search genes for phenotypes and diseases
- Cached results (7-day expiration)
- Paginated results (10 per page)
- Links to external databases (HPO, OMIM, ORPHA)

### 5. File Management
- Track BAM, VCF, and other analysis files
- Link files to samples
- File metadata and validation

## Database Schema Highlights

### Core Entities
- **User**: Authentication and authorization
- **UserProfile**: Extended user information
- **Patient**: Patient records
- **Sample**: Sample metadata
- **AnalysisFileLocation**: File tracking

### HPO Entities (smart_search)
- **Gene**: Gene information (Entrez ID, symbol)
- **HPOTerm**: Phenotype terms
- **Disease**: Disease information (multiple databases)
- **Associations**: Gene-Phenotype, Disease-Phenotype, Gene-Disease

### Region Extraction
- **RegionExtractionJob**: Extraction job tracking

## API Endpoints

### Authentication
- `/login/` - User login
- `/logout/` - User logout
- `/register/` - User registration

### Samples
- `/samples/` - Sample list and search
- `/samples/<id>/` - Sample detail

### Files
- `/files/` - File list
- `/files/upload/` - File upload

### Region Selection
- `/region-selection/create/` - Create extraction job
- `/region-selection/job/<uuid>/` - Job detail
- `/region-selection/download/<uuid>/` - Download extracted files

### Smart Search
- `/smart-search/` - Search home
- `/smart-search/result/<id>/` - Search results (with pagination)
- `/smart-search/history/` - Search history

## Important Notes

### Production Considerations

1. **Template Changes**: Require gunicorn/nginx restart
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

2. **Static Files**: Collect after changes
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Cache**: Clear search cache after HPO data updates
   ```bash
   python manage.py clear_search_cache --all
   ```

4. **Cron Jobs**: Set up periodic cleanup
   ```bash
   # Add to crontab
   */5 * * * * cd /path/to/cholestrack && python manage.py cleanup_expired_extractions
   0 2 * * 0 cd /path/to/cholestrack && python manage.py load_hpo_data --clear  # Weekly HPO update
   ```

### Performance Optimization

1. **Database Indexes**: All key fields are indexed
2. **Query Optimization**: Use `select_related()` and `prefetch_related()`
3. **Caching**: Search results cached for 7 days
4. **Pagination**: Client-side pagination for large result sets

### Security

1. **Secret Key**: Keep in environment variables
2. **Debug Mode**: Set `DEBUG=False` in production
3. **Allowed Hosts**: Configure properly for production
4. **User Approval**: Required before access

### Data Sources and Citations

**Human Phenotype Ontology (HPO):**
- Website: https://hpo.jax.org/
- License: https://hpo.jax.org/app/license
- Citation: Köhler S, et al. The Human Phenotype Ontology in 2024: phenotypes around the world. Nucleic Acids Res. 2024 Jan 5;52(D1):D1333-D1346.

## Troubleshooting

### Template Changes Not Appearing
**Problem**: HTML changes don't show in browser
**Solutions**:
1. Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
2. Restart gunicorn: `sudo systemctl restart gunicorn`
3. Restart nginx: `sudo systemctl restart nginx`
4. Clear browser cache
5. Try incognito/private window

### Gene Not Found in HPO Search
**Problem**: "Gene not found in local HPO database"
**Solution**: Load HPO data
```bash
python manage.py load_hpo_data
```

### Diseases Not Showing
**Problem**: Phenotypes show but no diseases
**Solutions**:
1. Verify data loaded correctly:
   ```bash
   python manage.py test_gene_search --gene BRCA1
   ```
2. Fix database field if needed:
   ```bash
   python manage.py fix_disease_database_field
   ```
3. Clear search cache:
   ```bash
   python manage.py clear_search_cache --all
   ```

### Region Extraction Fails
**Problem**: BAM extraction job fails
**Solutions**:
1. Verify samtools is installed: `samtools --version`
2. Check BAM file exists and is readable
3. Verify gene coordinates are valid
4. Check disk space in temp directory

### Database Connection Errors
**Problem**: Can't connect to PostgreSQL
**Solutions**:
1. Verify PostgreSQL is running
2. Check `.env` file has correct credentials
3. Verify database exists
4. Check network connectivity

## Development Workflow

### Making Changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** to code/templates

3. **Test locally**:
   ```bash
   python manage.py runserver
   ```

4. **Create migrations** if models changed:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **After merge to main**, update production:
   ```bash
   git checkout main
   git pull origin main
   python manage.py migrate
   python manage.py collectstatic --noinput
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

### Testing

```bash
# Run Django tests
python manage.py test

# Run specific app tests
python manage.py test smart_search

# Test specific functionality
python manage.py test_gene_search --gene ATP8B1
```

## Support and Documentation

### App-Specific READMEs
- `/cholestrack/smart_search/README.md` - HPO search detailed docs
- `/cholestrack/region_selection/README.md` - Region extraction detailed docs

### External Resources
- Django Documentation: https://docs.djangoproject.com/
- HPO Website: https://hpo.jax.org/
- Samtools Documentation: http://www.htslib.org/doc/samtools.html

## License

[Add project license information here]

---

**Last Updated**: 2025-11-15
**Django Version**: 5.2.8
**Python Version**: 3.11+
