import os
import uuid
import tempfile
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our working pipeline
from pipeline_v3 import run_pipeline_v3

logger = logging.getLogger(__name__)
router = APIRouter()

class UploadResponse(BaseModel):
    """Response model for blueprint upload"""
    job_id: str
    status: str
    message: str

class JobResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None

# In-memory job storage (for MVP - replace with Redis/DB in production)
jobs = {}

@router.post("/upload", response_model=UploadResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    openai_api_key: Optional[str] = Form(None)
):
    """
    Upload a blueprint PDF and start HVAC load calculation
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Validate zip code
        if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
            raise HTTPException(status_code=400, detail="Valid 5-digit zip code required")
        
        # Use environment API key if not provided
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key required")
        
        # Initialize job status
        jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "filename": file.filename,
            "zip_code": zip_code,
            "result": None,
            "error": None
        }
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Start processing in background
        asyncio.create_task(process_blueprint_async(job_id, temp_file_path, zip_code, api_key))
        
        logger.info(f"Started job {job_id} for file {file.filename}, zip {zip_code}")
        
        return UploadResponse(
            job_id=job_id,
            status="processing",
            message="Blueprint upload successful. Processing started."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_blueprint_async(job_id: str, pdf_path: str, zip_code: str, api_key: str):
    """
    Process blueprint asynchronously using pipeline_v3
    """
    try:
        # Update progress
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        
        logger.info(f"Job {job_id}: Starting pipeline_v3 processing")
        
        # Run pipeline_v3 (this is your working pipeline!)
        # Note: run_pipeline_v3 returns a dictionary, not an object
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            run_pipeline_v3,
            pdf_path, 
            zip_code, 
            None,  # user_inputs (optional)
            api_key
        )
        
        # Pipeline_v3 returns a dictionary - check if it has heating load data
        if result and "heating_load_btu_hr" in result:
            # Result is already a dictionary, just add some calculated fields
            result_data = {
                **result,  # Include all pipeline results
                "heating_tons": result["heating_load_btu_hr"] / 12000,  # Convert BTU to tons
                "cooling_tons": result["cooling_load_btu_hr"] / 12000,
                "zones_created": result.get("zones", 0),
                "spaces_detected": result.get("spaces", 0),
                "garage_detected": result.get("garage_detected", False),
                "bonus_over_garage": result.get("bonus_over_garage", False),
                "confidence_score": result.get("confidence", 0.0),
                "warnings": result.get("warnings", []),
                "zone_loads": result.get("zone_loads", {}),
                "processing_time_seconds": result.get("processing_time", 0)
            }
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["result"] = result_data
            
            logger.info(f"Job {job_id}: Completed successfully - {result['heating_load_btu_hr']:,.0f} BTU/hr heating")
            
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Pipeline processing failed: No valid result returned"
            logger.error(f"Job {job_id}: Pipeline failed - no valid result")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id}: Processing error - {e}")
        
    finally:
        # Cleanup temporary file
        try:
            os.unlink(pdf_path)
        except:
            pass

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get status of a processing job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"]
    )

@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """
    Get detailed result of completed job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed. Status: {job['status']}")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "filename": job["filename"],
        "zip_code": job["zip_code"],
        "result": job["result"]
    }