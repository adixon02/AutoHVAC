#!/usr/bin/env python3
"""
Test script to verify AI-first configuration
"""

import os
import sys

# Test configuration
print("=== AI-First Configuration Test ===\n")

# Check environment variables
ai_enabled = os.getenv("AI_PARSING_ENABLED", "true").lower() != "false"
legacy_limit = int(os.getenv("LEGACY_ELEMENT_LIMIT", "20000"))
warning_mb = int(os.getenv("FILE_SIZE_WARNING_MB", "20"))
use_gpt4v = os.getenv("USE_GPT4V_PARSING", "false").lower() == "true"  # Old flag
openai_key = os.getenv("OPENAI_API_KEY", "")

print(f"AI_PARSING_ENABLED: {ai_enabled} (default: true)")
print(f"LEGACY_ELEMENT_LIMIT: {legacy_limit:,} elements")
print(f"FILE_SIZE_WARNING_MB: {warning_mb}MB")
print(f"USE_GPT4V_PARSING (old): {use_gpt4v}")
print(f"OPENAI_API_KEY set: {'Yes' if openai_key else 'No'}")

print(f"\n✅ AI-first mode is {'ENABLED' if ai_enabled else 'DISABLED'}")

# Test parsing path logic
print("\n=== Parsing Path Logic ===")
print(f"1. Complex blueprint (40k elements):")
print(f"   - AI enabled: Will use GPT-4V (no element check)")
print(f"   - AI disabled: Will fail validation (exceeds {legacy_limit:,} limit)")

print(f"\n2. Large file (25MB):")
print(f"   - Will show warning: 'Large blueprint detected. AI processing may take 2-3 minutes.'")
print(f"   - Upload allowed (under 50MB limit)")

print(f"\n3. AI parsing fails:")
print(f"   - Falls back to legacy parser")
print(f"   - User sees: 'AI parsing temporarily unavailable, using traditional parsing as backup.'")

# Recommendations
print("\n=== Recommendations ===")
if not ai_enabled:
    print("⚠️  AI parsing is disabled. Set AI_PARSING_ENABLED=true for best results.")
if not openai_key:
    print("⚠️  OPENAI_API_KEY not set. AI parsing will fail without it.")
if use_gpt4v and not ai_enabled:
    print("⚠️  Conflicting settings: USE_GPT4V_PARSING=true but AI_PARSING_ENABLED=false")

print("\n✅ Configuration test complete.")