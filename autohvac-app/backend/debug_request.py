#!/usr/bin/env python3
"""
Debug script to test the exact payload from frontend and identify validation issues
"""
import json
from datetime import datetime
from models.api import CalculationRequest
from pydantic import ValidationError

# This is the exact format the frontend sends (from useAppStore.ts lines 224-256)
frontend_payload = {
    "project": {
        "id": "project-123",
        "project_name": "Test Project",
        "zip_code": "99206",
        "building_type": "residential",
        "construction_type": "new",
        "input_method": "blueprint",
        "created_at": "2025-07-24T10:00:00.000Z",
        "updated_at": "2025-07-24T10:00:00.000Z"
    },
    "building": {
        "total_square_footage": 1500,
        "foundation_type": "slab",
        "wall_insulation": "good",
        "ceiling_insulation": "good",
        "window_type": "double",
        "building_orientation": "south",
        "stories": 1,
        "building_age": "new"
    },
    "rooms": [
        {
            "id": "room-1",
            "name": "Living Room",
            "area": 300,
            "ceiling_height": 10,
            "exterior_walls": 2,
            "window_area": 60,
            "occupants": 4,
            "equipment_load": 500,
            "room_type": "living"
        },
        {
            "id": "room-2", 
            "name": "Kitchen",
            "area": 150,
            "ceiling_height": 10,
            "exterior_walls": 1,
            "window_area": 30,
            "occupants": 2,
            "equipment_load": 800,
            "room_type": "kitchen"
        },
        {
            "id": "room-3",
            "name": "Master Bedroom", 
            "area": 200,
            "ceiling_height": 10,
            "exterior_walls": 2,
            "window_area": 40,
            "occupants": 2,
            "equipment_load": 200,
            "room_type": "bedroom"
        }
    ]
}

print("Testing frontend payload validation...")
print("=" * 50)

try:
    # Try to validate the payload exactly as frontend sends it
    request = CalculationRequest(**frontend_payload)
    print("✅ SUCCESS: Frontend payload validates correctly!")
    print(f"Project: {request.project.project_name}")
    print(f"Building: {request.building.total_square_footage} sq ft")
    print(f"Rooms: {len(request.rooms)} rooms")
    
except ValidationError as e:
    print("❌ VALIDATION ERROR:")
    print("=" * 50)
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
        print(f"Type: {error['type']}")
        print("-" * 30)
    
    print("\nDetailed error:")
    print(json.dumps(e.errors(), indent=2, default=str))

except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {e}")
    print(f"Error type: {type(e)}")

print("\n" + "=" * 50)
print("Testing individual components...")

# Test project validation separately
try:
    from models.project import ProjectInfo
    project_data = frontend_payload["project"]
    project = ProjectInfo(**project_data)
    print("✅ Project validation: OK")
except ValidationError as e:
    print("❌ Project validation failed:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")

# Test building validation separately  
try:
    from models.project import BuildingCharacteristics
    building_data = frontend_payload["building"]
    building = BuildingCharacteristics(**building_data)
    print("✅ Building validation: OK")
except ValidationError as e:
    print("❌ Building validation failed:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")

# Test rooms validation separately
try:
    from models.project import Room
    rooms_data = frontend_payload["rooms"]
    rooms = [Room(**room_data) for room_data in rooms_data]
    print("✅ Rooms validation: OK")
except ValidationError as e:
    print("❌ Rooms validation failed:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")