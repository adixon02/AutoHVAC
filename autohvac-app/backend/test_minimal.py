#!/usr/bin/env python3
"""Minimal test to check if basic FastAPI works"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="AutoHVAC Test")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AutoHVAC Backend is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/blueprint/upload")
async def upload_blueprint():
    """Minimal blueprint upload endpoint for testing"""
    return {"message": "Upload endpoint working", "job_id": "test-123"}

@app.get("/api/blueprint/status/{job_id}")
async def get_status(job_id: str):
    """Minimal status endpoint"""
    return {"status": "completed", "message": "Test completed"}

@app.get("/api/blueprint/results/{job_id}")
async def get_results(job_id: str):
    """Minimal results endpoint"""
    return {
        "status": "completed",
        "analysis": {
            "project_info": {"project_name": "Test Project"},
            "building_chars": {"total_area": 1000},
            "rooms": [{"name": "Living Room", "area": 300}],
            "manual_j": {"cooling_tons": 2.5, "heating_tons": 3.0},
            "hvac_design": {"system_type": "ducted", "equipment_type": "heat_pump"}
        },
        "deliverables": {
            "executive_summary": "/api/blueprint/download/test-123/executive_summary",
            "manual_j_report": "/api/blueprint/download/test-123/manual_j_report",
            "hvac_design": "/api/blueprint/download/test-123/hvac_design",
            "layout_svg": "/api/blueprint/download/test-123/layout_svg"
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting minimal server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)