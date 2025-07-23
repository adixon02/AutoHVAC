#!/usr/bin/env python3
"""
CORS-Fixed Server - Combines working CORS with basic upload functionality
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
import os
import uuid
from datetime import datetime
from pathlib import Path
import shutil

# Create FastAPI app
app = FastAPI(title="AutoHVAC CORS-Fixed Server", version="1.0.0")

# CRITICAL: Add CORS middleware FIRST
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
        "message": "AutoHVAC CORS-Fixed Server", 
        "status": "running",
        "cors": "enabled",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "cors": "working"}

@app.post("/api/blueprint/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    project_type: Optional[str] = Form(None),
    construction_type: Optional[str] = Form(None)
):
    """Upload endpoint with proper CORS and basic functionality"""
    
    # Validate file type
    allowed_extensions = {".pdf"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Please upload a PDF blueprint."
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create mock processed result
    result = {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": file_path.stat().st_size,
        "upload_time": timestamp,
        "status": "processing", 
        "message": "Blueprint uploaded successfully. Analysis started.",
        "estimated_completion": "2-3 minutes",
        "project_info": {
            "zip_code": zip_code,
            "project_name": project_name,
            "project_type": project_type,
            "construction_type": construction_type
        }
    }
    
    # Save result for status endpoint
    status_file = PROCESSED_DIR / f"{job_id}.json"
    import json
    with open(status_file, "w") as f:
        json.dump(result, f, indent=2)
    
    return result

@app.get("/api/blueprint/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status"""
    status_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not status_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    import json
    with open(status_file, "r") as f:
        result = json.load(f)
    
    # Mock completion after a short time
    result["status"] = "completed"
    result["message"] = "Analysis complete! Ready for download."
    
    return result

@app.get("/api/blueprint/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results"""
    status_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not status_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    import json
    with open(status_file, "r") as f:
        base_result = json.load(f)
    
    # Return mock results
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
        },
        "deliverables": {
            "executive_summary": f"/api/blueprint/download/{job_id}/executive_summary",
            "manual_j_report": f"/api/blueprint/download/{job_id}/manual_j_report",
            "hvac_design": f"/api/blueprint/download/{job_id}/hvac_design",
            "layout_svg": f"/api/blueprint/download/{job_id}/layout_svg"
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting CORS-Fixed AutoHVAC server on port {port}")
    print("✅ CORS configured for all origins")
    print("📋 Basic blueprint upload functionality enabled")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )