"""
Blueprint Upload Router - Fast, Async, Memory-Optimized
Handles file uploads up to 150MB with streaming and background processing
"""
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import logging

from app.config import config
from app.tasks.pdf_processor import process_pdf_async

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/blueprint",
    tags=["blueprint"],
    responses={404: {"description": "Not found"}},
)

@router.options("/upload")
@router.options("/upload/")
async def upload_options(request: Request):
    """Handle CORS preflight for upload endpoint"""
    return JSONResponse(
        status_code=204,
        content="",
        headers={
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "600"
        }
    )

@router.post("/upload")
@router.post("/upload/")
async def upload_blueprint(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    project_name: str = Form(...),
    building_type: str = Form(...),
    construction_type: str = Form(...),
):
    """
    Fast blueprint upload with immediate 202 response
    Files are streamed to disk and processed asynchronously
    """
    start_time = datetime.now()
    
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail="Only PDF files are supported"
            )
        
        # Check file size without loading into memory
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"Blueprint upload: {file.filename}, {file_size_mb:.1f}MB")
        
        # Enforce 150MB limit
        if file_size > config.MAX_FILE_SIZE_BYTES:
            logger.warning(f"File too large: {file_size_mb:.1f}MB")
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size_mb:.1f}MB). Maximum size is {config.MAX_FILE_SIZE_MB}MB"
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create upload directory
        os.makedirs(config.UPLOAD_DIR, exist_ok=True)
        
        # Stream file to disk in chunks (memory-safe)
        file_path = os.path.join(config.UPLOAD_DIR, f"{job_id}_{file.filename}")
        
        try:
            with open(file_path, "wb") as out_file:
                while chunk := await file.read(config.CHUNK_SIZE):
                    out_file.write(chunk)
        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            # Clean up partial file
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise HTTPException(
                status_code=500,
                detail="Failed to save uploaded file"
            )
        
        # Initialize job in storage
        job_data = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "File uploaded successfully, processing queued",
            "created_at": start_time.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "project_info": {
                "zip_code": zip_code,
                "project_name": project_name,
                "building_type": building_type,
                "construction_type": construction_type
            },
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size_mb, 2),
                "file_path": file_path
            },
            "result": None,
            "error": None
        }
        
        # Store job data
        request.app.state.job_storage[job_id] = job_data
        
        # Queue background processing
        background_tasks.add_task(
            process_pdf_async,
            job_id=job_id,
            file_path=file_path,
            project_info=job_data["project_info"],
            job_storage=request.app.state.job_storage
        )
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Upload completed in {response_time:.2f}s, job {job_id} queued")
        
        # Return 202 with job ID immediately
        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": "queued",
                "message": "File uploaded successfully, processing started",
                "file_size_mb": round(file_size_mb, 2),
                "response_time_seconds": round(response_time, 2)
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Upload failed due to server error"
        )

@router.get("/status/{job_id}")
@router.get("/job/{job_id}")  # Alternative endpoint name
async def get_job_status(job_id: str, request: Request):
    """
    Get processing status and results for a job
    """
    try:
        job_storage = request.app.state.job_storage
        
        if job_id not in job_storage:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_data = job_storage[job_id]
        
        # Return current status
        response_data = {
            "job_id": job_id,
            "status": job_data["status"],
            "progress": job_data.get("progress", 0),
            "message": job_data.get("message", ""),
            "created_at": job_data["created_at"],
            "updated_at": job_data["updated_at"]
        }
        
        # Include results if completed
        if job_data["status"] == "completed" and job_data.get("result"):
            response_data["result"] = job_data["result"]
        
        # Include error if failed
        if job_data["status"] == "error" and job_data.get("error"):
            response_data["error"] = job_data["error"]
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check job status"
        )

@router.get("/results/{job_id}")
async def get_job_results(job_id: str, request: Request):
    """
    Get detailed results for a completed job
    """
    try:
        job_storage = request.app.state.job_storage
        
        if job_id not in job_storage:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_data = job_storage[job_id]
        
        if job_data["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed (status: {job_data['status']})"
            )
        
        if not job_data.get("result"):
            raise HTTPException(
                status_code=404,
                detail=f"No results available for job {job_id}"
            )
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": job_data["result"],
            "completed_at": job_data["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Results fetch error for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch job results"
        )