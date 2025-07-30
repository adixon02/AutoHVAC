from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from models.schemas import JobStatus as JobStatusSchema
from models.db_models import JobStatus
from app.config import DEBUG, DEV_VERIFIED_EMAILS
import logging

router = APIRouter()





@router.get("/{job_id}/debug")
async def get_job_debug(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    # Check DEBUG mode or dev email list
    user_email = request.headers.get("X-User-Email", "")
    if not (DEBUG or user_email in DEV_VERIFIED_EMAILS):
        raise HTTPException(status_code=403, detail="Debug access denied")
    
    project = await job_service.get_project(job_id, session)
    if not project:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": project.id,
        "status": project.status.value,
        "progress_percent": project.progress_percent,
        "current_stage": project.current_stage,
        "error": project.error,
        "created_at": project.created_at.isoformat(),
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "assumptions_collected": project.assumptions_collected,
        "duct_config": project.duct_config,
        "heating_fuel": project.heating_fuel,
        "file_size": project.file_size
    }

@router.get("/{job_id}", response_model=JobStatusSchema)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    try:
        logging.info(f"🔍 Fetching job status for job_id: {job_id}")
        project = await job_service.get_project(job_id, session)
        
        if not project:
            logging.warning(f"❌ Job not found in database: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
        
        logging.info(f"✅ Successfully retrieved job status for {job_id}: status={project.status.value}, error={project.error}")
        
        # Build response data
        response_data = {
            "job_id": job_id,
            "status": project.status.value,
            "result": project.result,
            "error": project.error,
            "progress_percent": project.progress_percent,
            "current_stage": project.current_stage
        }
        
        # Add upgrade prompt for completed jobs if user has used their free report
        if project.status == JobStatus.COMPLETED:
            from services.user_service import user_service
            eligibility = await user_service.check_free_report_eligibility(project.user_email, session)
            
            # Show upgrade prompt if they've used their free report and don't have subscription
            if eligibility["free_report_used"] and not eligibility["has_subscription"]:
                response_data["upgrade_prompt"] = {
                    "show": True,
                    "title": "Love AutoHVAC? Go Pro!",
                    "subtitle": "You've used your free report. Upgrade for unlimited analyses.",
                    "benefits": [
                        "Process unlimited blueprints",
                        "Priority processing queue",
                        "Bulk upload support",
                        "API access",
                        "Premium support"
                    ],
                    "cta_text": "Upgrade Now",
                    "cta_url": "/subscribe",
                    "cta_button_text": "Get Unlimited Reports",
                    "limited_time_offer": "20% OFF - Limited Time"
                }
        
        # Return appropriate status codes
        if project.status == JobStatus.FAILED:
            return JSONResponse(
                content=response_data,
                status_code=500
            )
        
        # Return 202 for in-progress jobs
        if project.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            return JSONResponse(
                content=response_data,
                status_code=202
            )
        
        # Return 200 for completed
        return response_data
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as exc:
        logging.exception(f"Unexpected error fetching job status for {job_id}: {type(exc).__name__}: {str(exc)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(exc)}"
        )