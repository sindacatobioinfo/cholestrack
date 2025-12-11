#!/bin/bash
# Test script for verifying sudo access to FASTQ files
# Run this on the burlo server to test if sudo is configured correctly

set -e

echo "======================================"
echo "FASTQ Sudo Access Test Script"
echo "======================================"
echo ""

# Configuration
FASTQ_DIR="/home/burlo/cholestrack/cholestrack/media/remote_files/fastq"
FASTQ_OWNER="burlo"
DJANGO_USER="${1:-ronald_moura}"  # First argument or default to ronald_moura

echo "Configuration:"
echo "  FASTQ Directory: ${FASTQ_DIR}"
echo "  FASTQ Owner: ${FASTQ_OWNER}"
echo "  Django User: ${DJANGO_USER}"
echo ""

# Check if Django user exists
if ! id "${DJANGO_USER}" >/dev/null 2>&1; then
    echo "ERROR: Django user '${DJANGO_USER}' does not exist"
    echo "Usage: $0 <django-user>"
    echo "Example: $0 ronald_moura"
    exit 1
fi

echo "Step 1: Checking sudoers file"
echo "------------------------------"
if [ -f "/etc/sudoers.d/cholestrack" ]; then
    echo "✓ Sudoers file exists at /etc/sudoers.d/cholestrack"

    # Check permissions
    perms=$(stat -c "%a" /etc/sudoers.d/cholestrack)
    if [ "$perms" = "440" ] || [ "$perms" = "400" ]; then
        echo "✓ Permissions are correct: $perms"
    else
        echo "⚠ WARNING: Permissions should be 440, currently: $perms"
        echo "  Run: sudo chmod 440 /etc/sudoers.d/cholestrack"
    fi

    # Check if Django user is mentioned
    if grep -q "^${DJANGO_USER}" /etc/sudoers.d/cholestrack; then
        echo "✓ Django user '${DJANGO_USER}' is configured in sudoers"
    elif grep -q "^#.*${DJANGO_USER}" /etc/sudoers.d/cholestrack; then
        echo "✗ Django user '${DJANGO_USER}' is COMMENTED OUT in sudoers"
        echo "  Edit /etc/sudoers.d/cholestrack and uncomment the ${DJANGO_USER} lines"
        exit 1
    else
        echo "⚠ WARNING: Django user '${DJANGO_USER}' not found in sudoers file"
        echo "  You may need to add it manually"
    fi
else
    echo "✗ Sudoers file NOT FOUND at /etc/sudoers.d/cholestrack"
    echo "  Run: sudo cp sudoers.d/cholestrack /etc/sudoers.d/cholestrack"
    echo "  Then: sudo chmod 440 /etc/sudoers.d/cholestrack"
    exit 1
fi
echo ""

echo "Step 2: Checking sudo syntax"
echo "------------------------------"
if sudo visudo -c 2>&1 | grep -q "parsed OK"; then
    echo "✓ Sudo configuration syntax is valid"
else
    echo "✗ Sudo configuration has SYNTAX ERRORS"
    sudo visudo -c
    exit 1
fi
echo ""

echo "Step 3: Finding FASTQ files"
echo "------------------------------"
if [ ! -d "${FASTQ_DIR}" ]; then
    echo "✗ FASTQ directory does not exist: ${FASTQ_DIR}"
    exit 1
fi

# Find first FASTQ file
SAMPLE_FILE=$(find "${FASTQ_DIR}" -name "*.fastq.gz" -type f | head -1)

if [ -z "${SAMPLE_FILE}" ]; then
    echo "✗ No FASTQ files found in ${FASTQ_DIR}"
    exit 1
fi

echo "✓ Found FASTQ file for testing: $(basename ${SAMPLE_FILE})"
echo "  Full path: ${SAMPLE_FILE}"
echo ""

echo "Step 4: Testing current user access"
echo "------------------------------"
if [ "$(whoami)" = "${FASTQ_OWNER}" ]; then
    echo "✓ Running as ${FASTQ_OWNER}, can read file directly"
    if cat "${SAMPLE_FILE}" > /dev/null 2>&1; then
        echo "✓ File is readable"
    else
        echo "✗ File exists but cannot be read - check permissions"
        ls -l "${SAMPLE_FILE}"
        exit 1
    fi
