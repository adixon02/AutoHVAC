from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from models.schemas import JobStatus
import logging

router = APIRouter()

@router.get("/test")
async def test_route():
    """Simple test route to verify basic functionality"""
    try:
        return {"status": "ok", "message": "Job router is working"}
    except Exception as e:
        logging.exception(f"Test route failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db-test/{job_id}")
async def test_db_connection(
    job_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Test database connection with detailed logging"""
    try:
        logging.info(f"Testing DB connection for job_id: {job_id}")
        
        # Test session creation
        logging.info("✅ Database session created")
        
        # Test job service
        project = await job_service.get_project(job_id, session)
        logging.info(f"✅ job_service.get_project returned: {project}")
        
        if project:
            return {
                "status": "found",
                "job_id": job_id,
                "project_status": project.status.value,
                "has_error": bool(project.error)
            }
        else:
            return {
                "status": "not_found",
                "job_id": job_id,
                "message": "Job not found (this is expected for test IDs)"
            }
    
    except Exception as exc:
        logging.exception(f"DB test failed for {job_id}: {exc}")
        return {
            "status": "error",
            "job_id": job_id,
            "error": str(exc),
            "error_type": type(exc).__name__
        }

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