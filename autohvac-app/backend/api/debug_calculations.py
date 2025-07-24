"""
Debug Calculations API
Provides detailed component-by-component load calculation breakdown
For troubleshooting and validation of Manual J results
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import Dict, Any
from services.enhanced_manual_j_calculator import EnhancedManualJCalculator
from services.climate_service import ClimateService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])

# Initialize services
climate_service = ClimateService()
calculator = EnhancedManualJCalculator()

@router.post("/calculate-detailed")
async def calculate_with_debug_output(request: Dict[str, Any]):
    """
    Perform Manual J calculation with detailed component breakdown
    Shows every calculation step for troubleshooting
    
    Expected request format:
    {
        "project_id": "test-project",
        "building_data": {
            "floor_area_ft2": 1480,
            "wall_insulation": {"effective_r": 19},
            "ceiling_insulation": 38,
            "window_schedule": {"u_value": 0.30, "shgc": 0.65},
            "air_tightness": 5.0
        },
        "rooms": [
            {
                "name": "Living Room",
                "area_ft2": 250,
                "ceiling_height": 9.0,
                "window_area": 30,
                "exterior_walls": 2,
                "perimeter_ft": 64
            }
        ],
        "climate": {
            "zip_code": "99206",
            "summer_design_temp": 89,
            "winter_design_temp": 5
        }
    }
    """
    try:
        logger.info(f"Starting detailed debug calculation")
        
        # Extract data from request
        project_id = request.get("project_id", "debug")
        building_data = request.get("building_data", {})
        room_data = request.get("rooms", [])
        climate_data = request.get("climate", {})
        
        # Add default climate data if not provided
        if "zip_code" in climate_data:
            climate_service_data = await climate_service.get_climate_data(climate_data["zip_code"])
            if climate_service_data:
                climate_data.update({
                    "summer_design_temp": climate_service_data.summer_design_temp,
                    "winter_design_temp": climate_service_data.winter_design_temp,
                    "zone": climate_service_data.zone
                })
        
        # Set defaults if missing
        climate_data.setdefault("summer_design_temp", 89)
        climate_data.setdefault("winter_design_temp", 5)
        climate_data.setdefault("humidity", 0.012)
        climate_data.setdefault("zone", "5A")
        
        # Perform calculation with enhanced detail
        system_calculation = await calculator.calculate_system_loads(
            project_id=project_id,
            building_data=building_data,
            room_data=room_data,
            climate_data=climate_data
        )
        
        # Create detailed debug response
        debug_response = {
            "summary": {
                "total_heating_btuh": system_calculation.total_heating_btuh,
                "total_cooling_btuh": system_calculation.total_cooling_btuh,
                "heating_tons": system_calculation.heating_tons,
                "cooling_tons": system_calculation.cooling_tons,
                "calculation_time": system_calculation.calculated_at.isoformat()
            },
            "input_data": {
                "building_characteristics": system_calculation.building_characteristics,
                "climate_data": system_calculation.climate_data,
                "room_count": len(system_calculation.room_loads)
            },
            "room_breakdown": [],
            "validation": system_calculation.validation_results,
            "assumptions": system_calculation.calculation_assumptions
        }
        
        # Add detailed room-by-room breakdown
        for room_load in system_calculation.room_loads:
            room_detail = {
                "room_name": room_load.room_name,
                "totals": {
                    "heating_btuh": room_load.total_heating_btuh,
                    "cooling_btuh": room_load.total_cooling_btuh
                },
                "geometry": room_load.geometry,
                "components": []
            }
            
            # Add component details
            for component in room_load.components:
                component_detail = {
                    "type": component.component_type,
                    "heating_btuh": component.heating_btuh,
                    "cooling_btuh": component.cooling_btuh,
                    "area_ft2": component.area_ft2,
                    "u_factor": component.u_factor,
                    "temp_diff": component.temp_diff,
                    "calculation_details": component.details or {}
                }
                room_detail["components"].append(component_detail)
            
            # Add validation flags
            if room_load.validation_flags:
                room_detail["validation_flags"] = room_load.validation_flags
            
            debug_response["room_breakdown"].append(room_detail)
        
        # Add calculation verification
        debug_response["verification"] = _verify_calculation_logic(debug_response)
        
        logger.info(f"Debug calculation complete: {system_calculation.cooling_tons:.1f} tons cooling")
        
        return debug_response
        
    except Exception as e:
        logger.error(f"Debug calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Debug calculation failed: {str(e)}"
        )

@router.post("/validate-loads")
async def validate_load_reasonableness(loads_data: Dict[str, Any]):
    """
    Validate calculated loads against industry standards
    
    Expected input:
    {
        "heating_btuh": 15000,
        "cooling_btuh": 21000,
        "floor_area_ft2": 1480,
        "climate_zone": "5A",
        "building_type": "residential"
    }
    """
    try:
        heating_btuh = loads_data.get("heating_btuh", 0)
        cooling_btuh = loads_data.get("cooling_btuh", 0)
        floor_area = loads_data.get("floor_area_ft2", 1)
        climate_zone = loads_data.get("climate_zone", "unknown")
        
        validation = {
            "input_data": loads_data,
            "load_densities": {
                "heating_btuh_per_sqft": heating_btuh / floor_area,
                "cooling_btuh_per_sqft": cooling_btuh / floor_area,
                "heating_tons_per_1000sqft": (heating_btuh / 12000) / (floor_area / 1000),
                "cooling_tons_per_1000sqft": (cooling_btuh / 12000) / (floor_area / 1000)
            },
            "industry_ranges": {
                "typical_heating_btuh_per_sqft": {"min": 10, "max": 25, "ideal": "15-20"},
                "typical_cooling_btuh_per_sqft": {"min": 15, "max": 35, "ideal": "20-30"},
                "typical_heating_tons_per_1000sqft": {"min": 0.5, "max": 1.5, "ideal": "0.8-1.2"},
                "typical_cooling_tons_per_1000sqft": {"min": 0.8, "max": 1.8, "ideal": "1.0-1.5"}
            },
            "validation_results": [],
            "recommendations": []
        }
        
        # Validate heating density
        heating_density = validation["load_densities"]["heating_btuh_per_sqft"]
        if heating_density < 10:
            validation["validation_results"].append({
                "type": "warning",
                "component": "heating_density",
                "message": f"Heating density ({heating_density:.1f} BTU/hr/ft²) is below typical range (10-25)",
                "possible_causes": ["Excellent insulation", "Mild climate", "Internal gains not accounted", "Calculation error"]
            })
        elif heating_density > 25:
            validation["validation_results"].append({
                "type": "warning", 
                "component": "heating_density",
                "message": f"Heating density ({heating_density:.1f} BTU/hr/ft²) is above typical range (10-25)",
                "possible_causes": ["Poor insulation", "High infiltration", "Extreme climate", "Oversized safety factors"]
            })
        else:
            validation["validation_results"].append({
                "type": "pass",
                "component": "heating_density",
                "message": f"Heating density ({heating_density:.1f} BTU/hr/ft²) is within normal range"
            })
        
        # Validate cooling density
        cooling_density = validation["load_densities"]["cooling_btuh_per_sqft"]
        if cooling_density < 15:
            validation["validation_results"].append({
                "type": "warning",
                "component": "cooling_density", 
                "message": f"Cooling density ({cooling_density:.1f} BTU/hr/ft²) is below typical range (15-35)",
                "possible_causes": ["Excellent insulation", "Low solar gains", "Minimal internal loads", "Calculation error"]
            })
        elif cooling_density > 35:
            validation["validation_results"].append({
                "type": "warning",
                "component": "cooling_density",
                "message": f"Cooling density ({cooling_density:.1f} BTU/hr/ft²) is above typical range (15-35)",
                "possible_causes": ["Poor insulation", "High solar gains", "High internal loads", "Poor window performance"]
            })
        else:
            validation["validation_results"].append({
                "type": "pass",
                "component": "cooling_density",
                "message": f"Cooling density ({cooling_density:.1f} BTU/hr/ft²) is within normal range"
            })
        
        # Add recommendations
        warning_count = len([r for r in validation["validation_results"] if r["type"] == "warning"])
        if warning_count == 0:
            validation["recommendations"].append("Load calculations appear reasonable for typical construction")
        else:
            validation["recommendations"].append(f"Review {warning_count} flagged items before finalizing equipment sizing")
            
        if heating_density < 12 or cooling_density < 18:
            validation["recommendations"].append("Consider validating building envelope inputs - loads may be optimistic")
            
        if heating_density > 22 or cooling_density > 32:
            validation["recommendations"].append("Consider verifying insulation values and air tightness - loads may be pessimistic")
        
        return validation
        
    except Exception as e:
        logger.error(f"Load validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Load validation failed: {str(e)}"
        )

def _verify_calculation_logic(debug_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify calculation logic for debugging"""
    
    verification = {
        "component_sum_check": {},
        "load_balance_check": {},
        "typical_ranges_check": {}
    }
    
    try:
        # Check that room components sum to room totals
        for room in debug_data["room_breakdown"]:
            room_name = room["room_name"]
            
            # Sum heating components
            component_heating_sum = sum(comp["heating_btuh"] for comp in room["components"])
            room_heating_total = room["totals"]["heating_btuh"]
            heating_diff = abs(component_heating_sum - room_heating_total)
            
            # Sum cooling components  
            component_cooling_sum = sum(comp["cooling_btuh"] for comp in room["components"])
            room_cooling_total = room["totals"]["cooling_btuh"]
            cooling_diff = abs(component_cooling_sum - room_cooling_total)
            
            verification["component_sum_check"][room_name] = {
                "heating_component_sum": component_heating_sum,
                "heating_room_total": room_heating_total,
                "heating_difference": heating_diff,
                "heating_matches": heating_diff < 1.0,
                "cooling_component_sum": component_cooling_sum,
                "cooling_room_total": room_cooling_total,
                "cooling_difference": cooling_diff,
                "cooling_matches": cooling_diff < 1.0
            }
        
        # Check system totals match room sums
        total_room_heating = sum(room["totals"]["heating_btuh"] for room in debug_data["room_breakdown"])
        total_room_cooling = sum(room["totals"]["cooling_btuh"] for room in debug_data["room_breakdown"])
        
        # Account for diversity and safety factors
        system_heating = debug_data["summary"]["total_heating_btuh"]
        system_cooling = debug_data["summary"]["total_cooling_btuh"]
        
        verification["load_balance_check"] = {
            "room_heating_sum": total_room_heating,
            "system_heating_total": system_heating,
            "heating_factor_applied": system_heating / total_room_heating if total_room_heating > 0 else 0,
            "room_cooling_sum": total_room_cooling,
            "system_cooling_total": system_cooling, 
            "cooling_factor_applied": system_cooling / total_room_cooling if total_room_cooling > 0 else 0
        }
        
        return verification
        
    except Exception as e:
        verification["error"] = f"Verification failed: {str(e)}"
        return verification