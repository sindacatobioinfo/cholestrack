#!/usr/bin/env python3
"""
Quick script to verify Django is loading .env file correctly.
Shows what values are actually being read for GEMINI settings.

Usage:
    cd /home/burlo/cholestrack/cholestrack
    source ../.venv/bin/activate
    python ../deploy_management/check_env_vars.py
"""

import os
import sys

# Add Django project to path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cholestrack'
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

print("=" * 60)
print("Environment Variable Diagnostics")
print("=" * 60)
print(f"\nProject directory: {project_dir}")
print(f".env file location: {os.path.join(project_dir, '.env')}")
print(f".env file exists: {os.path.exists(os.path.join(project_dir, '.env'))}")

# Load Django
try:
    import django
    django.setup()
    from django.conf import settings
    print("\n✓ Django loaded successfully")
except Exception as e:
    print(f"\n✗ Error loading Django: {e}")
    sys.exit(1)

# Check what values Django actually loaded
print("\n" + "=" * 60)
print("Django Settings Values")
print("=" * 60)

gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
gemini_model = getattr(settings, 'GEMINI_MODEL', None)

print(f"\nGEMINI_API_KEY:")
if gemini_api_key:
    print(f"  ✓ Set (length: {len(gemini_api_key)} chars)")
    print(f"  Preview: {gemini_api_key[:10]}...{gemini_api_key[-4:]}")
else:
    print(f"  ✗ NOT SET or empty!")
    print(f"  This will cause API errors")

print(f"\nGEMINI_MODEL:")
print(f"  Value: '{gemini_model}'")

# Also check if it's reading from system env
sys_gemini_model = os.environ.get('GEMINI_MODEL', 'NOT SET')
print(f"\nSystem environment GEMINI_MODEL: '{sys_gemini_model}'")

if gemini_model != sys_gemini_model and sys_gemini_model != 'NOT SET':
    print("  ⚠ WARNING: Django setting differs from system environment!")

# Check .env file content directly
env_file_path = os.path.join(project_dir, '.env')
if os.path.exists(env_file_path):
    print("\n" + "=" * 60)
    print(".env File Content (GEMINI variables only)")
    print("=" * 60)
    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GEMINI'):
                    # Mask API key for security
                    if 'API_KEY' in line:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            print(f"{parts[0]}=[REDACTED]")
                    else:
                        print(line)
    except Exception as e:
        print(f"Error reading .env file: {e}")
else:
    print("\n⚠ WARNING: .env file not found!")
    print(f"Expected location: {env_file_path}")
    print("Create it with:")
    print(f"  nano {env_file_path}")
    print("\nRequired content:")
    print("  GEMINI_API_KEY=your_api_key_here")
    print("  GEMINI_MODEL=gemini-2.5-flash")

print("\n" + "=" * 60)
print("Recommendations")
print("=" * 60)

if not gemini_api_key:
    print("\n✗ Add GEMINI_API_KEY to your .env file")

if gemini_model == 'gemini-1.5-flash':
    print("\n⚠ Using default model (gemini-1.5-flash)")
    print("  If you want gemini-2.5-flash, add to .env:")
    print("  GEMINI_MODEL=gemini-2.5-flash")

if gemini_model == 'gemini-2.5-flash':
    print(f"\n✓ Using gemini-2.5-flash model")
    print("  This is a valid model name")
    print("  If you get 400 errors, check if your API key has access to this model")

print("\n" + "=" * 60)
print("Next Steps")
print("=" * 60)
print("\n1. Verify .env file has correct values")
print("2. Restart gunicorn: sudo systemctl restart gunicorn")
print("3. Restart celery: sudo systemctl restart celery")
print("4. Run test_gemini_models.py to verify API connectivity")
print()
