# FASTQ File Permission Fix Guide

## Problem
User `ronald_moura` (Django app) cannot read files in `/home/burlo/cholestrack/cholestrack/media/remote_files/fastq/`

Error: `File exists but is not readable - Permission denied`

## Quick Diagnosis

Run this on the **burlo server** (where Django is running):

```bash
# Check who owns the file
ls -l /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz

# Check if ronald_moura can read it
sudo -u ronald_moura cat /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz > /dev/null

# If that fails, you have a permission issue
```

## Quick Fixes (choose one)

### Solution 1: Add user to file owner's group (RECOMMENDED)

```bash
# Find out what group owns the files
stat -c '%G' /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz

# Add ronald_moura to that group (replace <group> with actual group name)
sudo usermod -aG <group> ronald_moura

# Verify
groups ronald_moura

# Restart Django services for changes to take effect
sudo systemctl restart gunicorn
sudo systemctl restart celery  # if you have celery
```

### Solution 2: Make files world-readable (LESS SECURE)

```bash
# Make directory executable and files readable
sudo chmod a+rX /home/burlo/cholestrack/cholestrack/media/remote_files/fastq
sudo chmod a+r /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/*.fastq.gz

# No need to restart services
```

### Solution 3: Fix network mount permissions

If this is an **NFS mount**:

```bash
# On the SERVER exporting the files, edit /etc/exports:
/path/to/fastq *(rw,sync,no_root_squash,all_squash,anonuid=1000,anongid=1000)

# On the CLIENT (burlo server), remount:
sudo mount -o remount /home/burlo/cholestrack/cholestrack/media/remote_files
```

If this is a **CIFS/SMB mount**:

```bash
# Edit /etc/fstab on burlo server and add uid/gid:
//server/share /home/burlo/cholestrack/cholestrack/media/remote_files cifs credentials=/path/to/creds,uid=ronald_moura,gid=ronald_moura,file_mode=0644,dir_mode=0755 0 0

# Remount
sudo umount /home/burlo/cholestrack/cholestrack/media/remote_files
sudo mount -a
```

### Solution 4: Use ACLs (if filesystem supports it)

```bash
# Give ronald_moura specific read access
sudo setfacl -R -m u:ronald_moura:rX /home/burlo/cholestrack/cholestrack/media/remote_files/fastq
sudo setfacl -R -m d:u:ronald_moura:rX /home/burlo/cholestrack/cholestrack/media/remote_files/fastq

# Verify
getfacl /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz
```

## Full Diagnostic Script

For detailed diagnostics, run:

```bash
cd /home/burlo/cholestrack/cholestrack
./fix_fastq_permissions.sh
```

## Testing the Fix

After applying any fix:

```bash
# Test as the Django user
sudo -u ronald_moura cat /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/COL60_S8_1.fastq.gz > /dev/null

# Should output nothing if successful, or "Permission denied" if still broken
```

Then try downloading the file through the Django web interface again.

## Still Not Working?

Check:

1. **SELinux** (if enabled):
   ```bash
   sudo setenforce 0  # Temporarily disable to test
   # If that fixes it, adjust SELinux policies instead of disabling
   ```

2. **AppArmor** (if enabled):
   ```bash
   sudo systemctl status apparmor
   # Check /var/log/syslog for denials
   ```

3. **Mount is actually working**:
   ```bash
   mount | grep remote_files
   df -h | grep remote_files
   ls -la /home/burlo/cholestrack/cholestrack/media/remote_files/fastq/
   ```

4. **Django user is correct**:
   ```bash
   # Check what user gunicorn is running as
   ps aux | grep gunicorn
   ```

## Code Changes Already Applied

The Django code has been updated to:
- ✅ Check file permissions before attempting to open files
- ✅ Provide clear error messages when permissions are denied
- ✅ Log detailed information for debugging

This is why you're now seeing the clear error message instead of a generic download failure.
