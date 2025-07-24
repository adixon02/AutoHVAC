#!/usr/bin/env python3
"""
Optimized Blueprint API Router using the new service layer
High-performance, clean separation of concerns
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import json
import asyncio

from services.blueprint_service import get_blueprint_service
from core.error_handling import (
    AutoHVACException, AutoHVACErrors, 
    validate_file_upload, validate_zip_code,
    handle_file_system_error
)
from core.logging_config import get_logger, log_blueprint_processing, performance_timer

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Get service instance
blueprint_service = get_blueprint_service()

@router.post("/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    project_type: Optional[str] = Form(None),
    construction_type: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Upload a blueprint PDF file and initiate professional HVAC analysis
    
    This endpoint handles file upload, validation, and initiates background processing.
    Returns immediately with a job ID for status tracking.
    
    Args:
        file: PDF blueprint file (max 10MB)
        zip_code: Project ZIP code for climate zone determination
        project_name: Name of the project
        project_type: Type of project (residential/commercial)
        construction_type: Construction type (new/retrofit)
    
    Returns:
        Dict containing job_id and processing information
    
    Raises:
        AutoHVACException: If file validation fails or upload processing fails
    """
    with performance_timer("blueprint_upload", logger):
        # Validate file upload
        validate_file_upload(file, max_size_mb=10, allowed_extensions={".pdf"})
        
        # Validate ZIP code if provided
        if zip_code:
            zip_code = validate_zip_code(zip_code)
        
        try:
            # Read file content
            file_content = await file.read()
            file_size_mb = len(file_content) / 1024 / 1024
            
            logger.info(
                f"Blueprint upload started: {file.filename} ({file_size_mb:.2f}MB)",
                extra={
                    'extra_data': {
                        'filename': file.filename,
                        'file_size_mb': file_size_mb,
                        'zip_code': zip_code,
                        'project_name': project_name
                    }
                }
            )
            
            # Prepare project info
            project_info = {
                key: value for key, value in {
                    "zip_code": zip_code,
                    "project_name": project_name,
                    "project_type": project_type,
                    "construction_type": construction_type
                }.items() if value is not None
            }
            
            # Process through service layer
            result = await blueprint_service.upload_and_process_blueprint(
                file_content=file_content,
                filename=file.filename,
                project_info=project_info
            )
            
            job_id = result.get("job_id")
            if job_id:
                log_blueprint_processing(
                    job_id=job_id,
                    stage="upload",
                    status="completed",
                    details={
                        "filename": file.filename,
                        "file_size_mb": file_size_mb,
                        "project_info": project_info
                    }
                )
            
            return {
                **result,
                "file_size_mb": file_size_mb,
                "estimated_completion_minutes": "2-3",
                "next_steps": "Check processing status using the job_id"
            }
            
        except Exception as e:
            logger.error(f"Blueprint upload failed: {str(e)}", exc_info=True)
            raise AutoHVACException(
                AutoHVACErrors.BLUEPRINT_PROCESSING_FAILED,
                details={
                    "stage": "upload",
                    "filename": file.filename if file else "unknown",
                    "original_error": str(e)
                },
                cause=e
            )

@router.get("/status/{job_id}")
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """
    Get the current processing status of a blueprint analysis job
    
    Args:
        job_id: Unique job identifier returned from upload endpoint
    
    Returns:
        Dict containing status, progress, and other job information
    
    Raises:
        AutoHVACException: If job is not found or status check fails
    """
    with performance_timer(f"status_check_{job_id}", logger):
        try:
            status = await blueprint_service.get_processing_status(job_id)
            
            if status.get('status') == 'not_found':
                raise AutoHVACException(
                    AutoHVACErrors.JOB_NOT_FOUND,
                    details={"job_id": job_id}
                )
            
            logger.debug(
                f"Status check completed for job {job_id}",
                extra={
                    'extra_data': {
                        'job_id': job_id,
                        'status': status.get('status'),
                        'progress': status.get('progress')
                    }
                }
            )
            
            return status
            
        except AutoHVACException:
            raise
        except Exception as e:
            logger.error(f"Status check failed for job {job_id}: {str(e)}", exc_info=True)
            raise AutoHVACException(
                AutoHVACErrors.INTERNAL_SERVER_ERROR,
                details={
                    "operation": "status_check",
                    "job_id": job_id,
                    "original_error": str(e)
                },
                cause=e
            )

