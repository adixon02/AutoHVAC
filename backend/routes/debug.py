"""
Debug API endpoints for job analysis and troubleshooting
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from services.s3_storage import storage_service
from services.job_service import job_service
from database import get_async_session, AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/jobs/{project_id}/analysis")
async def get_job_analysis(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve complete analysis JSON for a job
    
    Returns the full blueprint analysis including all room data,
    parsing metadata, and confidence scores.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # Get analysis JSON from S3
        try:
            analysis_data = storage_service.get_json(project_id, 'analysis.json')
            return {
                "success": True,
                "project_id": project_id,
                "analysis": analysis_data
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail="Analysis data not found. This job may have been processed before JSON storage was implemented."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{project_id}/hvac-results")
async def get_hvac_results(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve HVAC calculation results for a job
    
    Returns the complete HVAC load calculations including
    heating/cooling loads per room and total building loads.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # Get HVAC results from S3
        try:
            hvac_data = storage_service.get_json(project_id, 'hvac_results.json')
            return {
                "success": True,
                "project_id": project_id,
                "hvac_results": hvac_data
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail="HVAC results not found. This job may still be processing or failed."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HVAC results for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{project_id}/gpt4v-raw")
async def get_gpt4v_raw(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve raw GPT-4V response for debugging
    
    Returns the raw response from GPT-4V including the model used,
    prompt, and unprocessed response text.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # Get GPT-4V raw response from S3
        try:
            gpt4v_data = storage_service.get_json(project_id, 'gpt4v_raw.json')
            return {
                "success": True,
                "project_id": project_id,
                "gpt4v_raw": gpt4v_data
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail="GPT-4V data not found. This job may not have used AI analysis."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GPT-4V data for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{project_id}/metadata")
async def get_job_metadata(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve job metadata including processing times and stages
    
    Returns metadata about the job processing including timestamps,
    processing duration, stages completed, and any errors.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # Get metadata from S3
        try:
            metadata = storage_service.get_json(project_id, 'metadata.json')
            return {
                "success": True,
                "project_id": project_id,
                "metadata": metadata
            }
        except FileNotFoundError:
            # Try to construct basic metadata from database
            if project:
                return {
                    "success": True,
                    "project_id": project_id,
                    "metadata": {
                        "status": project.status.value if project else "unknown",
                        "created_at": str(project.created_at) if project else None,
                        "completed_at": str(project.completed_at) if project else None,
                        "note": "Detailed metadata not available for this job"
                    }
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Metadata not found"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{project_id}/files")
async def list_job_files(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all files stored for a job
    
    Returns a list of all files stored in S3 for this job,
    useful for understanding what data is available.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # List files from S3
        files = storage_service.list_job_files(project_id)
        
        # Categorize files
        categorized = {
            "blueprint": [],
            "analysis": [],
            "results": [],
            "debug": [],
            "other": []
        }
        
        for file in files:
            if file == "blueprint.pdf":
                categorized["blueprint"].append(file)
            elif file.endswith(".json") and "debug/" not in file:
                if "analysis" in file:
                    categorized["analysis"].append(file)
                elif "hvac" in file or "result" in file:
                    categorized["results"].append(file)
                else:
                    categorized["other"].append(file)
            elif file.startswith("debug/"):
                categorized["debug"].append(file)
            else:
                categorized["other"].append(file)
        
        return {
            "success": True,
            "project_id": project_id,
            "total_files": len(files),
            "files": files,
            "categorized": categorized
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{project_id}/debug/{filename}")
async def get_debug_file(
    project_id: str,
    filename: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve a specific debug file for a job
    
    Debug files contain validation failures, error logs, and
    other diagnostic information.
    """
    try:
        # Debug endpoints don't check user ownership for easier troubleshooting
        project = await job_service.get_project(project_id, session)
        if not project:
            logger.warning(f"Project {project_id} not found in database")
        
        # Get debug file from S3
        try:
            debug_data = storage_service.get_json(project_id, f"debug/{filename}")
            return {
                "success": True,
                "project_id": project_id,
                "filename": filename,
                "data": debug_data
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, 
                detail=f"Debug file {filename} not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get debug file {filename} for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))