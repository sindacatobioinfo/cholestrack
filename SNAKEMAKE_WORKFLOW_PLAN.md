# Snakemake Workflow Integration Plan

## Overview
Integrate Snakemake workflow execution with the Cholestrack Django application, allowing users to submit genomic analysis jobs to a remote HPC/compute cluster and receive notifications upon completion.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Django Web Application                       │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Workflow Config│  │  Job Queue   │  │  Notification     │   │
│  │    Builder     │──│   (Celery)   │──│    System        │   │
│  └────────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────┬────────────────────────────────────┬───────────┘
                 │                                    │
                 │ SSH/SFTP                          │ Email/WebSocket
                 ↓                                    ↓
┌────────────────────────────────────────┐  ┌────────────────────┐
│     Remote Compute Server (HPC)        │  │       User         │
│  ┌──────────────────────────────────┐  │  │                    │
│  │  Snakemake Workflow Execution    │  │  │  Email + Dashboard │
│  │  - BAM Processing                │  │  │  Notifications     │
│  │  - Variant Calling               │  │  │                    │
│  │  - Quality Control               │  │  └────────────────────┘
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Shared Storage (NFS/Network)    │  │
│  │  - Input Files                   │  │
│  │  - Output Files                  │  │
│  │  - Logs                          │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Database Models and Job Management

#### 1.1 Create Workflow Job Model
**File**: `cholestrack/analysis_workflows/models.py`

```python
class WorkflowJob(models.Model):
    """
    Tracks Snakemake workflow execution jobs.
    """
    # Job identification
    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Workflow configuration
    config_file = models.ForeignKey('WorkflowConfiguration', on_delete=models.CASCADE)
    workflow_type = models.CharField(max_length=100)  # e.g., 'variant_calling'

    # Job status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued on HPC'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Remote execution details
    remote_job_id = models.CharField(max_length=200, blank=True, null=True)  # SLURM/PBS job ID
    remote_working_dir = models.CharField(max_length=500)

    # Progress tracking
    progress_percentage = models.IntegerField(default=0)
    current_step = models.CharField(max_length=200, blank=True)

    # Results
    output_files = models.JSONField(default=dict, blank=True)
    logs = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Notification
    notification_sent = models.BooleanField(default=False)
```

#### 1.2 Create Job Notification Model
```python
class JobNotification(models.Model):
    """
    Tracks notifications sent to users about job status.
    """
    job = models.ForeignKey(WorkflowJob, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50)  # 'email', 'in_app', 'webhook'
    sent_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    success = models.BooleanField(default=True)
```

### Phase 2: Remote Execution Service

#### 2.1 SSH Connection Manager
**File**: `cholestrack/analysis_workflows/remote_executor.py`

```python
class RemoteExecutor:
    """
    Handles SSH connections and remote command execution.
    """

    def __init__(self, host, username, key_path=None):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.ssh_client = None
        self.sftp_client = None

    def connect(self):
        """Establish SSH connection to remote server."""

    def disconnect(self):
        """Close SSH connection."""

    def upload_file(self, local_path, remote_path):
        """Upload file via SFTP."""

    def download_file(self, remote_path, local_path):
        """Download file via SFTP."""

    def execute_command(self, command):
        """Execute command on remote server and return output."""

    def submit_slurm_job(self, script_path):
        """Submit SLURM job and return job ID."""

    def check_job_status(self, job_id):
        """Check status of SLURM job."""

    def cancel_job(self, job_id):
        """Cancel running SLURM job."""
```

#### 2.2 Snakemake Workflow Launcher
**File**: `cholestrack/analysis_workflows/snakemake_launcher.py`

