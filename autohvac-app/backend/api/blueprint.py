from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import uuid
from pathlib import Path
import shutil
from datetime import datetime
import json
import asyncio

# Import our professional output generator
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from professional_output_generator import ProfessionalOutputGenerator

router = APIRouter()

# Storage paths
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
OUTPUTS_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Initialize our professional generator
professional_generator = ProfessionalOutputGenerator()

@router.post("/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Upload a blueprint PDF file and generate professional HVAC analysis
    Returns a job ID for tracking processing status
    """
    # Validate file type - we focus on PDFs for MVP
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
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Add background processing task
    background_tasks.add_task(process_blueprint_professional, job_id, file_path, file.filename)
    
    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": file_path.stat().st_size,
        "upload_time": timestamp,
        "status": "processing",
        "message": "Blueprint uploaded successfully. Professional analysis started.",
        "estimated_completion": "2-3 minutes"
    }

@router.get("/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """
    Get the processing status of a blueprint analysis
    """
    # Check if processed file exists
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if processed_file.exists():
        with open(processed_file, "r") as f:
            return json.load(f)
    
    # Check if upload exists
    upload_files = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    if upload_files:
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Blueprint is being analyzed... Generating professional HVAC design.",
            "progress": "50%"
        }
    
    raise HTTPException(status_code=404, detail="Job ID not found")

@router.get("/results/{job_id}")
async def get_analysis_results(job_id: str) -> Dict[str, Any]:
    """
    Get the complete analysis results for a processed blueprint
    """
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not processed_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Blueprint may still be processing."
        )
    
    with open(processed_file, "r") as f:
        data = json.load(f)
    
    if data.get("status") == "error":
        raise HTTPException(status_code=500, detail=data.get("error", "Processing failed"))
    
    return data

@router.get("/download/{job_id}/{file_type}")
async def download_deliverable(job_id: str, file_type: str):
    """
    Download specific deliverable files (manual_j, hvac_design, executive_summary, cad_drawing, web_layout)
    """
    from fastapi.responses import FileResponse
    
    # Map file types to actual file extensions
    file_mapping = {
        "manual_j": ".json",
        "hvac_design": ".json", 
        "executive_summary": ".txt",
        "cad_drawing": ".dxf",
        "web_layout": ".svg"
    }
    
    if file_type not in file_mapping:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Available: {list(file_mapping.keys())}")
    
    # Look for the file in job-specific directory
    job_output_dir = OUTPUTS_DIR / job_id
    output_files = list(job_output_dir.glob(f"*{file_mapping[file_type]}"))
    
    if not output_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = output_files[0]
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type='application/octet-stream'
    )

async def process_blueprint_professional(job_id: str, file_path: Path, original_filename: str):
    """
    Background task to process blueprint using our professional output generator
    """
    result = {
        "job_id": job_id,
        "status": "processing",
        "timestamp": datetime.now().isoformat(),
        "original_filename": original_filename
    }
    
    try:
        # Run our professional analysis with job-specific output directory
        job_output_dir = OUTPUTS_DIR / job_id
        job_output_dir.mkdir(exist_ok=True)
        
        summary = await professional_generator.generate_complete_analysis(
            blueprint_path=file_path,
            output_dir=job_output_dir
        )
        
        # Prepare result with all the professional data
        result.update({
            "status": "completed",
            "completion_time": datetime.now().isoformat(),
            "analysis_summary": summary,
            "project_info": {
                "name": summary.get("project_name", "Unknown Project"),
                "address": summary.get("address", ""),
                "confidence": summary.get("analysis_confidence", "0%"),
                "system_type": summary.get("system_recommendation", ""),
                "cost_estimate": summary.get("estimated_cost", 0),
                "ready_for_permits": summary.get("ready_for_permits", False)
            },
            "hvac_design": {
                "cooling_tons": summary.get("cooling_tons", 0),
                "heating_tons": summary.get("heating_tons", 0),
                "system_type": summary.get("system_recommendation", ""),
                "estimated_cost": summary.get("estimated_cost", 0)
            },
            "deliverables": {
                "files_generated": summary.get("deliverables_generated", 0),
                "file_list": summary.get("files", []),
                "download_links": {
                    "manual_j": f"/api/blueprint/download/{job_id}/manual_j",
                    "hvac_design": f"/api/blueprint/download/{job_id}/hvac_design", 
                    "executive_summary": f"/api/blueprint/download/{job_id}/executive_summary",
                    "cad_drawing": f"/api/blueprint/download/{job_id}/cad_drawing",
                    "web_layout": f"/api/blueprint/download/{job_id}/web_layout"
                }
            },
            "processing_info": {
                "generator_version": "professional_mvp_1.0",
                "ai_cost": "$0.00",  # Will be updated if AI gap filling was used
                "processing_time": "2-3 minutes",
                "confidence_score": summary.get("analysis_confidence", "0%")
            },
            "data_warnings": summary.get("data_warnings", [])
        })
        
        # Files are already generated in job-specific directory, no copying needed
        
    except Exception as e:
        result.update({
            "status": "error",
            "error": str(e),
            "error_time": datetime.now().isoformat()
        })
    
    # Save result
    output_path = PROCESSED_DIR / f"{job_id}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

@router.get("/")
async def blueprint_info():
    """
    Get information about the blueprint processing API
    """
    return {
        "service": "AutoHVAC Professional Blueprint Analysis",
        "version": "1.0.0",
        "supported_formats": ["PDF"],
        "deliverables": [
            "Manual J Load Calculation Report (JSON)",
            "HVAC System Design Specifications (JSON)", 
            "Executive Summary (TXT)",
            "CAD Drawings for Permits (DXF)",
            "Web Layout Visualization (SVG)"
        ],
        "processing_time": "2-3 minutes",
        "endpoints": {
            "upload": "POST /upload",
            "status": "GET /status/{job_id}",
            "results": "GET /results/{job_id}",
            "download": "GET /download/{job_id}/{file_type}"
        }
    }