#!/usr/bin/env python3
"""
Trace through the calculation to find where values are going wrong
"""
import asyncio
import logging
from services.enhanced_manual_j_calculator import EnhancedManualJCalculator
from services.climate_service import ClimateService

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def trace_calculation():
    calculator = EnhancedManualJCalculator()
    climate_service = ClimateService()
    
    # Get real climate data for Spokane
    climate_data = await climate_service.get_climate_data("99206")
    climate_dict = {
        "summer_design_temp": climate_data.summer_design_temp,
        "winter_design_temp": climate_data.winter_design_temp,
        "humidity": 0.012,
        "zone": climate_data.zone
    }
    
    print(f"Climate data: Summer={climate_dict['summer_design_temp']}°F, Winter={climate_dict['winter_design_temp']}°F")
    
    # Minimal test case - single 250 sq ft room
    building_data = {
        "floor_area_ft2": 250,
        "wall_insulation": {"effective_r": 19},
        "ceiling_insulation": 38,
        "window_schedule": {"u_value": 0.30, "shgc": 0.65},
        "air_tightness": 5.0,
        "ceiling_height": 9.0
    }
    
    room_data = [{
        "name": "Test Room",
        "area_ft2": 250,
        "area": 250,
        "ceiling_height": 9.0,
        "window_area": 30,  # 12% of floor area
        "exterior_walls": 2,
        "occupants": 2,
        "equipment_load": 125  # 0.5 W/sq ft
    }]
    
    print("\nInput data:")
    print(f"  Building area: {building_data['floor_area_ft2']} sq ft")
    print(f"  Room area: {room_data[0]['area_ft2']} sq ft")
    print(f"  Ceiling height: {room_data[0]['ceiling_height']} ft")
    print(f"  Window area: {room_data[0]['window_area']} sq ft")
    
    # Calculate
    result = await calculator.calculate_system_loads(
        project_id="test-trace",
        building_data=building_data,
        room_data=room_data,
        climate_data=climate_dict
    )
    
    print("\n=== CALCULATION RESULTS ===")
    print(f"Total heating: {result.total_heating_btuh:,.0f} BTU/hr ({result.heating_tons:.2f} tons)")
    print(f"Total cooling: {result.total_cooling_btuh:,.0f} BTU/hr ({result.cooling_tons:.2f} tons)")
    
    print("\n=== DESIGN TEMPERATURES ===")
    design_temps = calculator._calculate_design_temperatures(climate_dict)
    print(f"Heating temp diff: {design_temps['heating_temp_diff']}°F")
    print(f"Cooling temp diff: {design_temps['cooling_temp_diff']}°F")
    
    print("\n=== ROOM COMPONENT BREAKDOWN ===")
    for room_load in result.room_loads:
        print(f"\nRoom: {room_load.room_name}")
        print(f"  Total heating: {room_load.total_heating_btuh:,.0f} BTU/hr")
        print(f"  Total cooling: {room_load.total_cooling_btuh:,.0f} BTU/hr")
        
        print("\n  Components:")
        for comp in room_load.components:
            print(f"    {comp.component_type}:")
            print(f"      Heating: {comp.heating_btuh:,.0f} BTU/hr")
            print(f"      Cooling: {comp.cooling_btuh:,.0f} BTU/hr")
            if comp.details:
                for key, value in comp.details.items():
                    if isinstance(value, (int, float)):
                        print(f"      {key}: {value:,.2f}")
                    else:
                        print(f"      {key}: {value}")
    
    print("\n=== VALIDATION ===")
    print(f"Heating density: {result.validation_results['heating_density_btuh_sqft']:.1f} BTU/hr/sq ft")
    print(f"Cooling density: {result.validation_results['cooling_density_btuh_sqft']:.1f} BTU/hr/sq ft")
    print(f"Warnings: {result.validation_results['warnings']}")
    
    # Manual check of wall calculation
    print("\n=== MANUAL WALL CALCULATION CHECK ===")
    perimeter = 4 * (250 ** 0.5)  # Square room assumption
    wall_height = 9.0
    exterior_walls = 0.5  # 2 of 4 walls
    gross_wall_area = perimeter * wall_height * exterior_walls
    window_area = 30
    net_wall_area = gross_wall_area - window_area
    wall_u = 1/19
    heating_delta_t = 70 - climate_dict['winter_design_temp']
    cooling_delta_t = climate_dict['summer_design_temp'] - 75
    
    print(f"Perimeter: {perimeter:.1f} ft")
    print(f"Gross wall area: {gross_wall_area:.1f} sq ft")
    print(f"Net wall area: {net_wall_area:.1f} sq ft")
    print(f"Wall U-factor: {wall_u:.4f}")
    print(f"Heating ΔT: {heating_delta_t}°F")
    print(f"Cooling ΔT: {cooling_delta_t}°F")
    print(f"Expected wall heating load: {net_wall_area * wall_u * heating_delta_t:.0f} BTU/hr")
    print(f"Expected wall cooling load: {net_wall_area * wall_u * cooling_delta_t:.0f} BTU/hr")

if __name__ == "__main__":
    asyncio.run(trace_calculation())