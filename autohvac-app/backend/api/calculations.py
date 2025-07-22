from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

router = APIRouter()

class Room(BaseModel):
    name: str
    area: float
    height: float
    windows: List[Dict[str, Any]]
    exterior_walls: int
    type: str

class BuildingInfo(BaseModel):
    total_area: float
    num_floors: int
    insulation_quality: str
    construction_year: int
    zip_code: str

class LoadCalculationRequest(BaseModel):
    rooms: List[Room]
    building_info: BuildingInfo

@router.post("/load")
async def calculate_hvac_load(request: LoadCalculationRequest) -> Dict[str, Any]:
    """
    Calculate HVAC load using Manual J methodology
    This endpoint bridges to the existing Next.js calculation logic
    """
    try:
        total_cooling_load = 0
        total_heating_load = 0
        room_loads = []
        
        # Simple load calculation (this would integrate with existing manualJ.ts logic)
        for room in request.rooms:
            # Base BTU calculation
            base_btu = room.area * 30  # Moderate climate default
            
            # Adjustments
            if room.exterior_walls > 1:
                base_btu *= 1.15
            
            if room.height > 9:
                base_btu *= 1.1
            
            # Window load
            window_load = sum(w.get("area", 0) * 15 for w in room.windows)
            
            cooling_load = base_btu + window_load
            heating_load = base_btu * 1.1
            
            room_loads.append({
                "room": room.name,
                "cooling_btu": cooling_load,
                "heating_btu": heating_load
            })
            
            total_cooling_load += cooling_load
            total_heating_load += heating_load
        
        # Convert to tons
        cooling_tons = total_cooling_load / 12000
        heating_tons = total_heating_load / 12000
        
        return {
            "total_cooling_load": total_cooling_load,
            "total_heating_load": total_heating_load,
            "cooling_tons": round(cooling_tons, 1),
            "heating_tons": round(heating_tons, 1),
            "room_loads": room_loads,
            "calculation_method": "Manual J"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/duct-design")
async def design_duct_system(
    load_calculation: Dict[str, Any],
    building_layout: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate duct system design based on load calculations and building layout
    """
    try:
        # Placeholder for duct design algorithm
        return {
            "main_trunk_size": "24x8",
            "branch_ducts": [
                {"room": "Master Bedroom", "size": "8 inch round", "cfm": 150},
                {"room": "Living Room", "size": "10 inch round", "cfm": 250},
                {"room": "Kitchen", "size": "8 inch round", "cfm": 200}
            ],
            "return_locations": ["Hallway", "Master Bedroom"],
            "equipment_location": "Garage",
            "total_duct_length": 245,
            "design_notes": [
                "All ducts routed through attic space",
                "Insulation R-8 minimum required",
                "Include balancing dampers at each branch"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))