elif cat "${SAMPLE_FILE}" > /dev/null 2>&1; then
    echo "⚠ File is readable by current user $(whoami)"
    echo "  This means Django might not need sudo for this file"
else
    echo "✓ File is NOT readable by $(whoami) (expected)"
    echo "  This is why we need sudo"
fi
echo ""

echo "Step 5: Testing Django user access (without sudo)"
echo "------------------------------"
if sudo -u "${DJANGO_USER}" cat "${SAMPLE_FILE}" > /dev/null 2>&1; then
    echo "⚠ File IS readable by ${DJANGO_USER} without sudo"
    echo "  Django might not need sudo for this file"
    echo "  But sudo will still work as a fallback"
else
    echo "✓ File is NOT readable by ${DJANGO_USER} without sudo (expected)"
fi
echo ""

echo "Step 6: Testing sudo cat as burlo (THE IMPORTANT TEST)"
echo "------------------------------"
echo "Running: sudo -u ${DJANGO_USER} sudo -n -u ${FASTQ_OWNER} cat ${SAMPLE_FILE}"
echo ""

if sudo -u "${DJANGO_USER}" sudo -n -u "${FASTQ_OWNER}" cat "${SAMPLE_FILE}" > /dev/null 2>&1; then
    echo "✅ SUCCESS! Django user can read FASTQ files using sudo!"
    echo ""
    echo "File details:"
    file_size=$(sudo -u "${DJANGO_USER}" sudo -n -u "${FASTQ_OWNER}" cat "${SAMPLE_FILE}" | wc -c)
    echo "  Size: ${file_size} bytes"
    echo ""
else
    echo "✗ FAILED! Django user CANNOT read FASTQ files using sudo"
    echo ""
    echo "Error output:"
    sudo -u "${DJANGO_USER}" sudo -n -u "${FASTQ_OWNER}" cat "${SAMPLE_FILE}" 2>&1 || true
    echo ""
    echo "Possible causes:"
    echo "  1. Sudoers file not installed correctly"
    echo "  2. Wrong Django user specified (currently: ${DJANGO_USER})"
    echo "  3. Sudoers file has wrong user or paths"
    echo "  4. Sudoers file is commented out"
    echo ""
    echo "To fix:"
    echo "  1. Edit /etc/sudoers.d/cholestrack"
    echo "  2. Uncomment the lines for ${DJANGO_USER}"
    echo "  3. Verify paths match your setup"
    echo "  4. Run: sudo visudo -c"
    echo "  5. Run this test again"
    exit 1
fi
echo ""

echo "Step 7: Testing with multiple FASTQ files"
echo "------------------------------"
success_count=0
fail_count=0

for fastq_file in $(find "${FASTQ_DIR}" -name "*.fastq.gz" -type f | head -5); do
    filename=$(basename "$fastq_file")
    if sudo -u "${DJANGO_USER}" sudo -n -u "${FASTQ_OWNER}" cat "$fastq_file" > /dev/null 2>&1; then
        echo "✓ ${filename}"
        success_count=$((success_count + 1))
    else
        echo "✗ ${filename}"
        fail_count=$((fail_count + 1))
    fi
done

echo ""
echo "Results: ${success_count} succeeded, ${fail_count} failed"
echo ""

if [ $fail_count -gt 0 ]; then
    echo "⚠ WARNING: Some files failed. Check permissions."
    exit 1
fi

echo "======================================"
echo "✅ ALL TESTS PASSED!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Restart Django services:"
echo "     sudo systemctl restart gunicorn"
echo "     sudo systemctl restart celery  # if applicable"
echo ""
echo "  2. Test downloading FASTQ files through the web interface"
echo ""
echo "  3. Check Django logs for messages like:"
echo "     'Using sudo to read FASTQ file as burlo'"
echo "     'File download successful (via sudo)'"
echo ""
echo "  4. Monitor logs:"
echo "     sudo journalctl -u gunicorn -f"
echo ""
