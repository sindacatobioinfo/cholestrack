# Installing Sudoers Configuration for FASTQ File Access

## Problem

FASTQ files are owned by user `burlo` and only readable by that user. The Django application runs as a different user (e.g., `www-data`, `gunicorn`, or `ronald_moura`) and cannot access these files.

## Solution

The Django application now uses `sudo` to read FASTQ files as the `burlo` user. This requires installing a sudoers configuration file.

## Installation Steps

### Step 1: Identify the Django/Gunicorn user

Find out what user runs your Django application:

```bash
ps aux | grep gunicorn
```

Look at the first column - common users are:
- `www-data`
- `gunicorn`
- `django`
- `burlo`
- `ronald_moura`

### Step 2: Edit the sudoers configuration

Edit the sudoers configuration file to use the correct user:

```bash
cd /home/burlo/cholestrack/cholestrack
nano sudoers.d/cholestrack
```

Find these lines and uncomment the ones that match your Django user:

```
# ronald_moura ALL=(burlo) NOPASSWD: /bin/cat /home/burlo/cholestrack/*/media/remote_files/fastq/*
# ronald_moura ALL=(burlo) NOPASSWD: /bin/cp /home/burlo/cholestrack/*/media/remote_files/fastq/* /tmp/fastq_download_*
# ronald_moura ALL=(root) NOPASSWD: /bin/chmod 644 /tmp/fastq_download_*
```

For example, if your Django user is `ronald_moura`, uncomment those lines (remove the `#`).

### Step 3: Install the sudoers file

```bash
# Copy the file to sudoers.d directory
sudo cp sudoers.d/cholestrack /etc/sudoers.d/cholestrack

# Set correct permissions (required by sudo)
sudo chmod 440 /etc/sudoers.d/cholestrack

# Verify the syntax is correct
sudo visudo -c

# If syntax check passes, you should see:
# /etc/sudoers: parsed OK
# /etc/sudoers.d/cholestrack: parsed OK
```

If `visudo -c` reports an error, DO NOT proceed - fix the file first!

### Step 4: Test the configuration

Test that the Django user can now read FASTQ files as burlo:

```bash
# Replace 'ronald_moura' with your Django user
# Replace the file path with an actual FASTQ file

sudo -u ronald_moura sudo -n -u burlo cat /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz > /dev/null

# If successful, you should see no output
# If it fails, you'll see an error message
```

### Step 5: Restart Django

After installing the sudoers file, restart your Django services:

```bash
sudo systemctl restart gunicorn
sudo systemctl restart celery  # if you have celery
```

### Step 6: Test download through web interface

1. Log into the Cholestrack web interface
2. Navigate to a sample with FASTQ files
3. Try to download a FASTQ file
4. Check the logs for messages like "Using sudo to read FASTQ file as burlo"

## Verification

Check the Django logs to see if sudo is working:

```bash
# Check gunicorn logs
sudo journalctl -u gunicorn -f

# Or check application logs
tail -f /path/to/django/logs/django.log
```

You should see messages like:
```
Using sudo to read FASTQ file as burlo: COL60_S8_1.fastq.gz
File download successful (via sudo): User=ronald_moura, Patient=COL60, FileType=FASTQ, Size=...
```

## Troubleshooting

### Error: "sudo: a password is required"

This means the sudoers file is not configured correctly or not installed.
- Verify the file is at `/etc/sudoers.d/cholestrack`
- Verify permissions are `440`: `ls -l /etc/sudoers.d/cholestrack`
- Verify the correct Django user is specified in the file
- Run `sudo visudo -c` to check for syntax errors

### Error: "sudo is not configured"

The Django application couldn't find or use sudo.
- Make sure `sudo` is installed: `which sudo`
- Check that the sudoers file exists: `ls -l /etc/sudoers.d/cholestrack`
- Test manually as the Django user (see Step 4 above)

### Error: "Permission denied" still appearing

- The sudoers file may not match the actual file paths
- Check the actual path to FASTQ files: `realpath /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz`
- Update the sudoers file if paths don't match (especially symlinks)

### Downloads work for VCF/BAM but not FASTQ

This is expected! Only FASTQ files use the sudo approach. VCF/BAM/TSV files should be readable normally.

## Security Considerations

The sudoers configuration:
- ✅ Only allows reading (via `cat`) and copying (via `cp`) files
- ✅ Only allows access to FASTQ files in specific directories
- ✅ Uses NOPASSWD because it's a service account (non-interactive)
- ✅ The `-n` flag in code prevents password prompts
- ✅ Path validation prevents command injection

However:
- ⚠️ Any user who can run Django code can read FASTQ files as burlo
- ⚠️ Make sure your Django application has proper authentication
- ⚠️ Consider using Django's permission system to restrict FASTQ downloads

## Alternative Approaches (Not Implemented)

If you don't want to use sudo, consider:

1. **Add Django user to burlo's group** (simpler but gives access to all burlo's files)
2. **Use ACLs** to give specific read access
3. **Copy files to a staging area** with appropriate permissions
4. **Run a separate file-serving daemon** as burlo

The sudo approach was chosen because:
- It's secure and auditable
- It only affects FASTQ files
- It doesn't require changing file ownership/permissions on the network mount
- It's explicit about what access is granted

## How It Works

When a user downloads a FASTQ file:

1. Django receives the download request
2. Checks if file exists and is a FASTQ file
3. Checks if the file is readable by the Django user
4. If not readable (permission denied):
   - Uses `sudo -n -u burlo cat <file>` to read the file
   - Returns the file content to the user
5. If readable normally:
   - Uses normal file access (no sudo needed)

The code is in `cholestrack/files/views.py`:
- `read_file_as_owner()` function uses sudo to read files
- `download_single_file()` uses it for single FASTQ files
- `download_file()` uses it for complete FASTQ downloads

## Code Changes

The following was modified:
- Added `subprocess` import for running sudo commands
- Added `read_file_as_owner()` helper function
- Modified `download_single_file()` to use sudo for FASTQ files
- Modified `download_file()` to use sudo for FASTQ files
- Added proper error handling and logging

These changes are backward compatible:
- If files ARE readable, normal access is used
- If files are NOT readable AND file type is FASTQ, sudo is used
- Other file types (VCF, BAM, TSV) are unaffected
