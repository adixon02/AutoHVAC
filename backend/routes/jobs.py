from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from services.user_service import user_service
from services.s3_storage import storage_service
from models.db_models import Project, JobStatus
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ProjectSummary(BaseModel):
    id: str
    project_label: str
    filename: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    has_pdf_report: bool = False

class UserProjectsResponse(BaseModel):
    projects: List[ProjectSummary]
    total_count: int

@router.get("/list")
async def list_user_projects(
    email: EmailStr = Query(..., description="User email address"),
    limit: Optional[int] = Query(50, le=100, description="Number of projects to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """List all projects for a user"""
    try:
        # Verify user exists and email is verified
        await user_service.require_verified(email, session)
        
        # Get user projects
        projects = await job_service.get_user_projects(email, limit, session)
        total_count = await job_service.count_user_projects(email, session)
        
        # Convert to response format
        project_summaries = []
        for project in projects:
            project_summaries.append(ProjectSummary(
                id=project.id,
                project_label=project.project_label,
                filename=project.filename,
                status=project.status.value,
                created_at=project.created_at.isoformat(),
                completed_at=project.completed_at.isoformat() if project.completed_at else None,
                has_pdf_report=bool(project.pdf_report_path)
            ))
        
        return UserProjectsResponse(
            projects=project_summaries,
            total_count=total_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects for {email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/{project_id}/download")
async def download_project_report(
    project_id: str,
    email: EmailStr = Query(..., description="User email address"),
    session: AsyncSession = Depends(get_async_session)
):
    """Download PDF report for a project"""
    try:
        # Verify user owns the project
        project = await job_service.get_project_by_user_and_id(project_id, email, session)
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        # Check if report is completed and has PDF
        if project.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Project not completed yet"
            )
        
        if not project.pdf_report_path:
            raise HTTPException(
                status_code=404,
                detail="PDF report not available"
            )
        
        # Generate pre-signed URL for S3 download
        try:
            download_url = storage_service.get_download_url(
                project_id=project_id,
                file_type="report",
                expiry_seconds=3600  # 1 hour expiry
            )
            
            # Return redirect to pre-signed URL
            from fastapi.responses import RedirectResponse
            return RedirectResponse(
                url=download_url,
                status_code=303  # See Other - appropriate for GET after POST
            )
            
        except FileNotFoundError:
            logger.error(f"PDF report not found in S3 for project {project_id}")
            raise HTTPException(
                status_code=404,
                detail="Report file not found"
            )
        except Exception as e:
            logger.error(f"Error generating download URL for project {project_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate download URL"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {project_id} for {email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/{project_id}/details")
async def get_project_details(
    project_id: str,
    email: EmailStr = Query(..., description="User email address"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get detailed information about a project"""
    try:
        # Verify user owns the project
        project = await job_service.get_project_by_user_and_id(project_id, email, session)
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        return {
            "id": project.id,
            "project_label": project.project_label,
            "filename": project.filename,
            "file_size": project.file_size,
            "status": project.status.value,
            "result": project.result,
            "error": project.error,
            "created_at": project.created_at.isoformat(),
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
            "has_pdf_report": bool(project.pdf_report_path)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project details {project_id} for {email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    email: EmailStr = Query(..., description="User email address"),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a project (admin/cleanup function)"""
    try:
        # Verify user owns the project
        project = await job_service.get_project_by_user_and_id(project_id, email, session)
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        # Delete PDF report from S3 if it exists
        if project.pdf_report_path:
            try:
                # Delete report from S3 using the S3 key directly
                s3_key = f"reports/{project_id}_report.pdf"
                storage_service.s3_client.delete_object(
                    Bucket=storage_service.bucket_name,
                    Key=s3_key
                )
                logger.info(f"Deleted report from S3: {s3_key}")
            except Exception as e:
                logger.warning(f"Could not delete PDF report from S3: {str(e)}")
        
        # Delete from database
        success = await job_service.delete_project(project_id, session)
        
        if success:
            return {"message": "Project deleted successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete project"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id} for {email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )