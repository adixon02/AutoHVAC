import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime

from app.database import get_session
from app.models.user import JobModel, JobStatus
from app.services.job_storage import job_storage

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
    filename: Optional[str] = None
    project_label: Optional[str] = None
    zip_code: Optional[str] = None

class JobListResponse(BaseModel):
    """Job list response model"""
    projects: List[JobStatusResponse]  # Changed from "jobs" to "projects" for frontend compatibility
    total_count: int  # Changed from "total" to "total_count" for frontend compatibility

@router.get("/list", response_model=JobListResponse)
async def list_user_jobs(email: str, limit: int = 50, offset: int = 0, session: Session = Depends(get_session)):
    """
    List jobs for a specific user by email from PostgreSQL
    """
    try:
        # Query user's jobs from PostgreSQL
        statement = (
            select(JobModel)
            .where(JobModel.user_email == email)
            .order_by(JobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        user_jobs = session.exec(statement).all()
        
        # Convert to response format
        job_list = []
        for job in user_jobs:
            job_list.append(JobStatusResponse(
                job_id=job.id,
                status=job.status.value,
                progress=job.progress,
                result=job.result_data,
                error=job.error_data.get("message") if job.error_data else None,
                created_at=job.created_at.isoformat() if job.created_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                filename=job.filename,
                project_label=job.project_label,
                zip_code=job.zip_code
            ))
        
        # Get total count for pagination
        total_statement = select(JobModel).where(JobModel.user_email == email)
        total_count = len(session.exec(total_statement).all())
        
        logger.info(f"Listed {len(job_list)} jobs for user {email} (total: {total_count})")
        
        return JobListResponse(
            projects=job_list,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs for user {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user jobs")

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, session: Session = Depends(get_session)):
    """
    Get status and progress of a specific job from PostgreSQL
    """
    try:
        job = session.get(JobModel, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status.value,
            progress=job.progress,
            result=job.result_data,
            error=job.error_data.get("message") if job.error_data else None,
            created_at=job.created_at.isoformat() if job.created_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            filename=job.filename,
            project_label=job.project_label,
            zip_code=job.zip_code
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")

@router.get("/{job_id}/progress")
async def get_job_progress(job_id: str, session: Session = Depends(get_session)):
    """
    Get just the progress percentage of a job (lightweight endpoint)
    """
    try:
        job = session.get(JobModel, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job.id,
            "status": job.status.value,
            "progress": job.progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job progress for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job progress")

@router.delete("/{job_id}")
async def cancel_job(job_id: str, session: Session = Depends(get_session)):
    """
    Cancel a running job (if possible)
    """
    try:
        job = session.get(JobModel, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status == JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot cancel completed job")
        
        if job.status == JobStatus.FAILED:
            raise HTTPException(status_code=400, detail="Cannot cancel failed job")
        
        # Mark job as cancelled
        job.status = JobStatus.FAILED
        job.error_data = {"message": "Job cancelled by user"}
        job.updated_at = datetime.utcnow()
        
        session.add(job)
        session.commit()
        
        logger.info(f"Job {job_id} cancelled by user")
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")

@router.get("/")
async def list_jobs(limit: int = 10, offset: int = 0, session: Session = Depends(get_session)):
    """
    List recent jobs (for debugging/admin)
    """
    try:
        statement = (
            select(JobModel)
            .order_by(JobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        recent_jobs = session.exec(statement).all()
        
        job_list = []
        for job in recent_jobs:
            job_list.append(JobStatusResponse(
                job_id=job.id,
                status=job.status.value,
                progress=job.progress,
                result=job.result_data,
                error=job.error_data.get("message") if job.error_data else None,
                created_at=job.created_at.isoformat() if job.created_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                filename=job.filename,
                project_label=job.project_label,
                zip_code=job.zip_code
            ))
        
        # Get total count
        total_statement = select(JobModel)
        total_count = len(session.exec(total_statement).all())
        
        return JobListResponse(
            projects=job_list,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to list recent jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")

