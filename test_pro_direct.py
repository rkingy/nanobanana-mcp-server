#!/usr/bin/env python3
"""
Direct test of Gemini 3 Pro Image model.
Run with: GEMINI_API_KEY=your_key python test_pro_direct.py
"""
import os
import sys

# Try to load from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: Set GEMINI_API_KEY environment variable")
    print("Usage: GEMINI_API_KEY=your_key python test_pro_direct.py")
    sys.exit(1)

print(f"API Key found (first 10 chars): {api_key[:10]}...")

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

# Test 1: List models to check if Pro model exists
print("\n=== Test 1: Checking available image models ===")
try:
    for model in client.models.list():
        name = model.name
        if 'image' in name.lower() or 'pro' in name.lower():
            print(f"  Found: {name}")
except Exception as e:
    print(f"  Error listing models: {e}")

# Test 2: Try Pro model with exact documentation example
print("\n=== Test 2: Testing gemini-3-pro-image-preview ===")
try:
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=["A simple red circle on white background"],
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="1:1",
                image_size="1K"
            ),
        )
    )
    
    print(f"  SUCCESS! Response received")
    print(f"  Candidates: {len(response.candidates) if response.candidates else 0}")
    
    # Try to extract image
    if hasattr(response, 'parts') and response.parts:
        for i, part in enumerate(response.parts):
            if hasattr(part, 'text') and part.text:
                print(f"  Part {i}: Text")
            if hasattr(part, 'inline_data') and part.inline_data:
                print(f"  Part {i}: Image data ({len(part.inline_data.data)} bytes)")
                
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

# Test 3: Try Flash model for comparison
print("\n=== Test 3: Testing gemini-2.5-flash-image (for comparison) ===")
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=["A simple red circle on white background"],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
        )
    )
    
    print(f"  SUCCESS! Response received")
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'content') and candidate.content:
            parts = candidate.content.parts or []
            for i, part in enumerate(parts):
                if hasattr(part, 'inline_data') and part.inline_data:
                    print(f"  Part {i}: Image data ({len(part.inline_data.data)} bytes)")
                    
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

print("\n=== Tests complete ===")

