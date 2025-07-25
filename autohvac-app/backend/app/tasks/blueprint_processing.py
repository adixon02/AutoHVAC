"""
Background task for processing blueprint files
"""
import time
import asyncio
from pathlib import Path
from typing import Dict, Any

from ..core import settings, get_logger
from ..models.requests import JobStatusEnum
from ..services.job_storage import job_storage
from ..services.file_handler import file_handler

logger = get_logger(__name__)


async def process_blueprint_background(job_id: str, file_path: str, request_id: str):
    """
    Background task to process uploaded blueprint files.
    
    This is a stub implementation that simulates processing.
    In production, this would call your existing blueprint extraction logic.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to uploaded file
        request_id: Request ID for tracking
    """
    logger.info(
        "Starting blueprint processing",
        extra={
            "job_id": job_id,
            "file_path": file_path,
            "request_id": request_id
        }
    )
    
    try:
        # Update job to processing status
        job_storage.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.PROCESSING,
            progress=0,
            message="Starting blueprint analysis..."
        )
        
        # Simulate processing with progress updates
        processing_steps = [
            (10, "Loading PDF file..."),
            (25, "Extracting text and graphics..."), 
            (40, "Identifying rooms and spaces..."),
            (60, "Calculating dimensions..."),
            (75, "Analyzing HVAC requirements..."),
            (90, "Generating recommendations..."),
            (100, "Processing complete")
        ]
        
        for progress, message in processing_steps:
            job_storage.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.PROCESSING,
                progress=progress,
                message=message
            )
            
            # Simulate processing time
            await asyncio.sleep(0.5)
        
        # Generate mock result data
        result = await _generate_mock_result(file_path)
        
        # Mark job as completed
        job_storage.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.COMPLETED,
            progress=100,
            message="Blueprint processing completed successfully",
            result=result
        )
        
        logger.info(
            "Blueprint processing completed",
            extra={
                "job_id": job_id,
                "request_id": request_id,
                "rooms_found": len(result.get("rooms", []))
            }
        )
        
    except Exception as e:
        logger.error(
            f"Blueprint processing failed: {e}",
            extra={
                "job_id": job_id,
                "request_id": request_id
            },
            exc_info=True
        )
        
        # Mark job as failed
        job_storage.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.FAILED,
            message="Processing failed due to an error",
            error=str(e)
        )
        
    finally:
        # Clean up uploaded file
        await file_handler.delete_file(file_path)


async def _generate_mock_result(file_path: str) -> Dict[str, Any]:
    """
    Generate mock result data for testing.
    In production, this would be replaced with actual blueprint extraction logic.
    """
    file_info = file_handler.get_file_info(file_path)
    
    return {
        "file_info": {
            "filename": Path(file_path).name,
            "size_bytes": file_info.get("size_bytes", 0),
            "processed_at": time.time()
        },
        "building_info": {
            "total_area_sqft": 2400,
            "floors": 1,
            "construction_type": "Residential"
        },
        "rooms": [
            {
                "name": "Living Room",
                "area_sqft": 320,
                "volume_cuft": 2560,
                "load_btuh": 8500
            },
            {
                "name": "Master Bedroom", 
                "area_sqft": 200,
                "volume_cuft": 1600,
                "load_btuh": 5200
            },
            {
                "name": "Kitchen",
                "area_sqft": 150,
                "volume_cuft": 1200,
                "load_btuh": 6800
            }
        ],
        "hvac_requirements": {
            "total_cooling_load_btuh": 28000,
            "total_heating_load_btuh": 22000,
            "recommended_unit_size_tons": 2.5,
            "estimated_ductwork_linear_feet": 120
        },
        "recommendations": [
            "Consider zoned system for improved efficiency",
            "Ensure proper insulation in attic space", 
            "Install programmable thermostat"
        ]
    }