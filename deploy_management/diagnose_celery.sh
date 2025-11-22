#!/bin/bash
# Celery diagnostic script - checks common issues preventing Celery from starting

echo "=== Celery Diagnostic Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the current user
CELERY_USER="${CELERY_USER:-burlo}"
PROJECT_DIR="/home/$CELERY_USER/cholestrack"
WORKING_DIR="$PROJECT_DIR/cholestrack"

echo "Configuration:"
echo "  User: $CELERY_USER"
echo "  Project Dir: $PROJECT_DIR"
echo "  Working Dir: $WORKING_DIR"
echo ""

# Check 1: Verify directories exist
echo "=== Check 1: Directory Structure ==="
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${GREEN}✓${NC} Project directory exists: $PROJECT_DIR"
else
    echo -e "${RED}✗${NC} Project directory NOT found: $PROJECT_DIR"
    echo "  Update CELERY_USER or PROJECT_DIR variables in this script"
fi

if [ -d "$WORKING_DIR" ]; then
    echo -e "${GREEN}✓${NC} Working directory exists: $WORKING_DIR"
else
    echo -e "${RED}✗${NC} Working directory NOT found: $WORKING_DIR"
fi

if [ -f "$WORKING_DIR/celery_app.py" ]; then
    echo -e "${GREEN}✓${NC} celery_app.py found"
else
    echo -e "${RED}✗${NC} celery_app.py NOT found at $WORKING_DIR/celery_app.py"
fi
echo ""

# Check 2: Virtual environment
echo "=== Check 2: Virtual Environment ==="
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found: $PROJECT_DIR/.venv"

    if [ -f "$PROJECT_DIR/.venv/bin/celery" ]; then
        echo -e "${GREEN}✓${NC} Celery binary found in venv"
        $PROJECT_DIR/.venv/bin/celery --version
    else
        echo -e "${RED}✗${NC} Celery NOT installed in venv"
        echo "  Run: source $PROJECT_DIR/.venv/bin/activate && pip install celery==5.3.6"
    fi
else
    echo -e "${RED}✗${NC} Virtual environment NOT found: $PROJECT_DIR/.venv"
    echo "  Create with: python3 -m venv $PROJECT_DIR/.venv"
fi
echo ""

# Check 3: Redis
echo "=== Check 3: Redis Service ==="
if systemctl is-active --quiet redis 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis service is running"
elif systemctl is-active --quiet redis-server 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis-server service is running"
else
    echo -e "${RED}✗${NC} Redis is NOT running"
    echo "  Start with: sudo systemctl start redis"
fi

# Test Redis connection
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis connection successful (PING test)"
    else
        echo -e "${RED}✗${NC} Cannot connect to Redis"
        echo "  Check if Redis is running: sudo systemctl status redis"
    fi
else
    echo -e "${YELLOW}!${NC} redis-cli not found, skipping connection test"
fi
echo ""

# Check 4: Directory permissions
echo "=== Check 4: Log and PID Directories ==="
for dir in /var/log/celery /var/run/celery; do
    if [ -d "$dir" ]; then
        owner=$(stat -c '%U:%G' "$dir")
        perms=$(stat -c '%a' "$dir")

        if [ "$owner" = "$CELERY_USER:$CELERY_USER" ] && [ "$perms" = "755" ]; then
            echo -e "${GREEN}✓${NC} $dir exists with correct ownership and permissions"
        else
            echo -e "${YELLOW}!${NC} $dir exists but has owner=$owner (expected $CELERY_USER:$CELERY_USER) perms=$perms (expected 755)"
            echo "  Fix with: sudo chown $CELERY_USER:$CELERY_USER $dir && sudo chmod 755 $dir"
        fi
    else
        echo -e "${RED}✗${NC} $dir does NOT exist"
        echo "  Create with: sudo mkdir -p $dir && sudo chown $CELERY_USER:$CELERY_USER $dir && sudo chmod 755 $dir"
    fi
done
echo ""

# Check 5: Stale PID files
echo "=== Check 5: PID Files ==="
for pidfile in /var/run/celery/worker.pid /var/run/celery/beat.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}!${NC} $pidfile exists and process $pid is running"
            echo "  Check if this is an old Celery worker: ps aux | grep $pid"
        else
            echo -e "${YELLOW}!${NC} $pidfile exists but process $pid is NOT running (stale PID file)"
            echo "  Remove with: sudo rm $pidfile"
        fi
    else
        echo -e "${GREEN}✓${NC} No stale PID file: $pidfile"
    fi
done
echo ""

# Check 6: Running Celery processes
echo "=== Check 6: Running Celery Processes ==="
celery_procs=$(pgrep -f "celery.*worker" | wc -l)
if [ "$celery_procs" -gt 0 ]; then
    echo -e "${YELLOW}!${NC} Found $celery_procs running Celery processes"
    ps aux | grep -E "[c]elery.*worker"
    echo "  If these are orphaned, kill with: pkill -f 'celery.*worker'"
else
    echo -e "${GREEN}✓${NC} No Celery worker processes currently running"
fi
echo ""

# Check 7: Service file
echo "=== Check 7: Systemd Service File ==="
if [ -f "/etc/systemd/system/celery.service" ]; then
    echo -e "${GREEN}✓${NC} /etc/systemd/system/celery.service exists"

    # Check if paths in service file match
    echo "  Checking service file configuration..."
    if grep -q "WorkingDirectory=$WORKING_DIR" /etc/systemd/system/celery.service; then
        echo -e "${GREEN}✓${NC} WorkingDirectory matches: $WORKING_DIR"
    else
        echo -e "${RED}✗${NC} WorkingDirectory doesn't match!"
        echo "  Expected: $WORKING_DIR"
        echo "  Found: $(grep WorkingDirectory /etc/systemd/system/celery.service)"
    fi

    if grep -q "User=$CELERY_USER" /etc/systemd/system/celery.service; then
        echo -e "${GREEN}✓${NC} User matches: $CELERY_USER"
    else
        echo -e "${YELLOW}!${NC} User might not match"
        echo "  Found: $(grep ^User= /etc/systemd/system/celery.service)"
    fi
else
    echo -e "${RED}✗${NC} Service file NOT found: /etc/systemd/system/celery.service"
    echo "  Copy with: sudo cp $PROJECT_DIR/deploy_management/celery.service /etc/systemd/system/"
fi
echo ""

# Check 8: Test manual Celery start
echo "=== Check 8: Manual Celery Test ==="
echo "To manually test Celery, run:"
echo "  cd $WORKING_DIR"
echo "  source $PROJECT_DIR/.venv/bin/activate"
echo "  celery -A celery_app worker -l info"
echo ""
echo "Press Ctrl+C to stop the test, then fix any errors shown."
echo ""

# Check 9: Service status and logs
echo "=== Check 9: Service Status ==="
if systemctl list-unit-files | grep -q celery.service; then
    echo "Service status:"
    sudo systemctl status celery --no-pager -l || true
    echo ""
    echo "Recent logs:"
    sudo journalctl -u celery -n 20 --no-pager || echo "No journal entries found"
else
    echo -e "${YELLOW}!${NC} Celery service not registered with systemd"
fi
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "Quick Fix Command:"
echo "  cd $PROJECT_DIR/deploy_management && sudo ./fix_celery_restart.sh"
