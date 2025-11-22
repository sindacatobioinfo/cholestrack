# CholesTrack - Genomic Data Management Platform

## Project Overview

CholesTrack is a Django-based web application for managing genomic data, particularly focused on cholestasis-related genetic analysis. The platform provides tools for patient sample management, BAM file region extraction, and gene-phenotype-disease association searches using the Human Phenotype Ontology (HPO).

**Technology Stack:**
- **Framework**: Django 5.2.8
- **Database**: PostgreSQL (configured via environment variables)
- **Web Server**: Gunicorn + Nginx (production)
- **Python Version**: 3.11+
- **External Tools**: Samtools (for BAM file manipulation)
- **AI Services**: Google Gemini API (for AI genomic analysis agent)
- **Task Queue**: Celery + Redis (for background processing)

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
│   ├── ai_agent/             # AI genomic analysis agent
│   ├── templates/            # Shared HTML templates
│   ├── staticfiles/          # Collected static files
│   ├── manage.py             # Django management script
│   ├── celery_app.py         # Celery configuration for background tasks
│   └── requirements.txt      # Python dependencies
├── create_run_commands.sh    # Setup and management commands
└── .gitignore               # Git ignore rules
```

## Django Apps

### 1. **users** - User Management & RBAC
- Custom user authentication and authorization
- **Role-Based Access Control (RBAC)** - Fully implemented and enforced
- User approval workflow with email verification
- Login/logout/registration views

**Key Models:**
- `User` - Django's built-in User model
- `EmailVerification` - Email confirmation tracking
- `UserRole` - Role assignment and confirmation

**User Roles (Hierarchy):**
1. **Administrator** (`ADMIN`) - Full system access including Django admin
2. **Data Manager** (`DATA_MANAGER`) - Create, edit, view, and delete data
3. **Researcher** (`RESEARCHER`) - Create, edit, and view (no delete)
4. **Clinician** (`CLINICIAN`) - View and download only (read-only)

**RBAC Features:**
- View-level enforcement via `@role_required` decorator
- Template-level permission checks via `user.role.can_*()` methods
- Automated test suite for permission verification (`users/test_rbac.py`)
- Admin approval required for all role assignments

**Permission Matrix:**
| Action | ADMIN | DATA_MANAGER | RESEARCHER | CLINICIAN |
|--------|:-----:|:------------:|:----------:|:---------:|
| Create/Edit Patients | ✅ | ✅ | ✅ | ❌ |
| Delete Patients | ✅ | ✅ | ❌ | ❌ |
| Register/Edit Files | ✅ | ✅ | ✅ | ❌ |
| Delete Files | ✅ | ✅ | ❌ | ❌ |
| View/Download | ✅ | ✅ | ✅ | ✅ |

**Important Commands:**
```bash
python manage.py createsuperuser
python manage.py approve_existing_users
python manage.py test users.test_rbac  # Run RBAC tests
```

**See Also:**
- `RBAC_PERMISSIONS_DOCUMENTATION.md` - Complete RBAC reference
- `RBAC_IMPLEMENTATION_FIXES.md` - Implementation guide

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

### 8. **ai_agent** - AI Genomic Analysis Agent
AI-powered assistant for analyzing variant data using natural language with Google Gemini API.

**Key Models:**
- **ChatSession**: Conversation tracking with token usage
- **ChatMessage**: Individual messages (user/assistant/system)
- **AnalysisJob**: Background analysis tasks with results

**Features:**
- **Natural Language Interface:** Chat with AI to analyze genomic data
- **Statistical Analysis:** Variant counts, quality metrics, impact distribution
- **Genetic Model Filtering:**
  - Autosomal dominant (heterozygous, rare variants)
  - Autosomal recessive (homozygous alternate)
  - Compound heterozygous (multiple hits per gene)
- **Comparative Analysis:** Compare variants across multiple samples
- **Custom Queries:** Ask questions about variant data in plain English
- **Report Generation:** Create HTML, CSV, or Excel reports
- **Background Processing:** Long-running analyses via Celery
- **Data Privacy:** Automatic anonymization before sending to Gemini API

**Data Anonymization:**
- Sample IDs → Hashed (e.g., "SAMPLE_A7B8C9D0")
- Email addresses → `[EMAIL_REDACTED]`
- Phone numbers → `[PHONE_REDACTED]`
- Dates → `[DATE_REDACTED]`
- File paths removed
- Only variant data (non-PII) sent to API

**Important Commands:**
```bash
# Run Celery worker (required for background tasks)
cd /home/burlo/cholestrack/cholestrack
celery -A celery_app worker -l info

# Run migrations
python manage.py makemigrations ai_agent
python manage.py migrate