@router.get("/results/{job_id}")
async def get_analysis_results(job_id: str) -> Dict[str, Any]:
    """
    Get detailed extraction results for a completed job
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Dict containing complete extraction results and analysis
    
    Raises:
        HTTPException: If job not found or not completed
    """
    try:
        # Check job status first
        status = await blueprint_service.get_processing_status(job_id)
        
        if status.get('status') != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Job {job_id} is not completed. Status: {status.get('status', 'unknown')}"
            )
        
        # Get professional analysis (includes extraction results)
        results = await blueprint_service.get_professional_analysis(job_id)
        
        return {
            **results,
            "download_links": await blueprint_service.list_job_outputs(job_id)
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Results retrieval failed for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis results")

@router.get("/outputs/{job_id}")
async def list_job_outputs(job_id: str) -> List[Dict[str, Any]]:
    """
    List all available output files for a job
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        List of available output files with metadata
    """
    try:
        outputs = await blueprint_service.list_job_outputs(job_id)
        return outputs
        
    except Exception as e:
        logger.error(f"Output listing failed for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list job outputs")

@router.get("/download/{job_id}/{filename}")
async def download_deliverable(job_id: str, filename: str) -> FileResponse:
    """
    Download a specific deliverable file
    
    Args:
        job_id: Unique job identifier
        filename: Name of the file to download
    
    Returns:
        FileResponse with the requested file
    
    Raises:
        AutoHVACException: If file not found or download fails
    """
    with performance_timer(f"file_download_{job_id}_{filename}", logger):
        try:
            file_path = await blueprint_service.get_output_file(job_id, filename)
            
            # Determine media type based on file extension
            media_type_map = {
                '.pdf': 'application/pdf',
                '.json': 'application/json',
                '.dxf': 'application/octet-stream',
                '.svg': 'image/svg+xml',
                '.txt': 'text/plain'
            }
            
            file_ext = file_path.suffix.lower()
            media_type = media_type_map.get(file_ext, 'application/octet-stream')
            
            logger.info(
                f"File download requested: {job_id}/{filename}",
                extra={
                    'extra_data': {
                        'job_id': job_id,
                        'filename': filename,
                        'file_path': str(file_path),
                        'media_type': media_type
                    }
                }
            )
            
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "no-cache"
                }
            )
            
        except FileNotFoundError as e:
            logger.warning(f"File not found: {job_id}/{filename}")
            raise AutoHVACException(
                AutoHVACErrors.FILE_NOT_FOUND,
                details={
                    "job_id": job_id,
                    "filename": filename,
                    "operation": "download"
                },
                cause=e
            )
        except Exception as e:
            logger.error(f"Download failed for {job_id}/{filename}: {str(e)}", exc_info=True)
            handle_file_system_error(e, "file_download", f"{job_id}/{filename}")

@router.get("/extraction/{job_id}")
async def get_extraction_details(job_id: str) -> Dict[str, Any]:
    """
    Get detailed extraction results without professional analysis
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Dict containing raw extraction results
    """
    try:
        results = await blueprint_service.get_extraction_results(job_id)
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Extraction details failed for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve extraction details")

