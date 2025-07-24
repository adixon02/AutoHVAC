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
import sys
from dataclasses import asdict

# Basic logging setup first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import processors from local directory
try:
    from enhanced_blueprint_processor import EnhancedBlueprintProcessor as BlueprintProcessor
    from professional_output_generator import ProfessionalOutputGenerator
    logger.info("✅ Successfully imported core modules")
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    raise

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
    
    # Process blueprint with actual analysis
    try:
        processor = BlueprintProcessor()
        output_generator = ProfessionalOutputGenerator()
        
        # Extract data from PDF
        extraction_result = processor.process_blueprint(Path(file_path))
        
        # Generate professional analysis
        professional_outputs = await output_generator.generate_complete_analysis(
            blueprint_path=Path(file_path),
            output_dir=Path("outputs") / job_id
        )
        
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
            },
            "extraction_result": asdict(extraction_result),
            "professional_outputs": professional_outputs
        }
    except Exception as e:
        logger.error(f"Blueprint processing failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Return error status instead of hiding the failure
        result = {
            "job_id": job_id,
            "filename": file.filename,
            "file_size": len(content),
            "upload_time": timestamp,
            "status": "failed",
            "message": f"Blueprint processing failed: {str(e)}",
            "project_info": {
                "zip_code": zip_code,
                "project_name": project_name,
                "project_type": project_type,
                "construction_type": construction_type
            },
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    # Save processing result with error handling
    result_file = PROCESSED_DIR / f"{job_id}.json"
    try:
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"✅ Saved processing result: {result_file}")
    except Exception as json_error:
        logger.error(f"❌ Failed to save JSON result: {json_error}")
        # Still try to return the result even if saving fails
        pass
    
    logger.info(f"File uploaded successfully: {file.filename}, job_id: {job_id}")
    return result

@app.get("/api/blueprint/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """Get processing status"""
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    # Debug: log what we're looking for and what exists
    logger.info(f"Looking for job file: {processed_file}")
    logger.info(f"Processed dir contents: {list(PROCESSED_DIR.glob('*.json'))}")
    
    if not processed_file.exists():
        # Return a temporary processing status instead of 404
        return {
            "job_id": job_id,
            "status": "processing", 
            "message": "Analysis in progress...",
            "progress": 50
        }
    
    with open(processed_file, "r") as f:
        result = json.load(f)
    
    return result

@app.get("/api/blueprint/results/{job_id}")
async def get_analysis_results(job_id: str) -> Dict[str, Any]:
    """Get analysis results"""
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not processed_file.exists():
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    with open(processed_file, "r") as f:
        base_result = json.load(f)
    
    # Return actual analysis results if available, otherwise fallback to processed data
    if "professional_outputs" in base_result and base_result["professional_outputs"]:
        outputs = base_result["professional_outputs"]
        extraction = base_result.get("extraction_result", {})
        
        # Format data for frontend
        manual_j = outputs.get("manual_j_calculation", {})
        hvac_design = outputs.get("hvac_system_design", {})
        
        return {
            **base_result,
            "status": "completed",
            "analysis": {
                "project_info": base_result.get("project_info", {}),
                "building_chars": {
                    "total_area": extraction.get("building_characteristics", {}).get("total_area", 0),
                    "stories": extraction.get("building_characteristics", {}).get("stories", 1),
                },
                "rooms": extraction.get("rooms", []),
                "manual_j": {
                    "cooling_tons": manual_j.get("cooling_tons", 0),
                    "heating_tons": manual_j.get("heating_tons", 0),
                    "total_cooling_btuh": manual_j.get("total_cooling_btuh", 0),
                    "total_heating_btuh": manual_j.get("total_heating_btuh", 0)
                },
                "hvac_design": {
                    "system_type": hvac_design.get("system_type", "TBD"),
                    "equipment_type": hvac_design.get("equipment_type", "TBD"),
                    "efficiency": hvac_design.get("efficiency", {})
                },
                "professional_deliverables": outputs.get("professional_deliverables", {})
            }
        }
    else:
        # Check if processing actually failed based on status
        actual_status = base_result.get("status", "failed")
        if actual_status == "failed":
            # Return error status to frontend
            return {
                **base_result,
                "status": "failed",
                "error_message": base_result.get("message", "Blueprint processing failed"),
                "error_details": base_result.get("error", "Unknown error occurred")
            }
        else:
            # Fallback for cases where processing was incomplete
            return {
                **base_result,
                "status": "completed", 
                "analysis": {
                    "project_info": base_result.get("project_info", {}),
                    "building_chars": {
                        "total_area": 0,
                        "stories": 1
                    },
                    "rooms": [],
                    "manual_j": {
                        "cooling_tons": 0,
                        "heating_tons": 0,
                        "total_cooling_btuh": 0,
                        "total_heating_btuh": 0
                    },
                    "hvac_design": {
                        "system_type": "TBD",
                        "equipment_type": "TBD", 
                        "efficiency": {}
                    },
                    "warning": "Analysis incomplete - partial data available"
                }
            }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting AutoHVAC Backend API on port {port}")
    logger.info(f"📁 Working directory: {Path.cwd()}")
    logger.info(f"🐍 Python path: {sys.path[:3]}...")  # Show first 3 paths
    logger.info(f"📂 Upload dir: {UPLOAD_DIR.absolute()}")
    logger.info(f"📂 Processed dir: {PROCESSED_DIR.absolute()}")
    
    try:
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=port,
            timeout_keep_alive=30
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        raise