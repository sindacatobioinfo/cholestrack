# Region Selection App

Django app for extracting specific genomic regions from BAM files.

## Features

- **Flexible Region Specification**: Users can specify regions using either:
  - Gene names (e.g., BRCA1, TP53)
  - Genomic coordinates (chromosome:start-end)

- **Automatic Processing**: Uses samtools to extract regions from BAM files
- **Index Generation**: Automatically creates BAM index files (.bai) for extracted regions
- **Temporary Storage**: Files are stored temporarily and auto-deleted after download or expiration
- **Expiration Management**: Files expire 10 minutes after completion if not downloaded

## Installation

### Prerequisites

1. **Samtools** must be installed and available in PATH:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install samtools

   # macOS
   brew install samtools

   # Verify installation
   samtools --version
   ```

2. Add app to Django settings:
   ```python
   INSTALLED_APPS = [
       ...
       'region_selection',
   ]
   ```

3. Configure URLs in project/urls.py:
   ```python
   urlpatterns = [
       ...
       path('region-selection/', include('region_selection.urls')),
   ]
   ```

4. Run migrations:
   ```bash
   python manage.py migrate region_selection
   ```

## Configuration

Add these settings to your `settings.py`:

```python
# Temporary directory for extracted BAM files
REGION_EXTRACTION_TEMP_DIR = env(
    'REGION_EXTRACTION_TEMP_DIR',
    default='/tmp/cholestrack_extractions'
)

# Optional: Path to gene annotation database (JSON format)
GENE_DATABASE_PATH = env('GENE_DATABASE_PATH', default=None)
```

### Gene Database Format

If you want to support more genes beyond the built-in list, create a JSON file:

```json
{
    "BRCA1": {
        "chromosome": "chr17",
        "start": 43044295,
        "end": 43125483
    },
    "TP53": {
        "chromosome": "chr17",
        "start": 7661779,
        "end": 7687550
    }
}
```

Then set `GENE_DATABASE_PATH` in your environment or settings.

## Usage

### Web Interface

1. Navigate to `/region-selection/create/`
2. Enter:
   - Sample ID (must have an associated BAM file)
   - Region specification:
     - **Gene Name**: Enter gene symbol (e.g., BRCA1)
     - **Coordinates**: Enter chromosome, start, and end positions
3. Submit to create extraction job
4. Job is processed automatically
5. Download extracted BAM file (available for 10 minutes)

### API Endpoints

- `GET /region-selection/` - List all jobs
- `GET /region-selection/create/` - Create new extraction job
- `GET /region-selection/job/<job_id>/` - View job details
- `GET /region-selection/job/<job_id>/download/` - Download extracted file
- `GET /region-selection/api/job/<job_id>/status/` - Get job status (JSON)

## Automatic Cleanup

### Management Command

Run periodic cleanup of expired files:

```bash
# Dry run (shows what would be deleted)
python manage.py cleanup_expired_extractions --dry-run

# Clean up expired files
python manage.py cleanup_expired_extractions

# Clean up downloaded files as well
python manage.py cleanup_expired_extractions --all-downloaded
```

### Cron Setup

Add to crontab to run every 5 minutes:

```bash
*/5 * * * * cd /path/to/cholestrack && /path/to/venv/bin/python manage.py cleanup_expired_extractions >> /var/log/cholestrack_cleanup.log 2>&1
```

## Architecture

### Models

**RegionExtractionJob**:
- Tracks extraction requests
- Stores region specifications (gene or coordinates)
- Manages file paths and cleanup
- Auto-expires after 10 minutes

### Workflow

1. User submits extraction request
2. If gene name provided, convert to coordinates using gene database
3. Create temp directory for job
4. Run samtools to extract region:
   ```bash
   samtools view -b -h input.bam "chr1:100000-200000" > output.bam
   ```
5. Create BAM index:
   ```bash
   samtools index output.bam
   ```
6. Set expiration timestamp (current time + 10 minutes)
7. User downloads file
8. File marked as downloaded
9. Cleanup command removes temp files

### Security

- Uses Django's `role_confirmed_required` decorator
- Validates sample IDs against database
- Prevents directory traversal attacks
- Limits file access to job owner only
- Auto-cleanup prevents disk space issues

## Built-in Gene Database

The app includes coordinates for common genes:

- BRCA1, BRCA2 (breast cancer)
- TP53 (tumor suppressor)
- CFTR (cystic fibrosis)
- APOE (Alzheimer's)
- EGFR, KRAS, MYC (oncogenes)
- HBB (hemoglobin beta)
- DMD (muscular dystrophy)

To add more genes, use the `GENE_DATABASE_PATH` configuration.

## Troubleshooting

### "Samtools not found"
- Install samtools: `sudo apt-get install samtools`
- Verify PATH: `which samtools`

### "BAM file not found"
- Check that sample_id exists in database
- Verify file_type is 'BAM'
- Check that is_active is True
- Verify file path is correct on server

### "Extraction produced no output"
- Region may be empty (no reads in that region)
- Check chromosome naming (chr1 vs 1)
- Verify coordinates are valid for reference genome

### "Permission denied" on temp directory
- Create directory: `mkdir -p /tmp/cholestrack_extractions`
- Set permissions: `chmod 755 /tmp/cholestrack_extractions`
- Or configure different directory in settings

## Development

### Running Tests

```bash
python manage.py test region_selection
```

### Adding New Features

- **Gene name service**: Integrate with Ensembl or MyGene.info API
- **Background processing**: Use Celery for async extraction
- **Progress tracking**: Add WebSocket support for real-time updates
- **Batch extraction**: Support multiple regions at once
- **Format conversion**: Support CRAM to BAM conversion

## License

Part of the Cholestrack project.
