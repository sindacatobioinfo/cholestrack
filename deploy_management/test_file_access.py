#!/usr/bin/env python3
"""
Diagnostic script to test access to network-mounted TSV files.
Tests permissions, file existence, and actual file reading.

Usage:
    cd /home/burlo/cholestrack/cholestrack
    source ../.venv/bin/activate
    python ../deploy_management/test_file_access.py
"""

import os
import sys
from pathlib import Path

# Add Django project to path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cholestrack'
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

print("=" * 70)
print("Network File Access Diagnostics")
print("=" * 70)

# Load Django
try:
    import django
    django.setup()
    from files.models import AnalysisFileLocation
    from ai_agent.tsv_loader import load_tsv_preview
    print("\n✓ Django loaded successfully")
except Exception as e:
    print(f"\n✗ Error loading Django: {e}")
    sys.exit(1)

# Get current user info
print(f"\nRunning as user: {os.getenv('USER', 'unknown')}")
print(f"Process UID: {os.getuid()}")
print(f"Process GID: {os.getgid()}")
print(f"Process groups: {os.getgroups()}")

# Check mount point
base_path = Path("/media/remote_files")
print(f"\n" + "=" * 70)
print("Checking Base Mount Point")
print("=" * 70)
print(f"\nBase path: {base_path}")
print(f"Exists: {base_path.exists()}")
print(f"Is directory: {base_path.is_dir()}")
print(f"Is mount point: {base_path.is_mount()}")

if base_path.exists():
    try:
        stat_info = base_path.stat()
        print(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
        print(f"Owner UID: {stat_info.st_uid}")
        print(f"Owner GID: {stat_info.st_gid}")

        # Check if we can list directory
        print("\nTrying to list directory...")
        items = list(base_path.iterdir())
        print(f"✓ Can list directory - found {len(items)} items")
        if items:
            print(f"  First few items: {[item.name for item in items[:5]]}")
    except PermissionError as e:
        print(f"✗ Permission denied: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("✗ Base path does not exist!")

# Get a sample TSV file from database
print(f"\n" + "=" * 70)
print("Testing Sample TSV Files")
print("=" * 70)

try:
    tsv_files = AnalysisFileLocation.objects.filter(
        file_type='TSV',
        is_active=True
    ).values('sample_id', 'file_path')[:5]

    if not tsv_files:
        print("\n✗ No TSV files found in database")
        sys.exit(1)

    print(f"\nFound {len(tsv_files)} TSV files to test\n")

    for idx, file_info in enumerate(tsv_files, 1):
        sample_id = file_info['sample_id']
        relative_path = file_info['file_path']
        full_path = f"/media/remote_files/{relative_path}"

        print(f"\n{'='*70}")
        print(f"Test {idx}: Sample {sample_id}")
        print(f"{'='*70}")
        print(f"Relative path: {relative_path}")
        print(f"Full path: {full_path}")

        # Check if file exists
        file_path = Path(full_path)
        print(f"\nFile exists: {file_path.exists()}")
        print(f"Is file: {file_path.is_file()}")

        if file_path.exists():
            try:
                # Get file info
                stat_info = file_path.stat()
                print(f"File size: {stat_info.st_size / (1024*1024):.2f} MB")
                print(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
                print(f"Owner UID: {stat_info.st_uid}")
                print(f"Owner GID: {stat_info.st_gid}")

                # Check if readable
                print(f"Readable: {os.access(full_path, os.R_OK)}")

                # Try to open and read first line
                print("\nTrying to open file...")
                with open(full_path, 'r') as f:
                    first_line = f.readline()
                    print(f"✓ Successfully opened file")
                    print(f"  First line length: {len(first_line)} chars")
                    print(f"  Preview: {first_line[:100]}...")

                # Try using the TSV loader
                print("\nTrying TSV loader...")
                df, error = load_tsv_preview(full_path, num_rows=2)
                if df is not None:
                    print(f"✓ TSV loader successful!")
                    print(f"  Columns: {len(df.columns)}")
                    print(f"  Rows: {len(df)}")
                    print(f"  First few columns: {list(df.columns[:5])}")
                else:
                    print(f"✗ TSV loader failed: {error}")

            except PermissionError as e:
                print(f"\n✗ Permission denied reading file: {e}")
                print("\nPossible solutions:")
                print("  1. Add the Django user to the group that owns the files")
                print("  2. Change file permissions: chmod 644 <file>")
                print("  3. Change directory permissions: chmod 755 <directory>")
            except Exception as e:
                print(f"\n✗ Error reading file: {e}")
        else:
            print(f"\n✗ File not found at {full_path}")

            # Try to find it
            print("\nSearching for file in base directory...")
            try:
                for item in base_path.rglob(file_path.name):
                    print(f"  Found at: {item}")
            except Exception as e:
                print(f"  Search failed: {e}")

except Exception as e:
    print(f"\n✗ Error querying database: {e}")

# Final recommendations
print(f"\n" + "=" * 70)
print("Recommendations")
print("=" * 70)

print("""
If files are not accessible:

1. Check mount is working:
   mount | grep remote_files
   df -h | grep remote_files

2. Test as the Django user:
   sudo -u burlo ls -la /media/remote_files/
   sudo -u burlo cat /media/remote_files/path/to/file.txt

3. Fix permissions if needed:
   # For NFS mounts
   sudo chmod 755 /media/remote_files
   sudo chmod -R 644 /media/remote_files/*/*.txt

   # For CIFS/SMB mounts, add to /etc/fstab:
   //server/share /media/remote_files cifs uid=burlo,gid=burlo,... 0 0

4. Check Django user is in correct group:
   groups burlo
   sudo usermod -aG <group-with-file-access> burlo

5. Restart services after permission changes:
   sudo systemctl restart gunicorn
   sudo systemctl restart celery
""")

print("=" * 70)
