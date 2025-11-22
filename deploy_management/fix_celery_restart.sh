#!/bin/bash
# Quick fix script for Celery restart issues
# This script addresses common problems that prevent Celery from restarting

echo "=== Celery Restart Fix Script ==="
echo ""

# Get the current user
CELERY_USER="${CELERY_USER:-burlo}"
echo "Using Celery user: $CELERY_USER"
echo ""

# Step 1: Stop any running Celery workers
echo "1. Stopping any running Celery workers..."
sudo pkill -f 'celery.*worker' 2>/dev/null
sleep 2
echo "   Done."
echo ""

# Step 2: Remove stale PID files
echo "2. Removing stale PID files..."
sudo rm -f /var/run/celery/worker.pid
sudo rm -f /var/run/celery/beat.pid
echo "   Done."
echo ""

# Step 3: Ensure directories exist with correct permissions
echo "3. Setting up directories with correct permissions..."
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown -R $CELERY_USER:$CELERY_USER /var/log/celery /var/run/celery
sudo chmod 755 /var/log/celery /var/run/celery
echo "   Done."
echo ""

# Step 4: Verify Redis is running
echo "4. Checking Redis status..."
if sudo systemctl is-active --quiet redis; then
    echo "   Redis is running ✓"
elif sudo systemctl is-active --quiet redis-server; then
    echo "   Redis is running ✓"
else
    echo "   WARNING: Redis does not appear to be running!"
    echo "   Start it with: sudo systemctl start redis"
fi
echo ""

# Step 5: Reload systemd
echo "5. Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "   Done."
echo ""

# Step 6: Restart Celery service
echo "6. Starting Celery service..."
if sudo systemctl restart celery; then
    echo "   Celery service restarted successfully ✓"
    echo ""
    echo "7. Checking Celery status..."
    sudo systemctl status celery --no-pager -l
else
    echo "   ERROR: Failed to restart Celery service"
    echo ""
    echo "   Check logs with:"
    echo "   sudo journalctl -xeu celery.service"
    exit 1
fi

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Monitor Celery logs with:"
echo "  sudo journalctl -u celery -f"
echo ""
echo "Or check the log file:"
echo "  sudo tail -f /var/log/celery/worker.log"
