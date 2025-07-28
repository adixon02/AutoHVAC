from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from models.schemas import JobStatus
import logging

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        logging.info(f"Fetching job status for job_id: {job_id}")
        project = await job_service.get_project(job_id, session)
        
        if not project:
            logging.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        logging.info(f"Successfully retrieved job status for {job_id}: status={project.status.value}, error={project.error}")
        
        # Return normal 200 response with job status (including failed jobs)
        return JobStatus(
            job_id=job_id,
            status=project.status.value,
            result=project.result,
            error=project.error,
            assumptions_collected=project.assumptions_collected
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as exc:
        logging.exception(f"Unexpected error fetching job status for {job_id}: {type(exc).__name__}: {str(exc)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(exc)}"
        )