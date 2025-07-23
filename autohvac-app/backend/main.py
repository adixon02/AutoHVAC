#!/usr/bin/env python3
"""
Simplified AutoHVAC Backend - Focus on core blueprint upload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import uvicorn
import os
import uuid
import json
from pathlib import Path
from datetime import datetime
import logging

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoHVAC Backend API",
    description="AI-powered HVAC system design and blueprint processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],
)

# Create directories
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "AutoHVAC Backend API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "AutoHVAC Backend",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/blueprint/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    project_type: Optional[str] = Form(None),
    construction_type: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """Upload a blueprint PDF file"""
    
    # Validate file type
    allowed_extensions = {".pdf"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Please upload a PDF blueprint."
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Create mock result for testing
    result = {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": len(content),
        "upload_time": timestamp,
        "status": "processing",
        "message": "Blueprint uploaded successfully. Analysis started.",
        "project_info": {
            "zip_code": zip_code,
            "project_name": project_name,
            "project_type": project_type,
            "construction_type": construction_type
        }
    }
    
    # Save processing result
    result_file = PROCESSED_DIR / f"{job_id}.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"File uploaded successfully: {file.filename}, job_id: {job_id}")
    return result

@app.get("/api/blueprint/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """Get processing status"""
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not processed_file.exists():
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    with open(processed_file, "r") as f:
        result = json.load(f)
    
    # Mock completion after status check
    result["status"] = "completed"
    result["message"] = "Analysis complete!"
    
    return result

@app.get("/api/blueprint/results/{job_id}")
async def get_analysis_results(job_id: str) -> Dict[str, Any]:
    """Get analysis results"""
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not processed_file.exists():
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    with open(processed_file, "r") as f:
        base_result = json.load(f)
    
    # Return mock analysis results
    return {
        **base_result,
        "status": "completed",
        "analysis": {
            "project_info": base_result.get("project_info", {}),
            "building_chars": {
                "total_area": 2400,
                "stories": 2
            },
            "rooms": [
                {"name": "Living Room", "area": 400, "cooling_load": 8000},
                {"name": "Kitchen", "area": 200, "cooling_load": 4000},
                {"name": "Master Bedroom", "area": 300, "cooling_load": 6000}
            ],
            "manual_j": {
                "cooling_tons": 2.5,
                "heating_tons": 3.0,
                "total_cooling_btuh": 30000,
                "total_heating_btuh": 36000
            },
            "hvac_design": {
                "system_type": "ducted",
                "equipment_type": "heat_pump",
                "efficiency": {"seer": 16, "hspf": 9}
            }
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AutoHVAC Backend API on port {port}")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=30
    )