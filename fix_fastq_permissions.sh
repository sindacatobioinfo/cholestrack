#!/bin/bash
# Script to diagnose and fix FASTQ file permission issues on network-mounted directories
# Run this on the burlo server where Django is running

echo "=================================="
echo "FASTQ Permission Diagnostic Script"
echo "=================================="
echo ""

# Configuration
FASTQ_DIR="/home/burlo/cholestrack/cholestrack/media/remote_files/fastq"
SAMPLE_FILE="COL60_S8_1.fastq.gz"
DJANGO_USER="ronald_moura"

echo "Step 1: Checking current user"
echo "------------------------------"
echo "Current user: $(whoami)"
echo "Current UID: $(id -u)"
echo "Current GID: $(id -g)"
echo ""

echo "Step 2: Checking Django user '${DJANGO_USER}'"
echo "------------------------------"
id ${DJANGO_USER} 2>/dev/null || echo "ERROR: User ${DJANGO_USER} not found!"
echo ""

echo "Step 3: Checking directory permissions"
echo "------------------------------"
if [ -d "${FASTQ_DIR}" ]; then
    echo "Directory exists: ${FASTQ_DIR}"
    ls -ld "${FASTQ_DIR}"
    echo ""
    echo "Directory permissions breakdown:"
    stat -c "Owner: %U (UID: %u)" "${FASTQ_DIR}"
    stat -c "Group: %G (GID: %g)" "${FASTQ_DIR}"
    stat -c "Permissions: %A (%a)" "${FASTQ_DIR}"
    echo ""

    # Test if Django user can list directory
    echo "Testing if ${DJANGO_USER} can list directory..."
    sudo -u ${DJANGO_USER} ls "${FASTQ_DIR}" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ ${DJANGO_USER} CAN list directory"
    else
        echo "✗ ${DJANGO_USER} CANNOT list directory - PERMISSION ISSUE"
    fi
else
    echo "ERROR: Directory not found: ${FASTQ_DIR}"
    echo "Is the network mount working?"
    echo ""
    mount | grep remote_files
fi
echo ""

echo "Step 4: Checking sample file permissions"
echo "------------------------------"
SAMPLE_PATH="${FASTQ_DIR}/${SAMPLE_FILE}"
if [ -f "${SAMPLE_PATH}" ]; then
    echo "File exists: ${SAMPLE_PATH}"
    ls -lh "${SAMPLE_PATH}"
    echo ""
    echo "File permissions breakdown:"
    stat -c "Owner: %U (UID: %u)" "${SAMPLE_PATH}"
    stat -c "Group: %G (GID: %g)" "${SAMPLE_PATH}"
    stat -c "Permissions: %A (%a)" "${SAMPLE_PATH}"
    echo ""

    # Test if Django user can read file
    echo "Testing if ${DJANGO_USER} can read file..."
    sudo -u ${DJANGO_USER} cat "${SAMPLE_PATH}" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ ${DJANGO_USER} CAN read file"
    else
        echo "✗ ${DJANGO_USER} CANNOT read file - PERMISSION ISSUE"
    fi
else
    echo "ERROR: File not found: ${SAMPLE_PATH}"
fi
echo ""

echo "Step 5: Checking all FASTQ files"
echo "------------------------------"
if [ -d "${FASTQ_DIR}" ]; then
    echo "Testing access to first 5 FASTQ files..."
    count=0
    for file in "${FASTQ_DIR}"/*.fastq.gz; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            sudo -u ${DJANGO_USER} cat "$file" > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "✓ ${filename} - readable"
            else
                echo "✗ ${filename} - NOT readable"
            fi
            count=$((count+1))
            [ $count -ge 5 ] && break
        fi
    done
fi
echo ""

echo "Step 6: Checking mount point"
echo "------------------------------"
mount | grep "remote_files"
echo ""
df -h | grep "remote_files"
echo ""

echo "=================================="
echo "RECOMMENDED FIXES"
echo "=================================="
echo ""
echo "Based on the diagnostics above, here are the recommended solutions:"
echo ""
echo "Option 1: Add Django user to the file owner's group"
echo "---------------------------------------------------"
echo "If files are owned by a specific group (e.g., 'burlo' or 'bioinfo'):"
echo "  sudo usermod -aG <group-name> ${DJANGO_USER}"
echo "  # Then restart Django services:"
echo "  sudo systemctl restart gunicorn"
echo "  sudo systemctl restart celery"
echo ""

echo "Option 2: Fix file permissions (if you own the files)"
echo "------------------------------------------------------"
echo "Make files readable by everyone:"
echo "  sudo chmod -R 755 ${FASTQ_DIR}"
echo "  sudo chmod 644 ${FASTQ_DIR}/*.fastq.gz"
echo ""

echo "Option 3: Fix mount options (for CIFS/SMB mounts)"
echo "--------------------------------------------------"
echo "Edit /etc/fstab and add uid/gid options:"
echo "  //server/share ${FASTQ_DIR%/fastq} cifs credentials=...,uid=${DJANGO_USER},gid=${DJANGO_USER},... 0 0"
echo "Then remount:"
echo "  sudo umount ${FASTQ_DIR%/fastq}"
echo "  sudo mount -a"
echo ""

echo "Option 4: Fix mount options (for NFS mounts)"
echo "---------------------------------------------"
echo "Check NFS export options on the remote server in /etc/exports:"
echo "  /path/to/export *(rw,sync,no_root_squash,no_subtree_check)"
echo "On this server, remount with proper options:"
echo "  sudo mount -o remount ${FASTQ_DIR%/fastq}"
echo ""

echo "Option 5: Use ACLs for fine-grained control"
echo "--------------------------------------------"
echo "  sudo setfacl -R -m u:${DJANGO_USER}:rx ${FASTQ_DIR}"
echo "  sudo setfacl -R -m u:${DJANGO_USER}:r ${FASTQ_DIR}/*.fastq.gz"
echo ""

echo "=================================="
echo "QUICK FIX (run if you have permissions)"
echo "=================================="
echo ""
echo "If you want to quickly fix this, run one of these commands:"
echo ""
echo "# Check what group owns the files first"
echo "stat -c '%G' ${SAMPLE_PATH}"
echo ""
echo "# Then add Django user to that group"
echo "sudo usermod -aG \$(stat -c '%G' ${SAMPLE_PATH}) ${DJANGO_USER}"
echo "sudo systemctl restart gunicorn"
echo ""
echo "OR"
echo ""
echo "# Make files readable by everyone (less secure but simple)"
echo "sudo chmod -R a+rX ${FASTQ_DIR}"
echo ""
