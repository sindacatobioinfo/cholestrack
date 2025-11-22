#!/usr/bin/env python3
"""
Diagnostic script to test Gemini API configuration and list available models.
Run this to verify your GEMINI_API_KEY and see which models you can use.

Usage:
    cd /home/burlo/cholestrack/cholestrack
    source ../.venv/bin/activate
    python ../deploy_management/test_gemini_models.py
"""

import os
import sys

# Add Django project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../cholestrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

try:
    import django
    django.setup()
    from django.conf import settings
    print("✓ Django loaded successfully")
except Exception as e:
    print(f"✗ Error loading Django: {e}")
    sys.exit(1)

try:
    import google.generativeai as genai
    print(f"✓ google.generativeai version: {genai.__version__}")
except ImportError as e:
    print(f"✗ Error importing google.generativeai: {e}")
    print("  Install with: pip install google-generativeai==0.8.3")
    sys.exit(1)

# Check API key
api_key = getattr(settings, 'GEMINI_API_KEY', None)
if not api_key:
    print("✗ GEMINI_API_KEY not set in environment variables")
    sys.exit(1)
else:
    print(f"✓ GEMINI_API_KEY found (length: {len(api_key)} chars)")

# Configure API
try:
    genai.configure(api_key=api_key)
    print("✓ Gemini API configured")
except Exception as e:
    print(f"✗ Error configuring API: {e}")
    sys.exit(1)

# List available models
print("\n" + "="*60)
print("Available Gemini models for generateContent:")
print("="*60)

try:
    models_found = False
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            models_found = True
            print(f"\nModel: {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")

    if not models_found:
        print("✗ No models found that support generateContent")
        print("  This could indicate an API key issue or account restrictions")
except Exception as e:
    print(f"✗ Error listing models: {e}")
    print("  Check your API key and internet connection")
    sys.exit(1)

# Test model initialization
print("\n" + "="*60)
print("Testing model initialization:")
print("="*60)

configured_model = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
print(f"\nConfigured GEMINI_MODEL: {configured_model}")

# Test without prefix
try:
    model_name = configured_model.replace('models/', '', 1) if configured_model.startswith('models/') else configured_model
    print(f"Testing with model name: {model_name}")

    model = genai.GenerativeModel(
        model_name=model_name,
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    )
    print(f"✓ Model initialized successfully: {model_name}")

    # Test a simple generation
    print("\nTesting content generation with 'Hello, how are you?'...")
    response = model.generate_content("Hello, how are you?")
    print(f"✓ Content generation successful!")
    print(f"  Response: {response.text[:100]}...")

except Exception as e:
    print(f"✗ Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Check if the model name is correct and available")
    print("  2. Try a different model like 'gemini-1.5-pro' or 'gemini-2.0-flash'")
    print("  3. Verify your API key has access to this model")
    print("  4. Check if you've exceeded API quota limits")

print("\n" + "="*60)
print("Diagnostic complete!")
print("="*60)
