"""
Blueprint upload endpoint with streaming support
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import time

from ..models.responses import UploadResponse
from ..models.requests import JobStatusEnum
from ..core import settings, get_logger, FileSizeError, FileUploadError, create_http_exception
from ..services.file_handler import file_handler
from ..services.job_storage import job_storage
from ..tasks.blueprint_processing import process_blueprint_background

router = APIRouter()
logger = get_logger(__name__)


@router.options("/upload")
async def upload_options():
    """Handle CORS preflight for upload endpoint"""
    return JSONResponse(
        status_code=204,
        headers={
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "600"
        }
    )


@router.post("/upload", status_code=202, response_model=UploadResponse)
async def upload_blueprint(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...)
):
    """
    Upload blueprint file for processing.
    
    Features:
    - Streams file to disk in 1MB chunks
    - Rejects files > 150MB with HTTP 413
    - Returns HTTP 202 with job_id within 2 seconds
    - Queues background processing task
    """
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.info(
        "Blueprint upload started",
        extra={
            "request_id": request_id,
            "filename": file.filename,
            "content_type": file.content_type
        }
    )
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise create_http_exception(400, "Only PDF files are supported")
    
    try:
        # Stream file to disk with size limits
        file_path, file_size = await file_handler.save_upload_file(file)
        
        # Create job entry
        job_id = job_storage.create_job(file.filename, file_size)
        
        # Queue background processing task
        background_tasks.add_task(
            process_blueprint_background,
            job_id=job_id,
            file_path=file_path,
            request_id=request_id
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Blueprint upload completed",
            extra={
                "request_id": request_id,
                "job_id": job_id,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "processing_time_ms": round(processing_time, 2)
            }
        )
        
        return UploadResponse(
            job_id=job_id,
            status=JobStatusEnum.QUEUED,
            message="File uploaded successfully and queued for processing",
            file_size_bytes=file_size,
            filename=file.filename
        )
        
    except FileSizeError as e:
        logger.warning(f"File too large: {e}", extra={"request_id": request_id})
        raise create_http_exception(413, str(e))
        
    except FileUploadError as e:
        logger.error(f"Upload failed: {e}", extra={"request_id": request_id})
        raise create_http_exception(400, str(e))
        
    except Exception as e:
        logger.error(
            f"Unexpected upload error: {e}",
            extra={"request_id": request_id},
            exc_info=True
        )
        raise create_http_exception(500, "Upload failed due to server error")