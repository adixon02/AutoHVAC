"""
Manual J Calculation API endpoints
Following docs/02-development/api-checklist.md
"""
from fastapi import APIRouter, HTTPException, Request
import logging
import uuid
import json
from datetime import datetime
from services.climate_service import ClimateService
from services.enhanced_manual_j_calculator import EnhancedManualJCalculator
from models.api import CalculationRequest, CalculationResponse, ApiResponse
from models.calculations import SystemRecommendation, SystemTier, CoolingSystem, HeatingSystem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calculations", tags=["calculations"])

# Initialize services
climate_service = ClimateService()
calculator = EnhancedManualJCalculator()

@router.post("/calculate-debug")
async def debug_calculate_request(request: Request):
    """Debug endpoint to capture raw request body"""
    try:
        body = await request.body()
        json_data = json.loads(body)
        logger.info("=== RAW REQUEST DEBUG ===")
        logger.info(f"Raw request body: {json.dumps(json_data, indent=2, default=str)}")
        
        # Try to validate
        try:
            calc_request = CalculationRequest(**json_data)
            logger.info("✅ Validation successful")
            return {"status": "valid", "message": "Request validates successfully"}
        except Exception as validation_error:
            logger.error(f"❌ Validation failed: {validation_error}")
            return {"status": "invalid", "error": str(validation_error)}
            
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {"status": "error", "error": str(e)}

