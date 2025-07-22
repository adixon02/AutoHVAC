from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import uuid
from pathlib import Path
import shutil
from datetime import datetime

from processors.blueprint_parser import BlueprintParser
from ml_models.room_detector import RoomDetector

router = APIRouter()

# Storage paths
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Initialize processors
blueprint_parser = BlueprintParser()
room_detector = RoomDetector()

@router.post("/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Upload a blueprint file (PDF, DWG, DXF, PNG, JPG)
    Returns a job ID for tracking processing status
    """
    # Validate file type
    allowed_extensions = {".pdf", ".dwg", ".dxf", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed types: {allowed_extensions}"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Add background processing task
    background_tasks.add_task(process_blueprint, job_id, file_path)
    
    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": file_path.stat().st_size,
        "upload_time": timestamp,
        "status": "processing",
        "message": "Blueprint uploaded successfully. Processing started."
    }

@router.get("/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """
    Get the processing status of a blueprint
    """
    # Check if processed file exists
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if processed_file.exists():
        import json
        with open(processed_file, "r") as f:
            return json.load(f)
    
    # Check if upload exists
    upload_files = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    if upload_files:
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Blueprint is being processed"
        }
    
    raise HTTPException(status_code=404, detail="Job ID not found")

@router.get("/analyze/{job_id}")
async def get_blueprint_analysis(job_id: str) -> Dict[str, Any]:
    """
    Get the analysis results for a processed blueprint
    """
    processed_file = PROCESSED_DIR / f"{job_id}.json"
    
    if not processed_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Blueprint may still be processing."
        )
    
    import json
    with open(processed_file, "r") as f:
        data = json.load(f)
    
    if data.get("status") == "error":
        raise HTTPException(status_code=500, detail=data.get("error", "Processing failed"))
    
    return data

async def process_blueprint(job_id: str, file_path: Path):
    """
    Background task to process blueprint
    """
    import json
    
    result = {
        "job_id": job_id,
        "status": "processing",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Parse blueprint
        parsed_data = await blueprint_parser.parse(file_path)
        
        # Detect rooms
        rooms = await room_detector.detect_rooms(parsed_data)
        
        # Prepare result
        result.update({
            "status": "completed",
            "data": {
                "dimensions": parsed_data.get("dimensions"),
                "rooms": rooms,
                "total_area": sum(room["area"] for room in rooms),
                "num_rooms": len(rooms),
                "file_type": file_path.suffix,
                "metadata": parsed_data.get("metadata", {})
            }
        })
        
    except Exception as e:
        result.update({
            "status": "error",
            "error": str(e)
        })
    
    # Save result
    output_path = PROCESSED_DIR / f"{job_id}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)