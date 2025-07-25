"""
Climate API endpoints
Following docs/02-development/api-checklist.md
"""
from fastapi import APIRouter, HTTPException
import logging
from services.climate_service import ClimateService
from models.api import ApiResponse
from models.climate import ClimateData

logger = logging.getLogger(__name__)
router = APIRouter(tags=["climate"])

# Initialize climate service
climate_service = ClimateService()

@router.get("/{zip_code}", response_model=ClimateData)
async def get_climate_data(zip_code: str):
    """
    Get climate data for load calculations
    
    Args:
        zip_code: 5-digit ZIP code
        
    Returns:
        ClimateData with design temperatures and climate zone
        
    Raises:
        400: Invalid ZIP code format
        404: ZIP code not found in database
        500: Climate service unavailable
    """
    try:
        # Validate ZIP code format
        if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
            raise HTTPException(
                status_code=400,
                detail="Invalid ZIP code format. Please enter a 5-digit ZIP code."
            )
        
        # Look up climate data
        climate_data = await climate_service.get_climate_data(zip_code)
        
        if not climate_data:
            raise HTTPException(
                status_code=404,
                detail=f"Climate data not found for ZIP code {zip_code}. Please try a different ZIP code."
            )
        
        logger.info(f"Climate data served for ZIP {zip_code}: Zone {climate_data.zone}")
        return climate_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Climate service error for ZIP {zip_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Climate service temporarily unavailable. Please try again later."
        )

@router.get("/{zip_code}/validate")
async def validate_zip_code(zip_code: str) -> ApiResponse[bool]:
    """
    Validate if we have climate data coverage for a ZIP code
    """
    logger.info(f"ZIP validation request received for: {zip_code}")
    
    try:
        # Validate ZIP code format first
        if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
            logger.warning(f"Invalid ZIP code format in validation: {zip_code}")
            return ApiResponse(
                success=True,
                data=False,
                message=f"ZIP code {zip_code} has invalid format"
            )
        
        logger.info(f"Calling climate service to validate ZIP: {zip_code}")
        is_valid = await climate_service.validate_zip_coverage(zip_code)
        logger.info(f"ZIP validation result for {zip_code}: {is_valid}")
        
        return ApiResponse(
            success=True,
            data=is_valid,
            message=f"ZIP code {zip_code} {'is' if is_valid else 'is not'} supported"
        )
        
    except Exception as e:
        logger.error(f"ZIP validation error for {zip_code}: {e}")
        return ApiResponse(
            success=False,
            error="Unable to validate ZIP code"
        )