@router.post("/calculate", response_model=CalculationResponse)
async def calculate_loads(request: CalculationRequest):
    """
    Perform Manual J load calculations
    
    Args:
        request: Project, building, and room data
        
    Returns:
        Load calculations and system recommendations
        
    Raises:
        400: Invalid input data
        422: Calculation constraints not met
        500: Calculation engine error
    """
    try:
        logger.info(f"Starting calculation for project: {request.project.project_name}")
        logger.info(f"Building area: {request.building.total_square_footage} sq ft")
        logger.info(f"Number of rooms: {len(request.rooms)}")
        for room in request.rooms:
            logger.info(f"Room '{room.name}': {room.area} sq ft, {room.ceiling_height}' ceiling")
        
        # Validate required data
        if not request.rooms:
            raise HTTPException(
                status_code=400,
                detail="At least one room is required for calculations"
            )
        
        if request.building.total_square_footage <= 0:
            raise HTTPException(
                status_code=400,
                detail="Building square footage must be greater than zero"
            )
        
        # Get climate data
        climate_data = await climate_service.get_climate_data(request.project.zip_code)
        if not climate_data:
            logger.warning(f"No climate data for ZIP {request.project.zip_code}, using defaults")
            climate_data = await climate_service.get_default_climate_data()
        
        # Prepare data for enhanced calculator
        building_data = {
            "floor_area_ft2": request.building.total_square_footage,
            "wall_insulation": {"effective_r": 19},  # Default, should come from blueprint
            "ceiling_insulation": 38,  # Default, should come from blueprint  
            "window_schedule": {"u_value": 0.30, "shgc": 0.65},  # Default
            "air_tightness": 5.0,  # Default 5 ACH50
            "ceiling_height": 9.0  # Default
        }
        
        room_data = []
        for room in request.rooms:
            room_data.append({
                "name": room.name,
                "area_ft2": room.area,
                "area": room.area,  # Backward compatibility
                "ceiling_height": room.ceiling_height,
                "window_area": getattr(room, 'window_area', room.area * 0.12),
                "exterior_walls": getattr(room, 'exterior_walls', 2),
                "occupants": getattr(room, 'occupants', max(1, room.area // 200)),
                "equipment_load": getattr(room, 'equipment_load', room.area * 0.5)
            })
        
        climate_dict = {
            "summer_design_temp": climate_data.summer_design_temp,
            "winter_design_temp": climate_data.winter_design_temp,
            "humidity": getattr(climate_data, 'humidity', 0.012),  # Default humidity ratio
            "zone": climate_data.zone
        }
        
        # Perform Enhanced Manual J calculations
        system_calculation = await calculator.calculate_system_loads(
            project_id=request.project.id,
            building_data=building_data,
            room_data=room_data,
            climate_data=climate_dict
        )
        
        # Generate system recommendations
        recommendations = await _generate_system_recommendations(system_calculation)
        
        logger.info(f"Enhanced calculation complete: {system_calculation.cooling_tons:.1f} tons cooling, {system_calculation.heating_tons:.1f} tons heating")
        
        # Convert enhanced calculation to expected response format
        from models.calculations import LoadCalculation, RoomLoad
        load_calculation = LoadCalculation(
            project_id=system_calculation.project_id,
            total_cooling_load=int(system_calculation.total_cooling_btuh),
            total_heating_load=int(system_calculation.total_heating_btuh),
            cooling_tons=system_calculation.cooling_tons,
            heating_tons=system_calculation.heating_tons,
            room_loads=[
                RoomLoad(
                    room_id=room.room_name,
                    cooling_load=int(room.total_cooling_btuh),
                    heating_load=int(room.total_heating_btuh)
                )
                for room in system_calculation.room_loads
            ],
            calculated_at=system_calculation.calculated_at
        )
        
        return CalculationResponse(
            load_calculation=load_calculation,
            recommendations=recommendations
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Calculation engine error. Please check your data and try again."
        )

async def _generate_system_recommendations(system_calculation) -> list[SystemRecommendation]:
    """
    Generate three-tier equipment recommendations
    Based on calculated loads
    """
    cooling_tons = system_calculation.cooling_tons
    heating_btuh = system_calculation.total_heating_btuh
    
    # Round up to next 0.5 ton increment for equipment sizing
    equipment_cooling_tons = round(cooling_tons * 2) / 2
    if equipment_cooling_tons < cooling_tons:
        equipment_cooling_tons += 0.5
    
    # Round up heating to next 5000 BTU increment, minimum 10000 BTU/hr
    equipment_heating_btuh = max(10000, int(((heating_btuh // 5000) + 1) * 5000))
    
    recommendations = []
    
    # Economy tier
    recommendations.append(SystemRecommendation(
        tier=SystemTier.ECONOMY,
        cooling_system=CoolingSystem(
            type="Central Air Conditioner",
            size=equipment_cooling_tons,
            seer=14,
            brand="Goodman",
            model=f"GSX14{int(equipment_cooling_tons * 10):02d}",
            estimated_cost=int(equipment_cooling_tons * 1500 + 2000)
        ),
        heating_system=HeatingSystem(
            type="Gas Furnace",
            size=equipment_heating_btuh,
            efficiency=0.80,
            brand="Goodman",
            model=f"GM9S{equipment_heating_btuh // 1000:03d}",
            estimated_cost=int(equipment_heating_btuh / 25 + 1500)
        )
    ))
    
    # Standard tier
    recommendations.append(SystemRecommendation(
        tier=SystemTier.STANDARD,
        cooling_system=CoolingSystem(
            type="Central Air Conditioner",
            size=equipment_cooling_tons,
            seer=16,
            brand="Trane",
            model=f"4A7A6{int(equipment_cooling_tons * 10):02d}",
            estimated_cost=int(equipment_cooling_tons * 2000 + 2500)
        ),
        heating_system=HeatingSystem(
            type="Gas Furnace",
            size=equipment_heating_btuh,
            efficiency=0.90,
            brand="Trane",
            model=f"S9V2{equipment_heating_btuh // 1000:03d}",
            estimated_cost=int(equipment_heating_btuh / 20 + 2000)
        )
    ))
    
    # Premium tier  
    recommendations.append(SystemRecommendation(
        tier=SystemTier.PREMIUM,
        cooling_system=CoolingSystem(
            type="Heat Pump",
            size=equipment_cooling_tons,
            seer=20,
            brand="Carrier",
            model=f"25VNA4{int(equipment_cooling_tons * 10):02d}",
            estimated_cost=int(equipment_cooling_tons * 2800 + 3500)
        ),
        heating_system=HeatingSystem(
            type="Heat Pump",
            size=equipment_heating_btuh,
            efficiency=0.95,
            brand="Carrier",
            model=f"25VNA4{int(equipment_cooling_tons * 10):02d}",
            estimated_cost=1000  # Minimum cost for heat pump heating
        )
    ))
    
    return recommendations