```python
class SnakemakeLauncher:
    """
    Launches Snakemake workflows on remote compute servers.
    """

    def __init__(self, remote_executor):
        self.executor = remote_executor

    def prepare_working_directory(self, job_id):
        """Create remote working directory for job."""

    def upload_config(self, config_yaml, remote_path):
        """Upload config.yaml to remote server."""

    def upload_input_files(self, file_list, remote_dir):
        """Upload input files (BAMs, VCFs, etc.) to remote server."""

    def generate_slurm_script(self, job):
        """Generate SLURM submission script for Snakemake."""
        # Template:
        # #!/bin/bash
        # #SBATCH --job-name=cholestrack_{job_id}
        # #SBATCH --output=logs/snakemake_%j.out
        # #SBATCH --error=logs/snakemake_%j.err
        # #SBATCH --time=24:00:00
        # #SBATCH --ntasks=1
        # #SBATCH --cpus-per-task=4
        # #SBATCH --mem=16G
        #
        # module load snakemake/7.32.4
        #
        # snakemake --configfile config.yaml \
        #           --cores 4 \
        #           --use-conda \
        #           --keep-going \
        #           --printshellcmds \
        #           --reason

    def submit_workflow(self, job):
        """Submit Snakemake workflow to remote scheduler."""

    def monitor_workflow(self, job):
        """Monitor workflow progress and update job status."""

    def download_results(self, job):
        """Download output files from remote server."""
```

### Phase 3: Celery Task Queue Integration

#### 3.1 Background Tasks
**File**: `cholestrack/analysis_workflows/tasks.py`

```python
from celery import shared_task
from .models import WorkflowJob
from .snakemake_launcher import SnakemakeLauncher
from .remote_executor import RemoteExecutor
from django.conf import settings

@shared_task(bind=True, max_retries=3)
def submit_snakemake_job(self, job_id):
    """
    Submit Snakemake job to remote server.
    """
    try:
        job = WorkflowJob.objects.get(job_id=job_id)
        job.status = 'queued'
        job.save()

        # Create remote executor
        executor = RemoteExecutor(
            host=settings.HPC_HOST,
            username=settings.HPC_USERNAME,
            key_path=settings.HPC_SSH_KEY_PATH
        )
        executor.connect()

        # Launch workflow
        launcher = SnakemakeLauncher(executor)
        remote_job_id = launcher.submit_workflow(job)

        job.remote_job_id = remote_job_id
        job.status = 'running'
        job.started_at = timezone.now()
        job.save()

        # Schedule monitoring task
        monitor_snakemake_job.apply_async(
            args=[job_id],
            countdown=60  # Check after 1 minute
        )

        executor.disconnect()
        return f"Job {job_id} submitted with remote ID {remote_job_id}"

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()
        raise


@shared_task(bind=True)
def monitor_snakemake_job(self, job_id):
    """
    Monitor Snakemake job status and schedule next check.
    """
    try:
        job = WorkflowJob.objects.get(job_id=job_id)

        if job.status not in ['running', 'queued']:
            return  # Job already completed or cancelled

        executor = RemoteExecutor(
            host=settings.HPC_HOST,
            username=settings.HPC_USERNAME,
            key_path=settings.HPC_SSH_KEY_PATH
        )
        executor.connect()

        # Check job status
        status_info = executor.check_job_status(job.remote_job_id)

        if status_info['state'] == 'RUNNING':
            # Update progress if available
            job.current_step = status_info.get('current_step', '')
            job.save()

            # Schedule next check in 5 minutes
            monitor_snakemake_job.apply_async(
                args=[job_id],
                countdown=300
            )

        elif status_info['state'] == 'COMPLETED':
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()

            # Download results
            download_job_results.delay(job_id)

            # Send notification
            send_job_notification.delay(job_id, 'completed')

        elif status_info['state'] in ['FAILED', 'CANCELLED']:
            job.status = 'failed'
            job.error_message = status_info.get('error', 'Job failed on remote server')
            job.completed_at = timezone.now()
            job.save()

            send_job_notification.delay(job_id, 'failed')

        executor.disconnect()

    except Exception as e:
        # Log error and retry
        self.retry(exc=e, countdown=300)


@shared_task
def download_job_results(job_id):
    """
    Download output files from remote server.
    """
    job = WorkflowJob.objects.get(job_id=job_id)

    executor = RemoteExecutor(
        host=settings.HPC_HOST,
        username=settings.HPC_USERNAME,
        key_path=settings.HPC_SSH_KEY_PATH
    )
    executor.connect()

    # Download output files
    local_output_dir = os.path.join(settings.MEDIA_ROOT, 'workflow_results', str(job.job_id))
    os.makedirs(local_output_dir, exist_ok=True)

    # Download files based on workflow type
    remote_output_dir = os.path.join(job.remote_working_dir, 'results')

    downloaded_files = {}
    for remote_file in executor.list_files(remote_output_dir):
        local_file = os.path.join(local_output_dir, os.path.basename(remote_file))
        executor.download_file(remote_file, local_file)
        downloaded_files[os.path.basename(remote_file)] = local_file

    job.output_files = downloaded_files
    job.save()

    executor.disconnect()


@shared_task
def send_job_notification(job_id, notification_type):
    """
    Send notification to user about job status.
    """
    job = WorkflowJob.objects.get(job_id=job_id)
    user = job.user

    if notification_type == 'completed':
        subject = f"Workflow Job {job.job_id} Completed Successfully"
        message = f"""
        Your Snakemake workflow job has completed successfully.

        Job ID: {job.job_id}
        Workflow Type: {job.workflow_type}
        Completed At: {job.completed_at}

        You can view the results at: {settings.SITE_DOMAIN}/workflows/jobs/{job.job_id}/

        Output files:
        {', '.join(job.output_files.keys())}
        """
    else:  # failed
        subject = f"Workflow Job {job.job_id} Failed"
        message = f"""
        Your Snakemake workflow job has failed.

        Job ID: {job.job_id}
        Workflow Type: {job.workflow_type}
        Error: {job.error_message}

        Please check the logs for more details.
        """

    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )

    # Create in-app notification
    JobNotification.objects.create(
        job=job,
        notification_type='email',
        message=message,
        success=True
    )

    job.notification_sent = True
    job.save()
```

