#!/usr/bin/env python3
"""Ultra-simple FastAPI server to test basic deployment"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
import os

# Create FastAPI app
app = FastAPI(title="AutoHVAC Simple Test")

# Add CORS middleware - very permissive for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Simple AutoHVAC Backend", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "server": "simple"}

@app.post("/api/blueprint/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None)
):
    """Simple upload endpoint that accepts file uploads"""
    print(f"Received upload: {file.filename}, zip_code: {zip_code}")
    return {
        "status": "success",
        "job_id": "simple-test-123",
        "filename": file.filename,
        "message": "Upload received successfully"
    }

@app.get("/api/blueprint/status/{job_id}")
async def get_status(job_id: str):
    """Return completed status immediately"""
    return {
        "status": "completed",
        "job_id": job_id,
        "message": "Analysis complete"
    }

@app.get("/api/blueprint/results/{job_id}")
async def get_results(job_id: str):
    """Return mock results"""
    return {
        "status": "completed",
        "job_id": job_id,
        "analysis": {
            "project_info": {
                "project_name": "Test Project",
                "zip_code": "99019"
            },
            "building_chars": {
                "total_area": 1500,
                "stories": 1
            },
            "rooms": [
                {"name": "Living Room", "area": 400},
                {"name": "Kitchen", "area": 200},
                {"name": "Bedroom", "area": 300}
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
    print(f"Starting simple server on port {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )