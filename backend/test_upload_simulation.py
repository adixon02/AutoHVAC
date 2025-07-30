#!/usr/bin/env python3
"""
Simulate the upload validation logic
"""

import os
import sys

# Configuration
AI_PARSING_ENABLED = os.getenv("AI_PARSING_ENABLED", "true").lower() != "false"
LEGACY_ELEMENT_LIMIT = int(os.getenv("LEGACY_ELEMENT_LIMIT", "20000"))
FILE_SIZE_WARNING_MB = int(os.getenv("FILE_SIZE_WARNING_MB", "20"))

def simulate_upload_validation(file_size_mb: float, element_counts: list):
    """Simulate what happens during upload"""
    print(f"\n=== Upload Simulation ===")
    print(f"File size: {file_size_mb}MB")
    print(f"Element counts by page: {element_counts}")
    print(f"Total elements: {sum(element_counts):,}")
    print(f"AI parsing enabled: {AI_PARSING_ENABLED}")
    
    # File size check
    if file_size_mb > 50:
        print("\n❌ REJECTED: File size exceeds 50MB limit")
        return False
    
    # Large file warning
    if file_size_mb > FILE_SIZE_WARNING_MB:
        print(f"\n⚠️  WARNING: Large blueprint detected ({file_size_mb}MB)")
        print("   Message to user: 'AI processing may take 2-3 minutes. Please do not refresh or leave the page.'")
    
    # Complexity check
    max_elements = max(element_counts) if element_counts else 0
    
    if AI_PARSING_ENABLED:
        print(f"\n✅ AI-FIRST MODE: Complexity check skipped")
        print(f"   Max elements per page: {max_elements:,} (no limit)")
        print(f"   Will use GPT-4V for parsing")
        return True
    else:
        if max_elements > LEGACY_ELEMENT_LIMIT:
            print(f"\n❌ LEGACY MODE: Complexity check failed")
            print(f"   Max elements per page: {max_elements:,} (exceeds {LEGACY_ELEMENT_LIMIT:,} limit)")
            print(f"   Error: 'Blueprint is too complex for traditional parsing. AI parsing is recommended.'")
            return False
        else:
            print(f"\n✅ LEGACY MODE: Complexity check passed")
            print(f"   Max elements per page: {max_elements:,} (under {LEGACY_ELEMENT_LIMIT:,} limit)")
            return True

# Test cases
print("=== Testing AI-First Upload Validation ===")

# Test 1: The problematic blueprint
print("\n1. Complex AutoCAD Blueprint (blueprint-example-99206.pdf)")
simulate_upload_validation(1.36, [14220, 38159, 21829, 15000])

# Test 2: Large file
print("\n2. Large Blueprint")
simulate_upload_validation(25, [5000, 8000, 6000])

# Test 3: Very large file
print("\n3. Too Large File")
simulate_upload_validation(55, [1000, 2000])

# Test 4: Simple blueprint
print("\n4. Simple Blueprint")
simulate_upload_validation(0.5, [500, 800, 600])

# Test with AI disabled
print("\n\n=== Testing with AI DISABLED ===")
AI_PARSING_ENABLED = False

print("\n1. Complex AutoCAD Blueprint (AI disabled)")
simulate_upload_validation(1.36, [14220, 38159, 21829, 15000])