@router.delete("/job/{job_id}")
async def cancel_or_delete_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel an active job or delete completed job data
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Dict containing deletion confirmation
    """
    try:
        # This would need to be implemented in the service layer
        # For now, return a placeholder response
        return {
            "job_id": job_id,
            "message": "Job deletion functionality will be implemented",
            "status": "acknowledged"
        }
        
    except Exception as e:
        logger.error(f"Job deletion failed for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Job deletion failed")

@router.get("/stats/service")
async def get_service_statistics() -> Dict[str, Any]:
    """
    Get service performance and usage statistics
    
    Returns:
        Dict containing service statistics and performance metrics
    """
    try:
        stats = blueprint_service.get_service_stats()
        return {
            "service_status": "healthy",
            "statistics": stats,
            "api_version": "2.0"
        }
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve service statistics")

@router.post("/admin/cleanup")
async def cleanup_expired_jobs(max_age_hours: int = 168) -> Dict[str, Any]:
    """
    Administrative endpoint to clean up expired jobs
    
    Args:
        max_age_hours: Maximum age of jobs to keep (default: 168 hours / 7 days)
    
    Returns:
        Dict containing cleanup results
    """
    try:
        cleaned_count = await blueprint_service.cleanup_expired_jobs(max_age_hours)
        
        return {
            "message": "Cleanup completed successfully",
            "cleaned_items": cleaned_count,
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup operation failed")

@router.get("/stream/{job_id}")
async def stream_processing_progress(job_id: str) -> StreamingResponse:
    """
    Stream real-time processing progress via Server-Sent Events (SSE)
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        StreamingResponse with SSE data containing progress updates
    """
    
    async def event_stream():
        """Generate SSE events for job progress"""
        try:
            last_progress = -1
            max_wait_time = 300  # 5 minutes max wait
            start_time = asyncio.get_event_loop().time()
            
            while True:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > max_wait_time:
                    yield f"event: timeout\ndata: {json.dumps({'error': 'Maximum wait time exceeded'})}\n\n"
                    break
                
                try:
                    # Get current job status
                    status_data = await blueprint_service.get_job_status(job_id)
                    
                    if not status_data:
                        yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                        break
                    
                    current_progress = status_data.get('progress_percentage', 0)
                    job_status = status_data.get('status', 'unknown')
                    
                    # Only send updates when progress changes or every 5 seconds
                    if (current_progress != last_progress or 
                        int(current_time) % 5 == 0):
                        
                        progress_data = {
                            'job_id': job_id,
                            'status': job_status,
                            'progress': current_progress,
                            'stage': status_data.get('current_stage', 'processing'),
                            'message': status_data.get('status_message', ''),
                            'timestamp': current_time
                        }
                        
                        yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"
                        last_progress = current_progress
                    
                    # Check if job is complete
                    if job_status in ['completed', 'failed', 'cancelled']:
                        final_data = {
                            'job_id': job_id,
                            'status': job_status,
                            'progress': 100 if job_status == 'completed' else current_progress,
                            'message': 'Processing complete' if job_status == 'completed' else 'Processing failed',
                            'timestamp': current_time
                        }
                        
                        if job_status == 'completed':
                            final_data['result_url'] = f"/api/blueprint/result/{job_id}"
                        
                        yield f"event: complete\ndata: {json.dumps(final_data)}\n\n"
                        break
                    
                except Exception as e:
                    logger.error(f"Error streaming progress for job {job_id}: {str(e)}")
                    yield f"event: error\ndata: {json.dumps({'error': 'Internal streaming error'})}\n\n"
                    break
                
                # Wait before next update
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"SSE stream failed for job {job_id}: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': 'Stream connection failed'})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the blueprint processing service
    
    Returns:
        Dict containing health status and basic metrics
    """
    try:
        stats = blueprint_service.get_service_stats()
        
        return {
            "status": "healthy",
            "service": "blueprint-processor",
            "version": "2.0",
            "active_jobs": stats["active_jobs"],
            "processor_performance": {
                "avg_processing_time": stats["processor_stats"]["avg_processing_time"],
                "extraction_accuracy": stats["processor_stats"]["extraction_accuracy"],
                "cache_hit_rate": stats["processor_stats"].get("cache_hit_rate", 0.0)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "blueprint-processor",
            "error": str(e)
        }