# Test import
python manage.py shell
>>> from ai_agent.gemini_client import GeminiAnalysisClient
>>> client = GeminiAnalysisClient()
```

**Prerequisites:**
- Google Gemini API key (free tier available at https://aistudio.google.com/app/apikey)
- Redis server running (for Celery task queue)
- Celery worker running (for background tasks)

**Environment Variables:**
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
export GEMINI_MODEL="gemini-1.5-flash"  # Optional, defaults to gemini-1.5-flash
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

**Typical Workflow:**
1. User opens AI Agent from dashboard
2. User asks question: "Show me statistical summary for sample XYZ"
3. AI Agent queries variant data (TSV files)
4. For quick queries: Immediate response
5. For complex analysis: Background Celery job created
6. User receives results with option to download reports
7. All patient data anonymized before API calls

**Analysis Types:**
- **Statistical:** Summary statistics, variant counts, quality metrics
- **Genetic Model:** Filter by inheritance pattern (AD/AR/Compound Het)
- **Comparative:** Find shared/unique variants across samples
- **Variant Interpretation:** Explain significance of specific variants

**API Endpoints:**
- `/ai-agent/` - Chat interface
- `/ai-agent/send-message/` - Send message to AI (AJAX)
- `/ai-agent/start-job/` - Start background analysis job
- `/ai-agent/job-status/<uuid>/` - Check job status
- `/ai-agent/download-report/<uuid>/` - Download generated report

**See Also:**
- `/cholestrack/ai_agent/README.md` - Detailed documentation
- `/cholestrack/ai_agent/INSTALLATION.md` - Setup guide

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

# AI Agent settings
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-1.5-flash

# Celery settings (for AI Agent background tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Run Development Server

**For AI Agent features, you need 3 processes running:**

```bash
# Terminal 1: Redis (if not running as service)
redis-server

# Terminal 2: Celery Worker
cd /home/burlo/cholestrack/cholestrack
celery -A celery_app worker -l info

# Terminal 3: Django Development Server
python manage.py runserver
```

**Without AI Agent (basic setup):**
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

### Celery & AI Agent
```bash
# Start Celery worker (required for AI Agent)
cd /home/burlo/cholestrack/cholestrack
celery -A celery_app worker -l info

# Monitor Celery tasks (optional - requires flower)
pip install flower
celery -A celery_app flower

# Test Gemini API connection
python manage.py shell
>>> from ai_agent.gemini_client import GeminiAnalysisClient
>>> client = GeminiAnalysisClient()
>>> print("API key configured!" if client.api_key else "API key missing!")
```

## Key Features

### 1. Role-Based Access Control (RBAC)
**Status:** ✅ Fully Implemented and Enforced

- **Four-tier user hierarchy:** Administrator, Data Manager, Researcher, Clinician
- **Email verification:** Required before account activation
- **Admin approval:** All role assignments must be confirmed by administrator
- **View-level enforcement:** `@role_required` decorators protect sensitive operations
- **Template-level checks:** UI adapts to user permissions
- **Automated testing:** Comprehensive test suite verifies RBAC enforcement

**Security:**
- Clinicians have read-only access (view and download only)
- Researchers can create and edit but cannot delete
- Data Managers have full CRUD access
- Administrators have complete system control

**Documentation:** See `RBAC_PERMISSIONS_DOCUMENTATION.md` and `RBAC_IMPLEMENTATION_FIXES.md`

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

### 6. AI Genomic Analysis Agent
- Natural language interface powered by Google Gemini API
- Statistical analysis of variant data (TSV files)
- Genetic model filtering (AD, AR, compound heterozygous)
- Comparative analysis across multiple samples
- Automated report generation (HTML, CSV, Excel)
- Background job processing with Celery
- Data privacy through automatic anonymization
- Real-time chat interface with conversation history

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

### AI Agent (ai_agent)
- **ChatSession**: Conversation tracking with token usage
- **ChatMessage**: Individual messages (user/assistant/system)
- **AnalysisJob**: Background analysis tasks with results

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

### AI Agent
- `/ai-agent/` - Chat interface
- `/ai-agent/send-message/` - Send message to AI (AJAX)
- `/ai-agent/new-session/` - Create new chat session
- `/ai-agent/session/<uuid>/` - Load specific session
- `/ai-agent/start-job/` - Start background analysis job (AJAX)
- `/ai-agent/job-status/<uuid>/` - Check job status (AJAX)
- `/ai-agent/download-report/<uuid>/` - Download generated report

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
- `/cholestrack/ai_agent/README.md` - AI Agent detailed documentation
- `/cholestrack/ai_agent/INSTALLATION.md` - AI Agent installation guide

### External Resources
- Django Documentation: https://docs.djangoproject.com/
- HPO Website: https://hpo.jax.org/
- Samtools Documentation: http://www.htslib.org/doc/samtools.html

## License

[Add project license information here]

---

**Last Updated**: 2024-11-22
**Django Version**: 5.2.8
**Python Version**: 3.11+
**AI Features**: Google Gemini API + Celery Background Tasks
