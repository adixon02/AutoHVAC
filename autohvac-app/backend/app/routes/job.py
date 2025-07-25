"""
Job status and result polling endpoint
"""
from fastapi import APIRouter
from datetime import datetime

from ..models.responses import JobResponse
from ..models.requests import JobStatusEnum
from ..core import get_logger, create_http_exception
from ..services.job_storage import job_storage

router = APIRouter()
logger = get_logger(__name__)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get job status and results by job ID.
    
    Returns job status including:
    - Current processing status
    - Progress percentage
    - Results (if completed)
    - Error information (if failed)
    """
    job_data = job_storage.get_job(job_id)
    
    if not job_data:
        logger.warning(f"Job not found: {job_id}")
        raise create_http_exception(404, f"Job {job_id} not found")
    
    # Convert timestamps
    created_at = datetime.fromisoformat(job_data["created_at"])
    updated_at = datetime.fromisoformat(job_data["updated_at"])
    
    # Calculate processing time if completed
    processing_time = None
    if job_data["status"] in [JobStatusEnum.COMPLETED.value, JobStatusEnum.FAILED.value]:
        processing_time = (updated_at - created_at).total_seconds()
    
    return JobResponse(
        job_id=job_id,
        status=JobStatusEnum(job_data["status"]),
        created_at=created_at,
        updated_at=updated_at,
        progress_percent=job_data.get("progress_percent"),
        message=job_data.get("message"),
        result=job_data.get("result"),
        error=job_data.get("error"),
        processing_time_seconds=processing_time
    )