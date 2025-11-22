# Celery Systemd Setup Instructions

## Prerequisites

Before installing the service files, you need to:

1. **Create log directory:**
```bash
sudo mkdir -p /var/log/celery
sudo chown burlo:burlo /var/log/celery
sudo chmod 755 /var/log/celery
```

2. **Create PID directory:**
```bash
sudo mkdir -p /var/run/celery
sudo chown burlo:burlo /var/run/celery
sudo chmod 755 /var/run/celery
```

## Installation Steps

### 1. Copy Service Files

```bash
# Copy celery worker service
sudo cp celery.service /etc/systemd/system/

# (Optional) Copy celery beat service for scheduled tasks
sudo cp celerybeat.service /etc/systemd/system/
```

### 2. Verify Service File Configuration

**Important:** Before enabling, verify these paths in the service files match your actual setup:

- **User/Group**: Check if `burlo` is correct (should match your system user)
- **WorkingDirectory**: Should point to the inner cholestrack directory (e.g., `/home/burlo/cholestrack/cholestrack`)
- **Virtual Environment Path**: Should point to your virtualenv (e.g., `/home/burlo/cholestrack/.venv`)
- **Redis**: Ensure Redis is installed and running

**Note:** The celery service uses lowercase 'cholestrack' to match the Celery app name in `celery_app.py`.

Edit if needed:
```bash
sudo nano /etc/systemd/system/celery.service
# Update paths to match your installation directory
```

### 3. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 4. Enable Services (Start on Boot)

```bash
# Enable Celery worker
sudo systemctl enable celery.service

# (Optional) Enable Celery beat for scheduled tasks
sudo systemctl enable celerybeat.service
```

### 5. Start Services

```bash
# Start Celery worker
sudo systemctl start celery.service

# (Optional) Start Celery beat
sudo systemctl start celerybeat.service
```

## Managing Celery Services

### Check Status
```bash
sudo systemctl status celery
sudo systemctl status celerybeat
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u celery -f

# Celery worker log file
sudo tail -f /var/log/celery/worker.log

# Celery beat log file
sudo tail -f /var/log/celery/beat.log
```

### Restart Services
```bash
sudo systemctl restart celery
sudo systemctl restart celerybeat
```

### Stop Services
```bash
sudo systemctl stop celery
sudo systemctl stop celerybeat
```

### Disable Services (Don't Start on Boot)
```bash
sudo systemctl disable celery
sudo systemctl disable celerybeat
```

## Troubleshooting

### Service Won't Start or Restart

**Common Error:** `Job for celery.service failed because the control process exited with error code.`

**Automated Fix:**

Run the automated fix script:
```bash
cd /home/burlo/cholestrack/deploy_management
sudo ./fix_celery_restart.sh
```

**Manual Fix Steps:**

1. **Check service status for detailed error:**
```bash
sudo systemctl status celery -l
sudo journalctl -xeu celery.service
```

2. **Clean up stale PID files:**
```bash
# Remove old PID file if it exists
sudo rm -f /var/run/celery/worker.pid
```

3. **Verify and fix directory permissions:**
```bash
# Ensure directories exist with correct ownership
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown -R burlo:burlo /var/log/celery /var/run/celery
sudo chmod 755 /var/log/celery /var/run/celery
```

4. **Stop any running Celery workers manually:**
```bash
# Find and kill any orphaned Celery processes
pkill -f 'celery.*worker'
```

5. **Reload systemd and restart:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart celery
```

6. **Verify Redis is running:**
```bash
sudo systemctl status redis
# or
redis-cli ping
```

7. **Test Celery manually:**
```bash
cd /home/burlo/cholestrack/cholestrack
source ../.venv/bin/activate
celery -A celery_app worker -l info
# Press Ctrl+C to stop
```

### Permission Issues

```bash
# Fix log directory permissions
sudo chown -R burlo:burlo /var/log/celery
sudo chmod 755 /var/log/celery

# Fix PID directory permissions
sudo chown -R burlo:burlo /var/run/celery
sudo chmod 755 /var/run/celery

# Ensure the user can write to these locations
sudo -u burlo touch /var/log/celery/test.log
sudo -u burlo touch /var/run/celery/test.pid
sudo rm /var/log/celery/test.log /var/run/celery/test.pid
```

### PID File Issues

If Celery worker crashes or is killed improperly, the PID file may remain and prevent restart:

```bash
# Check if PID file exists
ls -la /var/run/celery/worker.pid

# Check if the process is actually running
cat /var/run/celery/worker.pid
ps aux | grep $(cat /var/run/celery/worker.pid 2>/dev/null)

# If process is not running, remove stale PID file
sudo rm /var/run/celery/worker.pid

# Restart service
sudo systemctl restart celery
```

### Update After Code Changes

After updating your Django/Celery code:
```bash
sudo systemctl restart celery
```

## Integration with Gunicorn and Nginx

Your complete service startup order will be:

1. **PostgreSQL** (database)
2. **Redis** (Celery broker)
3. **Celery Worker** (background tasks)
4. **Gunicorn** (Django application)
5. **Nginx** (web server)

All will start automatically on system boot after being enabled.

## Monitoring All Services

```bash
# Check all related services
sudo systemctl status postgresql redis celery gunicorn nginx
```

## Notes

- **Type=forking**: Celery worker uses `--detach` flag to run in background
- **Type=simple**: Celery beat runs in foreground (no detach option)
- **Restart=always**: Services will automatically restart if they crash
- **After=redis.service**: Ensures Redis starts before Celery
- **PID files**: Located in `/var/run/celery/` for process tracking
- **Logs**: Located in `/var/log/celery/` for debugging

## Security Considerations

The service files include basic security settings:
- `PrivateTmp=true`: Isolates /tmp directory
- `NoNewPrivileges=true`: Prevents privilege escalation

For production, consider adding more security directives based on your needs.
