import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)
router = APIRouter()

class JobStatusResponse(BaseModel):
    """Job status response model"""
    job_id: str
    status: str
    progress: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

class JobListResponse(BaseModel):
    """Job list response model"""
    projects: List[JobStatusResponse]  # Changed from "jobs" to "projects" for frontend compatibility
    total_count: int  # Changed from "total" to "total_count" for frontend compatibility

# Import jobs from blueprint route
from app.routes.blueprint import jobs

@router.get("/list", response_model=JobListResponse)
async def list_user_jobs(email: str, limit: int = 50, offset: int = 0):
    """
    List jobs for a specific user by email
    """
    job_list = []
    
    # Filter jobs by user email (for now, return all completed jobs)
    # In production, you'd filter by user_email field in job data
    for job_id, job_data in jobs.items():
        # For now, include all completed jobs as this user's jobs
        # In production, you'd check: if job_data.get("user_email") == email
        if job_data["status"] == "completed":
            job_list.append(JobStatusResponse(
                job_id=job_id,
                status=job_data["status"],
                progress=job_data["progress"],
                result=job_data["result"],
                error=job_data["error"],
                created_at=None,  # TODO: Add timestamps to job storage
                completed_at=None
            ))
    
    # Sort by job_id (newest first, roughly)
    job_list = sorted(job_list, key=lambda x: x.job_id, reverse=True)
    
    # Apply pagination
    paginated_jobs = job_list[offset:offset + limit]
    
    logger.info(f"Listed {len(paginated_jobs)} jobs for user {email}")
    
    return JobListResponse(
        projects=paginated_jobs,
        total_count=len(job_list)
    )

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status and progress of a specific job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"]
    )

@router.get("/{job_id}/progress")
async def get_job_progress(job_id: str):
    """
    Get just the progress percentage of a job (lightweight endpoint)
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"]
    }

@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running job (if possible)
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    if job["status"] == "failed":
        raise HTTPException(status_code=400, detail="Cannot cancel failed job")
    
    # Mark job as cancelled
    jobs[job_id]["status"] = "cancelled"
    jobs[job_id]["error"] = "Job cancelled by user"
    
    logger.info(f"Job {job_id} cancelled by user")
    
    return {"message": f"Job {job_id} cancelled successfully"}

@router.get("/")
async def list_jobs(limit: int = 10, offset: int = 0):
    """
    List recent jobs (for debugging/admin)
    """
    job_list = []
    
    # Convert jobs dict to list and sort by creation (newest first)
    sorted_jobs = list(jobs.items())[-limit-offset:-offset if offset > 0 else None]
    
    for job_id, job_data in sorted_jobs:
        job_list.append(JobStatusResponse(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            result=job_data["result"],
            error=job_data["error"]
        ))
    
    return JobListResponse(
        projects=job_list,
        total_count=len(jobs)
    )

