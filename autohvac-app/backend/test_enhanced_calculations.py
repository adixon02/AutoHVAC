"""
Test Enhanced Manual J Calculations
Validate improvements against 99206 blueprint data
Compare old vs new calculation results
"""
import asyncio
import logging
from services.enhanced_manual_j_calculator import EnhancedManualJCalculator
from services.climate_service import ClimateService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enhanced_calculator():
    """Test enhanced calculator with realistic 99206 blueprint data"""
    
    logger.info("=== TESTING ENHANCED MANUAL J CALCULATOR ===")
    
    # Initialize services
    calculator = EnhancedManualJCalculator()
    climate_service = ClimateService()
    
    # Get Spokane, WA climate data (99206)
    climate_data_obj = await climate_service.get_climate_data("99206")
    climate_data = {
        "summer_design_temp": climate_data_obj.summer_design_temp if climate_data_obj else 89,
        "winter_design_temp": climate_data_obj.winter_design_temp if climate_data_obj else 5,
        "humidity": 0.012,  # Typical for Spokane
        "zone": climate_data_obj.zone if climate_data_obj else "5A"
    }
    
    logger.info(f"Climate data: {climate_data}")
    
    # Realistic building data for 99206 blueprint (1480 sq ft home)
    building_data = {
        "floor_area_ft2": 1480,
        "wall_insulation": {"effective_r": 21},  # R-21 typical for newer construction
        "ceiling_insulation": 49,  # R-49 attic insulation
        "window_schedule": {"u_value": 0.30, "shgc": 0.65, "total_area": 178},  # 12% of floor area
        "air_tightness": 3.5,  # 3.5 ACH50 for good construction
        "foundation_type": "slab"
    }
    
    # Realistic room data (based on typical 1480 sq ft layout)
    room_data = [
        {
            "name": "Living Room",
            "area_ft2": 320,
            "length_ft": 20,
            "width_ft": 16,
            "perimeter_ft": 72,
            "ceiling_height": 9.0,
            "window_area": 48,  # Large living room windows
            "window_orientations": ["south", "west"],
            "exterior_walls": 2,
            "occupants": 3,
            "equipment_watts": 200
        },
        {
            "name": "Kitchen",
            "area_ft2": 200,
            "length_ft": 12,
            "width_ft": 16.67,
            "perimeter_ft": 57.34,
            "ceiling_height": 9.0,
            "window_area": 16,  # Kitchen window over sink
            "window_orientations": ["north"],
            "exterior_walls": 2,
            "occupants": 1,
            "equipment_watts": 500  # High for appliances
        },
        {
            "name": "Master Bedroom",
            "area_ft2": 280,
            "length_ft": 14,
            "width_ft": 20,
            "perimeter_ft": 68,
            "ceiling_height": 9.0,
            "window_area": 36,  # Bedroom windows
            "window_orientations": ["east", "south"],
            "exterior_walls": 2,
            "occupants": 2,
            "equipment_watts": 150
        },
        {
            "name": "Bedroom 2",
            "area_ft2": 180,
            "length_ft": 12,
            "width_ft": 15,
            "perimeter_ft": 54,
            "ceiling_height": 9.0,
            "window_area": 24,
            "window_orientations": ["east"],
            "exterior_walls": 2,
            "occupants": 1,
            "equipment_watts": 100
        },
        {
            "name": "Bedroom 3",
            "area_ft2": 160,
            "length_ft": 10,
            "width_ft": 16,
            "perimeter_ft": 52,
            "ceiling_height": 9.0,
            "window_area": 20,
            "window_orientations": ["north"],
            "exterior_walls": 2,
            "occupants": 1,
            "equipment_watts": 100
        },
        {
            "name": "Bathrooms",
            "area_ft2": 120,
            "length_ft": 12,
            "width_ft": 10,
            "perimeter_ft": 44,
            "ceiling_height": 9.0,
            "window_area": 8,
            "window_orientations": ["north"],
            "exterior_walls": 1,
            "occupants": 0,
            "equipment_watts": 200  # Exhaust fans, lighting
        },
        {
            "name": "Hallways",
            "area_ft2": 220,
            "length_ft": 40,  # Total hallway length
            "width_ft": 5.5,
            "perimeter_ft": 91,
            "ceiling_height": 9.0,
            "window_area": 0,  # No windows in hallways
            "window_orientations": [],
            "exterior_walls": 0,  # Interior space
            "occupants": 0,
            "equipment_watts": 50
        }
    ]
    
    logger.info(f"Building: {building_data['floor_area_ft2']} sq ft with {len(room_data)} zones")
    
    # Perform enhanced calculation
    try:
        system_calculation = await calculator.calculate_system_loads(
            project_id="test-99206",
            building_data=building_data,
            room_data=room_data,
            climate_data=climate_data
        )
        
        # Display results
        logger.info("=" * 50)
        logger.info("ENHANCED CALCULATION RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total Heating Load: {system_calculation.total_heating_btuh:,.0f} BTU/hr")
        logger.info(f"Total Cooling Load: {system_calculation.total_cooling_btuh:,.0f} BTU/hr")
        logger.info(f"Heating Capacity: {system_calculation.heating_tons:.1f} tons")
        logger.info(f"Cooling Capacity: {system_calculation.cooling_tons:.1f} tons")
        
        # Calculate load densities
        floor_area = building_data["floor_area_ft2"]
        heating_density = system_calculation.total_heating_btuh / floor_area
        cooling_density = system_calculation.total_cooling_btuh / floor_area
        
        logger.info(f"Heating Density: {heating_density:.1f} BTU/hr/sq ft")
        logger.info(f"Cooling Density: {cooling_density:.1f} BTU/hr/sq ft")
        
        # Room-by-room breakdown
        logger.info("\nROOM-BY-ROOM BREAKDOWN:")
        for room_load in system_calculation.room_loads:
            logger.info(f"{room_load.room_name}:")
            logger.info(f"  Heating: {room_load.total_heating_btuh:,.0f} BTU/hr")
            logger.info(f"  Cooling: {room_load.total_cooling_btuh:,.0f} BTU/hr")
            
            # Show component breakdown for first room as example
            if room_load.room_name == "Living Room":
                logger.info("  Component breakdown:")
                for component in room_load.components:
                    logger.info(f"    {component.component_type}: "
                              f"H={component.heating_btuh:.0f}, C={component.cooling_btuh:.0f} BTU/hr")
        
        # Validation results
        logger.info("\nVALIDATION RESULTS:")
        validation = system_calculation.validation_results
        logger.info(f"Heating density: {validation['heating_density_btuh_sqft']:.1f} BTU/hr/sq ft")
        logger.info(f"Cooling density: {validation['cooling_density_btuh_sqft']:.1f} BTU/hr/sq ft")
        logger.info(f"Heating tons/1000 sq ft: {validation['heating_tons_per_1000sqft']:.2f}")
        logger.info(f"Cooling tons/1000 sq ft: {validation['cooling_tons_per_1000sqft']:.2f}")
        
        if validation["warnings"]:
            logger.warning("Validation warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
        else:
            logger.info("✓ All validation checks passed")
        
        # Assumptions
        logger.info("\nCALCULATION ASSUMPTIONS:")
        for assumption in system_calculation.calculation_assumptions:
            logger.info(f"  - {assumption}")
        
        # Compare to problematic original results
        logger.info("\n" + "=" * 50)
        logger.info("COMPARISON TO ORIGINAL ISSUES")
        logger.info("=" * 50)
        logger.info("Original problematic results:")
        logger.info("  Cooling: 1.0 tons (11,824 BTU/hr)")
        logger.info("  Heating: 0.2 tons (1,989 BTU/hr)")
        logger.info("")
        logger.info("Enhanced calculation results:")
        logger.info(f"  Cooling: {system_calculation.cooling_tons:.1f} tons ({system_calculation.total_cooling_btuh:,.0f} BTU/hr)")
        logger.info(f"  Heating: {system_calculation.heating_tons:.1f} tons ({system_calculation.total_heating_btuh:,.0f} BTU/hr)")
        
        improvement_cooling = system_calculation.cooling_tons / 1.0
        improvement_heating = system_calculation.heating_tons / 0.2
        
        logger.info(f"Improvement factors:")
        logger.info(f"  Cooling: {improvement_cooling:.1f}x increase")
        logger.info(f"  Heating: {improvement_heating:.1f}x increase")
        
        # Final assessment
        if 1.5 <= system_calculation.cooling_tons <= 2.5 and 1.0 <= system_calculation.heating_tons <= 2.0:
            logger.info("✅ RESULTS LOOK REASONABLE for 1480 sq ft home in Spokane, WA")
        else:
            logger.warning("⚠️  Results may need further investigation")
        
        return system_calculation
        
    except Exception as e:
        logger.error(f"Enhanced calculation failed: {e}")
        raise

async def compare_extraction_methods():
    """Compare old mock data vs new extraction approach"""
    
    logger.info("\n" + "=" * 50)
    logger.info("EXTRACTION METHOD COMPARISON")
    logger.info("=" * 50)
    
    # Old mock approach (what was causing low loads)
    old_mock_data = {
        "rooms": [
            {"name": "Living Room", "area": 250, "height": 10, "windows": 3, "exterior_walls": 2},
            {"name": "Kitchen", "area": 150, "height": 10, "windows": 2, "exterior_walls": 1},
            {"name": "Master Bedroom", "area": 200, "height": 10, "windows": 2, "exterior_walls": 2}
        ],
        "total_area": 600,  # Only 600 sq ft vs actual 1480 sq ft!
        "building_details": {"floors": 1, "foundation_type": "slab", "roof_type": "standard"}
    }
    
    logger.info("OLD MOCK DATA ISSUES:")
    logger.info(f"  Total area: {old_mock_data['total_area']} sq ft (should be 1480)")
    logger.info(f"  Room count: {len(old_mock_data['rooms'])} (missing bathrooms, hallways)")
    logger.info(f"  No insulation values (used poor defaults)")
    logger.info(f"  No actual room dimensions (square assumptions)")
    logger.info(f"  No window performance data")
    logger.info(f"  No air tightness data")
    
    logger.info("\nNEW ENHANCED EXTRACTION:")
    logger.info(f"  Systematic regex patterns for R-values, U-values, areas")
    logger.info(f"  AI visual analysis for room layouts and orientations")
    logger.info(f"  Actual room dimensions and perimeters")
    logger.info(f"  Window orientation and performance data")
    logger.info(f"  Building envelope specifications")
    logger.info(f"  Confidence scoring for extracted data")
    
    # This explains why the original calculation was so low!
    area_ratio = 1480 / 600
    logger.info(f"\nAREA UNDERESTIMATE IMPACT:")
    logger.info(f"  Area ratio: {area_ratio:.1f}x underestimated")
    logger.info(f"  Expected load increase: ~{area_ratio:.1f}x")
    logger.info(f"  This alone explains much of the improvement!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_calculator())
    asyncio.run(compare_extraction_methods())