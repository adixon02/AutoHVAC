"""
Climate data endpoint for HVAC load calculations
"""
from fastapi import APIRouter, HTTPException

from ..models.responses import ClimateResponse
from ..core import settings, get_logger, create_http_exception

router = APIRouter()
logger = get_logger(__name__)


@router.get("/{zip_code}", response_model=ClimateResponse)
async def get_climate_data(zip_code: str):
    """
    Get climate zone and design temperatures for a ZIP code.
    
    This is a stub implementation that returns mock data.
    In production, this would integrate with your existing climate service.
    
    Args:
        zip_code: 5-digit ZIP code
        
    Returns:
        Climate data including zone and design temperatures
    """
    # Validate ZIP code format
    if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
        raise create_http_exception(
            400, 
            "Invalid ZIP code format. Please enter a 5-digit ZIP code."
        )
    
    logger.info(f"Climate data requested for ZIP: {zip_code}")
    
    # Mock climate data - replace with actual service call
    mock_data = _get_mock_climate_data(zip_code)
    
    return ClimateResponse(
        zip_code=zip_code,
        climate_zone=mock_data["climate_zone"],
        heating_design_temp=mock_data["heating_design_temp"],
        cooling_design_temp=mock_data["cooling_design_temp"],
        data_source="Mock Data Service",
        message="Climate data retrieved successfully"
    )


def _get_mock_climate_data(zip_code: str) -> dict:
    """
    Generate mock climate data based on ZIP code.
    In production, replace with actual climate service integration.
    """
    # Simple mock logic based on ZIP code patterns
    first_digit = int(zip_code[0])
    
    if first_digit in [0, 1, 2]:  # Northern states
        return {
            "climate_zone": "5A",
            "heating_design_temp": -5.0,
            "cooling_design_temp": 87.0
        }
    elif first_digit in [3, 4, 5]:  # Mid-Atlantic/Midwest
        return {
            "climate_zone": "4A", 
            "heating_design_temp": 15.0,
            "cooling_design_temp": 91.0
        }
    elif first_digit in [6, 7]:  # Southern states
        return {
            "climate_zone": "3A",
            "heating_design_temp": 25.0,
            "cooling_design_temp": 95.0
        }
    elif first_digit in [8, 9]:  # Western/Southwest
        return {
            "climate_zone": "2B",
            "heating_design_temp": 35.0,
            "cooling_design_temp": 105.0
        }
    else:
        return {
            "climate_zone": "4A",
            "heating_design_temp": 15.0,
            "cooling_design_temp": 91.0
        }