#!/usr/bin/env python3
"""
Debug script to test potential issues with frontend data conversion
"""
import json
from datetime import datetime
from models.api import CalculationRequest
from pydantic import ValidationError

# Test with potential problematic data types that frontend might send
problematic_payload = {
    "project": {
        "id": "project-1753374517984",  # Long numeric ID from frontend
        "project_name": "test",
        "zip_code": "99206",
        "building_type": "residential",
        "construction_type": "new", 
        "input_method": "blueprint",
        # These dates might come as strings from JSON
        "created_at": "2025-07-24T16:28:37.984Z",  # ISO string format
        "updated_at": "2025-07-24T16:28:37.984Z"
    },
    "building": {
        "total_square_footage": 1500.0,  # Might be float instead of int
        "foundation_type": "slab",
        "wall_insulation": "good",
        "ceiling_insulation": "good", 
        "window_type": "double",
        "building_orientation": "south",
        "stories": 1.0,  # Might be float instead of int
        "building_age": "new"
    },
    "rooms": [
        {
            "id": "room-1",
            "name": "Living Room",
            "area": 300.5,  # Float area
            "ceiling_height": 10.0,  # Float height
            "exterior_walls": 2.0,  # Float walls  
            "window_area": 60.0,  # Float window area
            "occupants": 4.0,  # Float occupants
            "equipment_load": 500.0,  # Float equipment load
            "room_type": "living"
        }
    ]
}

print("Testing potentially problematic frontend data...")
print("=" * 60)

try:
    request = CalculationRequest(**problematic_payload)
    print("✅ SUCCESS: Problematic payload validates correctly!")
    
except ValidationError as e:
    print("❌ VALIDATION ERROR with problematic data:")
    print("=" * 60)
    for error in e.errors():
        print(f"Field: {'.'.join(str(x) for x in error['loc'])}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
        print(f"Type: {error['type']}")
        print("-" * 30)

# Test with empty/null values that might come from blueprint processing
empty_blueprint_payload = {
    "project": {
        "id": "project-1753374517984",
        "project_name": "test",
        "zip_code": "99206", 
        "building_type": "residential",
        "construction_type": "new",
        "input_method": "blueprint",
        "created_at": "2025-07-24T16:28:37.984Z",
        "updated_at": "2025-07-24T16:28:37.984Z"
    },
    "building": {
        "total_square_footage": 0,  # Zero area from failed blueprint extraction
        "foundation_type": "slab",
        "wall_insulation": "good",
        "ceiling_insulation": "good",
        "window_type": "double", 
        "building_orientation": "south",
        "stories": 1,
        "building_age": "new"
    },
    "rooms": []  # Empty rooms array
}

print("\nTesting empty blueprint data...")
print("=" * 60)
try:
    request = CalculationRequest(**empty_blueprint_payload)
    print("✅ SUCCESS: Empty blueprint data validates!")
    
except ValidationError as e:
    print("❌ VALIDATION ERROR with empty blueprint data:")
    for error in e.errors():
        print(f"Field: {'.'.join(str(x) for x in error['loc'])}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
        print(f"Type: {error['type']}")
        print("-" * 30)

# Test with missing climate data (frontend doesn't send climate in CalculationRequest)
print("\nChecking CalculationRequest model structure...")
from models.api import CalculationRequest
import inspect

sig = inspect.signature(CalculationRequest)
print(f"CalculationRequest fields: {list(sig.parameters.keys())}")

# Check if there are any extra fields that shouldn't be there
print("\nField annotations:")
for field_name, field_info in CalculationRequest.model_fields.items():
    print(f"  {field_name}: {field_info.annotation}")