#!/usr/bin/env python3
"""
Test the exact scenario causing 0.34 tons cooling output
"""
import asyncio
import json
from services.enhanced_manual_j_calculator import EnhancedManualJCalculator
from services.climate_service import ClimateService

async def test_frontend_scenario():
    """Test with the exact data causing issues"""
    
    calculator = EnhancedManualJCalculator()
    climate_service = ClimateService()
    
    # Get climate data
    climate_data = await climate_service.get_climate_data("99206")
    climate_dict = {
        "summer_design_temp": climate_data.summer_design_temp,
        "winter_design_temp": climate_data.winter_design_temp,
        "humidity": 0.012,
        "zone": climate_data.zone
    }
    
    print("Testing scenario that produced 0.34 tons cooling...")
    print("=" * 60)
    
    # This is likely what's happening - very small area or missing rooms
    scenarios = [
        {
            "name": "Minimal area scenario",
            "building_data": {
                "floor_area_ft2": 100,  # Very small area
                "wall_insulation": {"effective_r": 19},
                "ceiling_insulation": 38,
                "window_schedule": {"u_value": 0.30, "shgc": 0.65},
                "air_tightness": 5.0,
                "ceiling_height": 9.0
            },
            "room_data": [{
                "name": "Single Room",
                "area_ft2": 100,
                "area": 100,
                "ceiling_height": 9.0,
                "window_area": 12,
                "exterior_walls": 2,
                "occupants": 1,
                "equipment_load": 50
            }]
        },
        {
            "name": "Empty rooms scenario",
            "building_data": {
                "floor_area_ft2": 1500,
                "wall_insulation": {"effective_r": 19},
                "ceiling_insulation": 38,
                "window_schedule": {"u_value": 0.30, "shgc": 0.65},
                "air_tightness": 5.0,
                "ceiling_height": 9.0
            },
            "room_data": []  # No rooms!
        },
        {
            "name": "Default room values scenario",
            "building_data": {
                "floor_area_ft2": 1500,
                "wall_insulation": {"effective_r": 19},
                "ceiling_insulation": 38,
                "window_schedule": {"u_value": 0.30, "shgc": 0.65},
                "air_tightness": 5.0,
                "ceiling_height": 9.0
            },
            "room_data": [
                {
                    "name": "Room 1",
                    "area_ft2": 250,  # Default area
                    "area": 250,
                    "ceiling_height": 9.0,
                    # All other values missing/default
                },
                {
                    "name": "Room 2", 
                    "area_ft2": 250,
                    "area": 250,
                    "ceiling_height": 9.0,
                }
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print("-" * 40)
        
        try:
            result = await calculator.calculate_system_loads(
                project_id=f"test-{scenario['name']}",
                building_data=scenario['building_data'],
                room_data=scenario['room_data'],
                climate_data=climate_dict
            )
            
            print(f"Building area: {scenario['building_data']['floor_area_ft2']} sq ft")
            print(f"Rooms: {len(scenario['room_data'])}")
            print(f"Cooling: {result.cooling_tons:.2f} tons ({result.total_cooling_btuh:,.0f} BTU/hr)")
            print(f"Heating: {result.heating_tons:.2f} tons ({result.total_heating_btuh:,.0f} BTU/hr)")
            
            # Check if this matches the problematic output
            if 0.3 <= result.cooling_tons <= 0.4:
                print("⚠️  THIS MATCHES THE PROBLEMATIC 0.34 TONS!")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Now test what the actual API endpoint is doing
    print("\n\nChecking API endpoint logic...")
    print("=" * 60)
    
    # Simulate the API endpoint data preparation
    from api.calculations import router
    
    # Mock request data that might be causing issues
    request_data = {
        "project": {
            "id": "test-123",
            "project_name": "Test",
            "zip_code": "99206",
            "building_type": "residential",
            "construction_type": "new",
            "input_method": "blueprint"
        },
        "building": {
            "total_square_footage": 500,  # Small value from bad extraction?
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
                "name": "Room 1",
                "area": 100,  # Very small
                "ceiling_height": 9,
                "room_type": "living"
            }
        ]
    }
    
    # Prepare data like the API does
    building_data = {
        "floor_area_ft2": request_data["building"]["total_square_footage"],
        "wall_insulation": {"effective_r": 19},
        "ceiling_insulation": 38,
        "window_schedule": {"u_value": 0.30, "shgc": 0.65},
        "air_tightness": 5.0,
        "ceiling_height": 9.0
    }
    
    room_data = []
    for room in request_data["rooms"]:
        room_data.append({
            "name": room["name"],
            "area_ft2": room["area"],
            "area": room["area"],
            "ceiling_height": room.get("ceiling_height", 9),
            "window_area": room.get("window_area", room["area"] * 0.12),
            "exterior_walls": room.get("exterior_walls", 2),
            "occupants": room.get("occupants", max(1, room["area"] // 200)),
            "equipment_load": room.get("equipment_load", room["area"] * 0.5)
        })
    
    print("API prepared data:")
    print(f"Building: {building_data['floor_area_ft2']} sq ft")
    print(f"Rooms: {room_data}")
    
    result = await calculator.calculate_system_loads(
        project_id="api-test",
        building_data=building_data,
        room_data=room_data,
        climate_data=climate_dict
    )
    
    print(f"\nAPI Result:")
    print(f"Cooling: {result.cooling_tons:.2f} tons")
    print(f"Heating: {result.heating_tons:.2f} tons")
    
    if 0.3 <= result.cooling_tons <= 0.4:
        print("\n⚠️  FOUND IT! This configuration produces the 0.34 tons issue!")
        print("The problem is: Building area is too small (500 sq ft)")

if __name__ == "__main__":
    asyncio.run(test_frontend_scenario())