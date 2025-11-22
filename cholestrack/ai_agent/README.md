# AI Genomic Analysis Agent

An AI-powered assistant for analyzing genomic variant data using Claude API with data anonymization.

## Features

### Core Capabilities
- **Statistical Analysis**: Summary statistics, variant counts, quality metrics
- **Variant Interpretation**: Explain significance of genetic variants
- **Comparative Analysis**: Compare variants across samples
- **Genetic Model Filtering**: Filter by inheritance patterns (AD, AR, compound het)
- **Custom Queries**: Natural language questions about variant data
- **Report Generation**: HTML, CSV, Excel formats

### Key Components

1. **Chat Interface** (`chat_interface.html`)
   - Modern, interactive chat UI
   - Conversation history sidebar
   - Real-time messaging
   - Quick action buttons

2. **Claude API Integration** (`claude_client.py`)
   - Anthropic Claude API wrapper
   - Automatic data anonymization
   - Token usage tracking
   - Error handling

3. **Data Parsers** (`data_parser.py`)
   - TSV file parser for _rawdata.txt files
   - Multi-sample comparison tools
   - Quality filtering
   - Frequency filtering

4. **Genetic Models** (`genetic_models.py`)
   - Autosomal Dominant filtering
   - Autosomal Recessive filtering
   - Compound Heterozygous detection
   - Inheritance pattern annotation

5. **Background Tasks** (`tasks.py`)
   - Celery integration for long-running analyses
   - Statistical analysis jobs
   - Genetic model filtering jobs
   - Comparative analysis jobs

6. **Report Generation** (`report_generator.py`)
   - Professional HTML reports
   - CSV/Excel exports
   - Summary statistics displays

## Setup Instructions

### 1. Install Dependencies

Add to `requirements.txt`:
```
anthropic==0.21.3
pandas==2.1.4
numpy==1.26.3
openpyxl==3.1.2
celery==5.3.6
redis==5.0.1
```

Install:
```bash
pip install anthropic pandas numpy openpyxl celery redis
```

### 2. Configure Settings

Add to `cholestrack/settings.py`:

```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'ai_agent',
]

# AI Agent Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = 'claude-3-5-sonnet-20241022'  # or claude-3-opus-20240229

# Celery Configuration (if not already configured)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

### 3. Add URL Routes

Update `cholestrack/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('ai-agent/', include('ai_agent.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py makemigrations ai_agent
python manage.py migrate ai_agent
```

### 5. Set Environment Variable

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or add to `.env` file (if using python-decouple):
```
ANTHROPIC_API_KEY=your-api-key-here
```

### 6. Start Celery Worker (for background tasks)

```bash
celery -A cholestrack worker -l info
```

### 7. Access the AI Agent

Navigate to: `http://your-domain/ai-agent/`

## Usage Examples

### Example 1: Statistical Summary
```
User: "What samples are available for analysis?"
AI: Lists available samples with anonymized IDs

User: "Give me a statistical summary for SAMPLE_ABC123"
AI: Provides variant counts, quality metrics, impact distribution
```

### Example 2: Genetic Model Filtering
```
User: "Filter variants for autosomal dominant inheritance in sample XYZ"
AI: Applies AD model and returns filtered variants

User: "Generate an HTML report for these results"
AI: Creates analysis job, generates report, provides download link
```

### Example 3: Comparative Analysis
```
User: "Compare variants between samples A, B, and C"
AI: Identifies shared and unique variants

User: "Export shared variants to Excel"
AI: Generates Excel file with comparative data
```

## Data Privacy & Security

### Anonymization Features
- Sample IDs are hashed before sending to Claude API
- Patient identifiers (emails, phone numbers, dates) are redacted
- File paths are removed from data
- Only variant data (non-PII) is included in API calls

### Anonymization Example
```
Real Sample ID: "PATIENT_JOHN_DOE_2024"
Sent to API:    "SAMPLE_A7B8C9D0"
```

### What Gets Anonymized
✅ Sample IDs → Hashed IDs
✅ Email addresses → [EMAIL_REDACTED]
✅ Phone numbers → [PHONE_REDACTED]
✅ Dates → [DATE_REDACTED]
✅ File paths → [FILE_PATH_REDACTED]

### What is NOT Anonymized (Safe to Send)
- Chromosome positions (chr1:12345)
- Gene names (BRCA1, TP53)
- Variant alleles (C>T)
- Impact annotations (HIGH, MODERATE)
- Population frequencies (gnomAD AF)

## Architecture

```
┌─────────────────┐
│  Chat UI        │
│  (Frontend)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Django Views   │
│  (views.py)     │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌────────┐  ┌──────────┐
│ Claude │  │  Celery  │
│  API   │  │  Tasks   │
└────────┘  └─────┬────┘
                  │
                  ▼
          ┌───────────────┐
          │ Data Parsers  │
          │ Genetic Models│
          │ Report Gen    │
          └───────────────┘
```

## File Type Assumptions

The system expects TSV files (_rawdata.txt) with these columns:
- **Required**: CHROM, POS, REF, ALT
- **Recommended**: GENE, GT, IMPACT, CONSEQUENCE, gnomAD_AF, QUAL, DP, GQ

## Troubleshooting

### API Key Not Found
```
Error: Anthropic API key not configured
Solution: Set ANTHROPIC_API_KEY environment variable
```

### Celery Not Running
```
Error: Analysis jobs stuck in PENDING
Solution: Start Celery worker: celery -A cholestrack worker -l info
```

### No Data Files Found
```
Error: No data files found for samples
Solution: Ensure AnalysisFileLocation records exist with file_type='TSV'
```

## RBAC Integration

The AI Agent respects the existing RBAC system:
- Requires `@login_required`
- Requires `@role_confirmed_required`
- Only shows samples user has access to
- Maintains audit trail via ChatSession/ChatMessage models

## Future Enhancements

Potential improvements:
- [ ] Support for VCF file parsing (in addition to TSV)
- [ ] Visualization charts (matplotlib integration)
- [ ] Multi-modal analysis (combine with BAM QC data)
- [ ] Custom annotation databases
- [ ] Batch analysis workflows
- [ ] API endpoints for programmatic access
- [ ] Local LLM deployment option

## Support

For questions or issues, contact the development team or create a ticket in the project management system.