### Phase 4: Django Views and Forms

#### 4.1 Job Submission View
**File**: `cholestrack/analysis_workflows/views.py`

```python
@login_required
@role_confirmed_required
def submit_workflow_job(request, config_id):
    """
    Submit workflow job using existing configuration.
    """
    config = get_object_or_404(WorkflowConfiguration, id=config_id, user=request.user)

    if request.method == 'POST':
        # Create job
        job = WorkflowJob.objects.create(
            user=request.user,
            config_file=config,
            workflow_type=config.workflow_type,
            remote_working_dir=f"/hpc/workflows/{request.user.username}/{uuid.uuid4()}"
        )

        # Submit to Celery queue
        submit_snakemake_job.delay(str(job.job_id))

        messages.success(request, f'Workflow job {job.job_id} has been submitted!')
        return redirect('analysis_workflows:job_detail', job_id=job.job_id)

    return render(request, 'analysis_workflows/submit_job.html', {'config': config})


@login_required
@role_confirmed_required
def job_detail(request, job_id):
    """
    View job details and status.
    """
    job = get_object_or_404(WorkflowJob, job_id=job_id, user=request.user)

    context = {
        'job': job,
        'can_cancel': job.status in ['pending', 'queued', 'running'],
        'can_resubmit': job.status in ['failed', 'cancelled'],
    }
    return render(request, 'analysis_workflows/job_detail.html', context)


@login_required
@role_confirmed_required
def job_list(request):
    """
    List all workflow jobs for current user.
    """
    jobs = WorkflowJob.objects.filter(user=request.user).order_by('-created_at')

    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'analysis_workflows/job_list.html', context)


@login_required
@role_confirmed_required
def cancel_job(request, job_id):
    """
    Cancel running job.
    """
    job = get_object_or_404(WorkflowJob, job_id=job_id, user=request.user)

    if job.status in ['pending', 'queued', 'running']:
        # Cancel on remote server
        executor = RemoteExecutor(
            host=settings.HPC_HOST,
            username=settings.HPC_USERNAME,
            key_path=settings.HPC_SSH_KEY_PATH
        )
        executor.connect()
        executor.cancel_job(job.remote_job_id)
        executor.disconnect()

        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.save()

        messages.success(request, f'Job {job.job_id} has been cancelled.')
    else:
        messages.error(request, 'Job cannot be cancelled in its current state.')

    return redirect('analysis_workflows:job_detail', job_id=job.job_id)
```

### Phase 5: Configuration and Security

#### 5.1 Settings Configuration
**File**: `cholestrack/project/settings.py`

