#!/bin/bash
# Diagnostic script to compare permissions across remote_files subdirectories
# This will help identify why FASTQ files don't work while VCF/BAM/TSV do

echo "=========================================="
echo "Remote Files Permission Diagnostic"
echo "=========================================="
echo ""

REMOTE_FILES_BASE="/home/burlo/cholestrack/cholestrack/media/remote_files"
DJANGO_USER="${1:-ronald_moura}"

echo "Configuration:"
echo "  Remote files base: ${REMOTE_FILES_BASE}"
echo "  Django user: ${DJANGO_USER}"
echo ""

if [ ! -d "${REMOTE_FILES_BASE}" ]; then
    echo "ERROR: Remote files directory not found: ${REMOTE_FILES_BASE}"
    exit 1
fi

echo "Step 1: Checking subdirectories in remote_files"
echo "=========================================="
echo ""

for subdir in "${REMOTE_FILES_BASE}"/*; do
    if [ -d "$subdir" ]; then
        dirname=$(basename "$subdir")
        echo "Directory: ${dirname}"
        echo "----------------------------------------"

        # Get permissions
        ls -ld "$subdir"

        # Get owner and group
        owner=$(stat -c "%U" "$subdir")
        group=$(stat -c "%G" "$subdir")
        perms=$(stat -c "%a" "$subdir")

        echo "  Owner: ${owner}"
        echo "  Group: ${group}"
        echo "  Permissions: ${perms}"

        # Check if Django user can list directory
        if sudo -u "${DJANGO_USER}" ls "$subdir" >/dev/null 2>&1; then
            echo "  ✓ ${DJANGO_USER} CAN list directory"
        else
            echo "  ✗ ${DJANGO_USER} CANNOT list directory"
        fi

        # Find a sample file and check if readable
        sample_file=$(find "$subdir" -type f | head -1)
        if [ -n "$sample_file" ]; then
            filename=$(basename "$sample_file")
            file_owner=$(stat -c "%U" "$sample_file")
            file_group=$(stat -c "%G" "$sample_file")
            file_perms=$(stat -c "%a" "$sample_file")

            echo "  Sample file: ${filename}"
            echo "    Owner: ${file_owner}"
            echo "    Group: ${file_group}"
            echo "    Permissions: ${file_perms}"

            # Test if Django user can read
            if sudo -u "${DJANGO_USER}" cat "$sample_file" >/dev/null 2>&1; then
                echo "    ✓ ${DJANGO_USER} CAN read file"
            else
                echo "    ✗ ${DJANGO_USER} CANNOT read file"
            fi
        else
            echo "  (No files found in directory)"
        fi

        echo ""
    fi
done

echo "Step 2: Checking Django user groups"
echo "=========================================="
echo ""
sudo -u "${DJANGO_USER}" id
echo ""

echo "Step 3: Comparing working vs non-working directories"
echo "=========================================="
echo ""

# Find a working directory (vcf, bam, or tsv)
working_dir=""
for dir in vcf bam tsv; do
    if [ -d "${REMOTE_FILES_BASE}/${dir}" ]; then
        sample=$(find "${REMOTE_FILES_BASE}/${dir}" -type f | head -1)
        if [ -n "$sample" ] && sudo -u "${DJANGO_USER}" cat "$sample" >/dev/null 2>&1; then
            working_dir="${dir}"
            break
        fi
    fi
done

if [ -z "$working_dir" ]; then
    echo "WARNING: Could not find a working directory to compare with"
else
    echo "Working directory found: ${working_dir}"
    echo ""

    echo "Comparing ${working_dir}/ (WORKS) vs fastq/ (DOESN'T WORK):"
    echo "----------------------------------------"
    echo ""

    echo "${working_dir} directory:"
    ls -ld "${REMOTE_FILES_BASE}/${working_dir}"
    stat -c "  Permissions: %a, Owner: %U, Group: %G" "${REMOTE_FILES_BASE}/${working_dir}"

    echo ""
    echo "fastq directory:"
    if [ -d "${REMOTE_FILES_BASE}/fastq" ]; then
        ls -ld "${REMOTE_FILES_BASE}/fastq"
        stat -c "  Permissions: %a, Owner: %U, Group: %G" "${REMOTE_FILES_BASE}/fastq"
    else
        echo "  fastq directory not found!"
    fi

    echo ""
    echo "Sample files comparison:"
    echo "----------------------------------------"

    working_sample=$(find "${REMOTE_FILES_BASE}/${working_dir}" -type f | head -1)
    fastq_sample=$(find "${REMOTE_FILES_BASE}/fastq" -type f | head -1)

    if [ -n "$working_sample" ]; then
        echo ""
        echo "${working_dir} file (WORKS):"
        ls -l "$working_sample"
        stat -c "  Permissions: %a, Owner: %U, Group: %G" "$working_sample"
    fi

    if [ -n "$fastq_sample" ]; then
        echo ""
        echo "fastq file (DOESN'T WORK):"
        ls -l "$fastq_sample"
        stat -c "  Permissions: %a, Owner: %U, Group: %G" "$fastq_sample"
    fi
fi

echo ""
echo ""
echo "=========================================="
echo "RECOMMENDATIONS"
echo "=========================================="
echo ""

# Check if Django user is in burlo group
if sudo -u "${DJANGO_USER}" groups | grep -q burlo; then
    echo "✓ ${DJANGO_USER} is in 'burlo' group"
else
    echo "✗ ${DJANGO_USER} is NOT in 'burlo' group"
    echo ""
    echo "If working directories have group 'burlo', add user to group:"
    echo "  sudo usermod -aG burlo ${DJANGO_USER}"
    echo "  sudo systemctl restart gunicorn"
fi

echo ""
echo "To fix the fastq folder, you likely need to:"
echo ""
echo "Option 1: Match permissions to working directories"
echo "  # Example: if ${working_dir} has 755 permissions and group 'burlo'"
echo "  sudo chgrp -R burlo ${REMOTE_FILES_BASE}/fastq"
echo "  sudo chmod 755 ${REMOTE_FILES_BASE}/fastq"
echo "  sudo chmod 644 ${REMOTE_FILES_BASE}/fastq/*.fastq.gz"
echo ""
echo "Option 2: Make files world-readable (like other directories)"
echo "  sudo chmod 755 ${REMOTE_FILES_BASE}/fastq"
echo "  sudo chmod 644 ${REMOTE_FILES_BASE}/fastq/*.fastq.gz"
echo ""
echo "Option 3: Add Django user to the group that owns working files"
echo "  # Check what group owns working files above, then:"
echo "  sudo usermod -aG <group> ${DJANGO_USER}"
echo "  sudo systemctl restart gunicorn"
echo ""

echo "After applying fix, test with:"
echo "  sudo -u ${DJANGO_USER} cat ${REMOTE_FILES_BASE}/fastq/COL60_S8_1.fastq.gz > /dev/null"
echo ""
