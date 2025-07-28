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
            from app.middleware.error_handler import create_error_response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=404,
                content=create_error_response("JobNotFound", "Job not found", 404),
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        
        logging.info(f"Successfully retrieved job status for {job_id}: {project.status.value}")
        
        # Return HTTP 500 for failed jobs with structured error
        if project.status.value == "error" and project.error:
            from app.middleware.error_handler import create_error_response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content=create_error_response("PipelineError", project.error, 500),
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        
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
        logging.error(f"Unexpected error fetching job status for {job_id}: {type(exc).__name__}: {str(exc)}")
        # Let the global exception handler deal with this
        raise