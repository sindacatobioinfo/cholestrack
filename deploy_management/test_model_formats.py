#!/usr/bin/env python3
"""
Test different model name formats to find what works with google-generativeai 0.8.3
This will help identify the exact format the API expects.

Usage:
    cd /home/burlo/cholestrack/cholestrack
    source ../.venv/bin/activate
    python ../deploy_management/test_model_formats.py
"""

import os
import sys

# Add Django project to path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cholestrack'
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

try:
    import django
    django.setup()
    from django.conf import settings
    print("✓ Django loaded")
except Exception as e:
    print(f"✗ Error loading Django: {e}")
    sys.exit(1)

try:
    import google.generativeai as genai
    print(f"✓ google-generativeai version: {genai.__version__}")
except ImportError as e:
    print(f"✗ Error importing google.generativeai: {e}")
    sys.exit(1)

# Get API key
api_key = getattr(settings, 'GEMINI_API_KEY', None)
if not api_key:
    print("✗ GEMINI_API_KEY not set")
    sys.exit(1)

genai.configure(api_key=api_key)
print(f"✓ API configured (key length: {len(api_key)})")

print("\n" + "="*70)
print("STEP 1: List all available models")
print("="*70)

try:
    available_models = []
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            available_models.append(model.name)
            print(f"  ✓ {model.name}")

    if not available_models:
        print("  ✗ No models found that support generateContent")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error listing models: {e}")
    sys.exit(1)

print(f"\nFound {len(available_models)} available models")

print("\n" + "="*70)
print("STEP 2: Test different model name formats")
print("="*70)

# Test different format variations
test_formats = [
    # Format 1: Simple name (no prefix, no version)
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",

    # Format 2: With models/ prefix
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-1.5-flash",

    # Format 3: With version suffix
    "gemini-2.5-flash-002",
    "gemini-2.0-flash-002",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-001",

    # Format 4: With models/ prefix AND version suffix
    "models/gemini-2.5-flash-002",
    "models/gemini-2.0-flash-002",
    "models/gemini-1.5-flash-002",

    # Format 5: Latest stable versions
    "gemini-2.5-flash-latest",
    "models/gemini-2.5-flash-latest",
]

# Also test the first available model from the list
if available_models:
    first_model = available_models[0]
    if first_model not in test_formats:
        test_formats.insert(0, first_model)
        print(f"\nAdding first available model from API: {first_model}")

successful_models = []

for model_name in test_formats:
    print(f"\nTesting: '{model_name}'")
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )

        # Try to generate content
        response = model.generate_content("Say 'test successful'")
        result = response.text

        print(f"  ✓✓✓ SUCCESS! Response: {result[:50]}")
        successful_models.append(model_name)

    except Exception as e:
        error_msg = str(e)
        if "unexpected model name format" in error_msg:
            print(f"  ✗ Format error: unexpected model name format")
        elif "404" in error_msg or "not found" in error_msg.lower():
            print(f"  ✗ Model not found (404)")
        elif "403" in error_msg or "permission" in error_msg.lower():
            print(f"  ✗ Permission denied (403)")
        elif "400" in error_msg:
            print(f"  ✗ Bad request (400): {error_msg[:100]}")
        else:
            print(f"  ✗ Error: {error_msg[:100]}")

print("\n" + "="*70)
print("RESULTS SUMMARY")
print("="*70)

if successful_models:
    print(f"\n✓✓✓ Found {len(successful_models)} working model format(s):")
    for model in successful_models:
        print(f"  ✓ {model}")

    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    print(f"\nUpdate your .env file with:")
    print(f"  GEMINI_MODEL={successful_models[0]}")

else:
    print("\n✗✗✗ No model formats worked!")
    print("\nPossible issues:")
    print("  1. API key doesn't have access to any models")
    print("  2. Quota exceeded")
    print("  3. Region restrictions")
    print("  4. google-generativeai version incompatibility")

    print("\nTroubleshooting:")
    print("  1. Check your API key at: https://aistudio.google.com/app/apikey")
    print("  2. Verify quota at: https://aistudio.google.com/app/prompts")
    print("  3. Try upgrading: pip install --upgrade google-generativeai")

print("\n" + "="*70)