```python
# Remote HPC Configuration
HPC_HOST = env('HPC_HOST', default='hpc.example.com')
HPC_USERNAME = env('HPC_USERNAME', default='cholestrack')
HPC_SSH_KEY_PATH = env('HPC_SSH_KEY_PATH', default='/path/to/ssh/key')
HPC_WORKING_DIR_BASE = env('HPC_WORKING_DIR_BASE', default='/hpc/workflows')

# Workflow Configuration
SNAKEMAKE_WORKFLOWS_DIR = env('SNAKEMAKE_WORKFLOWS_DIR', default='/path/to/snakemake/workflows')
WORKFLOW_RESULTS_DIR = os.path.join(MEDIA_ROOT, 'workflow_results')

# Job Monitoring
JOB_MONITOR_INTERVAL = 300  # 5 minutes
JOB_MAX_RUNTIME = 86400  # 24 hours
```

#### 5.2 SSH Key Setup
```bash
# Generate SSH key pair for Django server
ssh-keygen -t rsa -b 4096 -f ~/.ssh/cholestrack_hpc_key -N ""

# Add public key to remote server's authorized_keys
ssh-copy-id -i ~/.ssh/cholestrack_hpc_key.pub user@hpc.example.com

# Set proper permissions
chmod 600 ~/.ssh/cholestrack_hpc_key
chmod 644 ~/.ssh/cholestrack_hpc_key.pub
```

### Phase 6: Testing Strategy

#### 6.1 Unit Tests
- Test remote executor connection and command execution
- Test SLURM script generation
- Test file upload/download
- Test job status parsing

#### 6.2 Integration Tests
- Test full workflow submission pipeline
- Test job monitoring and status updates
- Test notification delivery
- Test result download

#### 6.3 End-to-End Tests
- Submit real workflow with test data
- Monitor until completion
- Verify results downloaded correctly
- Verify notification sent

### Phase 7: Deployment Checklist

- [ ] Set up SSH keys between Django server and HPC
- [ ] Configure environment variables for HPC connection
- [ ] Install required Python packages (paramiko, scp)
- [ ] Create remote working directory structure
- [ ] Set up Celery workers for background tasks
- [ ] Configure email settings for notifications
- [ ] Test connectivity to HPC from Django server
- [ ] Deploy Snakemake workflows to HPC
- [ ] Create database migrations
- [ ] Set up monitoring and logging
- [ ] Create user documentation

## Security Considerations

1. **SSH Key Management**: Store private keys securely, never in version control
2. **User Isolation**: Each user gets separate working directory on HPC
3. **Resource Limits**: Implement quotas for CPU/memory/storage per user
4. **Input Validation**: Sanitize all user inputs in config files
5. **File Access Control**: Restrict access to job results based on ownership
6. **Audit Logging**: Log all job submissions and status changes

## Alternative Approaches

### Option A: REST API on HPC
Instead of SSH, deploy a REST API on the HPC that Django can call:
- Pros: More scalable, better error handling, easier testing
- Cons: Requires additional infrastructure on HPC

### Option B: Shared Filesystem
If Django and HPC share a filesystem (NFS):
- Pros: No file transfer needed, faster
- Cons: Requires shared storage setup

### Option C: Job Queue Manager (e.g., Dask, Ray)
Use a distributed job queue manager:
- Pros: Better resource management, built-in monitoring
- Cons: More complex setup

## Recommended Approach

**Hybrid Approach**:
1. Use SSH for initial implementation (simplest, most flexible)
2. Monitor jobs via Celery periodic tasks
3. Store results on shared storage if available, otherwise download via SFTP
4. Send email notifications + in-app notifications
5. Consider migrating to REST API approach as system scales

## Timeline Estimate

- Phase 1-2: 2-3 days (Models + Remote Executor)
- Phase 3: 2 days (Celery Tasks)
- Phase 4: 1-2 days (Views and Forms)
- Phase 5-6: 1-2 days (Configuration + Testing)
- Phase 7: 1 day (Deployment)

**Total**: ~7-10 days for full implementation

## Next Steps

1. Confirm remote server details (HPC host, auth method, job scheduler)
2. Set up SSH access between Django server and HPC
3. Implement RemoteExecutor class with basic SSH functionality
4. Create database models and migrations
5. Implement basic job submission without Snakemake (test connectivity)
6. Add Snakemake integration
7. Implement monitoring and notifications
8. Test with real workflow
9. Deploy to production
