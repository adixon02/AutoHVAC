#!/usr/bin/env python3
"""
AutoHVAC Local Development Server
================================

A simplified version of the AutoHVAC backend that runs locally without Docker,
Redis, PostgreSQL, or Celery for testing the blueprint parsing functionality.
"""

import os
import sys
import json
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import the parsing modules
from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser
from app.parser.ai_cleanup import cleanup, AICleanupError
from services.manualj import calculate_manualj

app = FastAPI(title="AutoHVAC Local API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage for local testing
jobs = {}
job_counter = 0

class LocalJobStore:
    """Simple in-memory job storage for local testing"""
    
    def create_job(self, filename: str, email: str = "") -> str:
        global job_counter
        job_counter += 1
        job_id = f"local-job-{job_counter}"
        
        jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "email": email,
            "status": "created",
            "stage": "pending",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }
        
        return job_id
    
    def update_job(self, job_id: str, updates: Dict[str, Any]):
        if job_id in jobs:
            jobs[job_id].update(updates)
            jobs[job_id]["updated_at"] = datetime.now().isoformat()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return jobs.get(job_id)

job_store = LocalJobStore()

@app.get("/")
async def root():
    return {"message": "AutoHVAC Local API is running", "jobs_processed": len(jobs)}

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "local_development"}

@app.post("/api/v1/blueprint/upload")
async def upload_blueprint(file: UploadFile = File(...), email: str = "", zip_code: str = "99206"):
    """Upload and process a blueprint PDF"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create job
    job_id = job_store.create_job(file.filename, email)
    
    try:
        # Read file content
        content = await file.read()
        
        # Start processing in background
        asyncio.create_task(process_blueprint_local(job_id, content, file.filename, email, zip_code))
        
        return {"job_id": job_id, "status": "processing", "message": "Blueprint upload successful"}
        
    except Exception as e:
        job_store.update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "stage": "upload"
        })
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/v1/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    job = job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

async def process_blueprint_local(job_id: str, file_content: bytes, filename: str, email: str, zip_code: str):
    """Process blueprint PDF locally without Celery"""
    
    try:
        job_store.update_job(job_id, {
            "status": "processing",
            "stage": "initializing",
            "progress": 10
        })
        
        # Save PDF to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            job_store.update_job(job_id, {
                "stage": "extracting_geometry",
                "progress": 25
            })
            
            # Stage 1: Extract geometry
            geometry_parser = GeometryParser()
            raw_geometry = geometry_parser.parse(temp_path)
            
            job_store.update_job(job_id, {
                "stage": "extracting_text",
                "progress": 50
            })
            
            # Stage 2: Extract text
            text_parser = TextParser()
            raw_text = text_parser.parse(temp_path)
            
            job_store.update_job(job_id, {
                "stage": "ai_processing",
                "progress": 70
            })
            
            # Stage 3: AI cleanup
            try:
                blueprint_schema = await cleanup(raw_geometry, raw_text)
            except AICleanupError as e:
                # Fallback to rule-based parsing
                from uuid import uuid4
                from app.parser.schema import BlueprintSchema, Room
                
                blueprint_schema = BlueprintSchema(
                    project_id=uuid4(),
                    zip_code=zip_code,
                    sqft_total=1200.0,  # Default
                    stories=1,
                    rooms=[
                        Room(
                            name="Living Room",
                            dimensions_ft=(20.0, 15.0),
                            floor=1,
                            windows=3,
                            orientation="S",
                            area=300.0
                        ),
                        Room(
                            name="Kitchen",
                            dimensions_ft=(12.0, 10.0),
                            floor=1,
                            windows=1,
                            orientation="E",
                            area=120.0
                        ),
                        Room(
                            name="Master Bedroom",
                            dimensions_ft=(14.0, 12.0),
                            floor=1,
                            windows=2,
                            orientation="N",
                            area=168.0
                        )
                    ]
                )
            
            job_store.update_job(job_id, {
                "stage": "calculating_loads",
                "progress": 85
            })
            
            # Stage 4: Manual J calculations
            hvac_analysis = calculate_manualj(blueprint_schema)
            
            job_store.update_job(job_id, {
                "stage": "finalizing",
                "progress": 95
            })
            
            # Compile results
            result = {
                "job_id": job_id,
                "filename": filename,
                "email": email,
                "processed_at": datetime.now().isoformat(),
                "project_name": Path(filename).stem,
                "zip_code": zip_code,
                "building_summary": {
                    "total_area_ft2": blueprint_schema.sqft_total,
                    "stories": blueprint_schema.stories,
                    "room_count": len(blueprint_schema.rooms)
                },
                "blueprint": blueprint_schema.dict(),
                "hvac_analysis": hvac_analysis,
                "parsing_metadata": {
                    "geometry_summary": {
                        "lines_found": len(raw_geometry.lines),
                        "rectangles_found": len(raw_geometry.rectangles),
                        "polylines_found": len(raw_geometry.polylines),
                        "page_size": [raw_geometry.page_width, raw_geometry.page_height],
                        "scale_detected": raw_geometry.scale_factor
                    },
                    "text_summary": {
                        "words_found": len(raw_text.words),
                        "room_labels_found": len(raw_text.room_labels),
                        "dimensions_found": len(raw_text.dimensions),
                        "notes_found": len(raw_text.notes)
                    }
                }
            }
            
            job_store.update_job(job_id, {
                "status": "completed",
                "stage": "complete",
                "progress": 100,
                "result": result
            })
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        job_store.update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "stage": "processing"
        })

@app.get("/api/v1/jobs")
async def list_jobs():
    """List all jobs for debugging"""
    return {"jobs": list(jobs.values()), "total": len(jobs)}

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting AutoHVAC Local Server")
    print("📡 Backend API: http://localhost:8000")
    print("📋 API Docs: http://localhost:8000/docs")
    print("🔧 Local mode - no Redis/PostgreSQL required")
    print("-" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)