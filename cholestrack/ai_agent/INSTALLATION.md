# AI Agent Installation Guide

## Step-by-Step Installation

### Step 1: Add App to INSTALLED_APPS

Edit `cholestrack/settings.py` and add `'ai_agent'` to INSTALLED_APPS:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Existing apps
    'users',
    'samples',
    'files',
    'analysis_workflows',
    'region_selection',
    'profile',
    # NEW: AI Agent
    'ai_agent',  # <-- Add this line
]
```

### Step 2: Add AI Agent Configuration

Add to `cholestrack/settings.py` (at the end of the file):

```python
# =============================================================================
# AI AGENT CONFIGURATION
# =============================================================================

# Anthropic Claude API
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Claude model to use (options: claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-haiku-20240307)
CLAUDE_MODEL = 'claude-3-5-sonnet-20241022'

# Celery configuration for background tasks
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
```

### Step 3: Create Celery App

Create file `cholestrack/celery.py` (if it doesn't exist):

```python
"""
Celery configuration for cholestrack project.
"""

import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cholestrack.settings')

app = Celery('cholestrack')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

Update `cholestrack/__init__.py` to load Celery app:

```python
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### Step 4: Add URL Routes

Edit `cholestrack/urls.py` and add AI Agent URLs:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # ... existing URL patterns
    path('ai-agent/', include('ai_agent.urls')),  # <-- Add this line
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### Step 5: Install Python Dependencies

Create/update `requirements.txt`:

```txt
# Existing dependencies...

# AI Agent dependencies
anthropic==0.21.3
pandas==2.1.4
numpy==1.26.3
openpyxl==3.1.2
celery==5.3.6
redis==5.0.1
```

Install dependencies:

```bash
pip install anthropic pandas numpy openpyxl celery redis
```

### Step 6: Install and Start Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should output: PONG
```

### Step 7: Set Environment Variables

Create `.env` file in project root (or export in shell):

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

If using `.env` file, install python-decouple:

```bash
pip install python-decouple
```

And update `settings.py`:

```python
from decouple import config

ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
```

### Step 8: Run Migrations

```bash
python manage.py makemigrations ai_agent
python manage.py migrate
```

### Step 9: Create Superuser (if needed)

```bash
python manage.py createsuperuser
```

### Step 10: Start Development Services

Terminal 1 - Django Server:
```bash
python manage.py runserver
```

Terminal 2 - Celery Worker:
```bash
celery -A cholestrack worker -l info
```

Optional - Celery Beat (for periodic tasks):
```bash
celery -A cholestrack beat -l info
```

### Step 11: Add Dashboard Button

Edit your dashboard/home template (e.g., `templates/home.html` or `templates/dashboard.html`):

```html
<!-- Add this button to your dashboard -->
<a href="{% url 'ai_agent:chat_interface' %}" class="btn btn-primary">
    <i class="fas fa-robot"></i> AI Analysis Agent
</a>
```

Or add to navigation bar in `base.html`:

```html
<li class="nav-item">
    <a class="nav-link" href="{% url 'ai_agent:chat_interface' %}">
        <i class="fas fa-robot"></i> AI Agent
    </a>
</li>
```

### Step 12: Configure File Type Mapping

The AI Agent expects TSV files to be marked with `file_type='TSV'` in the `AnalysisFileLocation` model.

If your _rawdata.txt files are currently stored with a different file_type, you have two options:

**Option A: Update existing records**
```python
# In Django shell or migration
from files.models import AnalysisFileLocation

AnalysisFileLocation.objects.filter(
    file_location__endswith='_rawdata.txt'
).update(file_type='TSV')
```

**Option B: Modify the AI Agent query**
Edit `ai_agent/views.py` line 83 to match your file_type:

```python
# Change this:
available_samples = AnalysisFileLocation.objects.filter(
    file_type='TSV',  # <-- Change to your file_type
    is_active=True
)
```

## Verification

### 1. Check Django Admin

Visit: `http://localhost:8000/admin/ai_agent/`

You should see:
- Chat sessions
- Chat messages
- Analysis jobs

### 2. Test AI Agent

Visit: `http://localhost:8000/ai-agent/`

You should see the chat interface with welcome message.

### 3. Test Background Jobs

Try asking: "Analyze statistical data for a sample"

Check Celery worker terminal for task execution logs.

### 4. Check Redis

```bash
redis-cli
> KEYS *
> EXIT
```

Should show Celery keys if tasks are running.

## Troubleshooting

### Issue: "Anthropic API key not configured"
**Solution:** Set `ANTHROPIC_API_KEY` environment variable

### Issue: "No module named 'anthropic'"
**Solution:** `pip install anthropic`

### Issue: "Connection refused" (Redis)
**Solution:** Start Redis: `sudo systemctl start redis` or `brew services start redis`

### Issue: "Jobs stuck in PENDING"
**Solution:** Start Celery worker: `celery -A cholestrack worker -l info`

### Issue: "No data files found"
**Solution:** Ensure your `AnalysisFileLocation` records have `file_type='TSV'` or modify query in views.py

### Issue: ImportError with celery
**Solution:** Ensure `cholestrack/__init__.py` imports celery_app and `cholestrack/celery.py` exists

## Production Deployment

For production deployment:

1. **Use environment variables** for sensitive data (API keys)
2. **Use supervisor or systemd** to manage Celery workers
3. **Use nginx** as reverse proxy
4. **Enable HTTPS** for API calls
5. **Set DEBUG=False** in settings.py
6. **Use Redis with authentication**
7. **Monitor Celery** with Flower: `pip install flower && celery -A cholestrack flower`
8. **Set up log rotation** for Celery logs
9. **Consider rate limiting** for API calls

## Next Steps

Once installed:

1. Configure user permissions (RBAC integration)
2. Test with real variant data
3. Customize system prompts in `claude_client.py`
4. Add custom analysis types in `tasks.py`
5. Create custom report templates in `report_generator.py`

## Support

For questions or issues:
- Check the main README.md
- Review Django/Celery logs
- Contact development team
