import os
import uuid
import tempfile
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

# Import database and user service for paywall enforcement
from app.database import get_session
from app.services.user_service import user_service
from app.services.s3_storage import storage_service

# Import our working pipeline
from pipeline_v3 import run_pipeline_v3

logger = logging.getLogger(__name__)
router = APIRouter()

class UploadResponse(BaseModel):
    """Response model for blueprint upload"""
    job_id: str
    status: str
    message: str

class JobResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None

# In-memory job storage (for MVP - replace with Redis/DB in production)
jobs = {}

@router.post("/upload", response_model=UploadResponse)
async def upload_blueprint(
    request: Request,
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    email: str = Form(...),  # CRITICAL: Email required for paywall enforcement
    device_fingerprint: Optional[str] = Form(None),  # ANTI-FRAUD: Device fingerprint
    openai_api_key: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """
    Upload a blueprint PDF and start HVAC load calculation
    
    CRITICAL PAYWALL ENFORCEMENT: This endpoint enforces our freemium business model.
    Users get exactly 1 free report, then must subscribe for more.
    """
    try:
        # Extract client IP for tracking
        client_ip = request.client.host if request.client else "unknown"
        
        # CRITICAL PAYWALL CHECK: Enforce business model before processing
        logger.info(f"🔒 PAYWALL CHECK: Checking upload permission for {email} (Device: {device_fingerprint[:12] if device_fingerprint else 'None'}...)")
        
        if not user_service.validate_email_format(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # ENHANCED ANTI-FRAUD: Check both email AND device fingerprint
        can_upload = user_service.can_upload_new_report(email, session, device_fingerprint, client_ip)
        
        if not can_upload:
            logger.warning(f"🚫 PAYWALL BLOCKED: {email} attempted upload but not allowed")
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "subscription_required",
                    "message": "You've used your free report. Please upgrade to continue.",
                    "upgrade_required": True,
                    "email": email
                }
            )
        
        logger.info(f"✅ PAYWALL PASSED: {email} can upload")
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Validate zip code
        if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
            raise HTTPException(status_code=400, detail="Valid 5-digit zip code required")
        
        # Use environment API key if not provided
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key required")
        
        # Initialize job status with user tracking and timestamps
        from datetime import datetime
        jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "filename": file.filename,
            "zip_code": zip_code,
            "email": email,  # Track which user this belongs to
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Save uploaded file temporarily AND to S3 for data collection
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 📊 DATA COLLECTION: Save original blueprint to S3
        await storage_service.save_upload(job_id, content, file.filename)
        
        # CRITICAL: Mark free report as used if this is a new user's first report
        # Also ensure user exists with device fingerprint tracking
        user = user_service.get_or_create_user(email, session, device_fingerprint, client_ip)
        is_first_report = not user.free_report_used
        
        # Start processing in background with user tracking
        asyncio.create_task(process_blueprint_async(
            job_id, temp_file_path, zip_code, api_key, email, session, is_first_report
        ))
        
        logger.info(f"Started job {job_id} for file {file.filename}, zip {zip_code}")
        
        return UploadResponse(
            job_id=job_id,
            status="processing",
            message="Blueprint upload successful. Processing started."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_blueprint_async(
    job_id: str, 
    pdf_path: str, 
    zip_code: str, 
    api_key: str, 
    email: str, 
    session: Session, 
    is_first_report: bool
):
    """
    Process blueprint asynchronously using pipeline_v3
    """
    try:
        # Update progress
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        
        logger.info(f"Job {job_id}: Starting pipeline_v3 processing")
        
        # Run pipeline_v3 (this is your working pipeline!)
        # Note: run_pipeline_v3 returns a dictionary, not an object
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            run_pipeline_v3,
            pdf_path, 
            zip_code, 
            None,  # user_inputs (optional)
            api_key
        )
        
        # Pipeline_v3 returns a dictionary - check if it has heating load data
        if result and "heating_load_btu_hr" in result:
            # Result is already a dictionary, just add some calculated fields
            result_data = {
                **result,  # Include all pipeline results
                "heating_tons": result["heating_load_btu_hr"] / 12000,  # Convert BTU to tons
                "cooling_tons": result["cooling_load_btu_hr"] / 12000,
                "zones_created": result.get("zones", 0),
                "spaces_detected": result.get("spaces", 0),
                "garage_detected": result.get("garage_detected", False),
                "bonus_over_garage": result.get("bonus_over_garage", False),
                "confidence_score": result.get("confidence", 0.0),
                "warnings": result.get("warnings", []),
                "zone_loads": result.get("zone_loads", {}),
                "processing_time_seconds": result.get("processing_time", 0)
            }
            
            # Add completion timestamp
            from datetime import datetime
            completion_time = datetime.utcnow().isoformat()
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["result"] = result_data
            jobs[job_id]["completed_at"] = completion_time
            
            # CRITICAL: Mark free report as used on successful completion
            if is_first_report:
                success = user_service.mark_free_report_used(email, session)
                if success:
                    logger.info(f"🔒 PAYWALL: Marked free report as used for {email}")
                else:
                    logger.error(f"🔒 PAYWALL ERROR: Failed to mark free report used for {email}")
            
            # 📊 DATA COLLECTION: Save comprehensive job data to S3
            try:
                await storage_service.save_complete_job_data(job_id, jobs[job_id])
                logger.info(f"📊 DATA: Saved complete dataset for job {job_id}")
            except Exception as e:
                logger.error(f"📊 DATA ERROR: Failed to save complete data for {job_id}: {e}")
                # Don't fail the job if data collection fails
            
            logger.info(f"Job {job_id}: Completed successfully - {result['heating_load_btu_hr']:,.0f} BTU/hr heating")
            
        else:
            from datetime import datetime
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Pipeline processing failed: No valid result returned"
            jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            
            # 📊 DATA COLLECTION: Save failure data for analysis
            try:
                await storage_service.save_complete_job_data(job_id, jobs[job_id])
                logger.info(f"📊 DATA: Saved failure data for job {job_id}")
            except Exception as data_error:
                logger.error(f"📊 DATA ERROR: Failed to save failure data for {job_id}: {data_error}")
            
            logger.error(f"Job {job_id}: Pipeline failed - no valid result")
            
    except Exception as e:
        from datetime import datetime
        
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        
        # 📊 DATA COLLECTION: Save error data for analysis
        try:
            await storage_service.save_complete_job_data(job_id, jobs[job_id])
            logger.info(f"📊 DATA: Saved error data for job {job_id}")
        except Exception as data_error:
            logger.error(f"📊 DATA ERROR: Failed to save error data for {job_id}: {data_error}")
        
        logger.error(f"Job {job_id}: Processing error - {e}")
        
    finally:
        # Cleanup temporary file
        try:
            os.unlink(pdf_path)
        except:
            pass

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get status of a processing job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"]
    )

@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """
    Get detailed result of completed job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed. Status: {job['status']}")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "filename": job["filename"],
        "zip_code": job["zip_code"],
        "result": job["result"]
    }

@router.get("/users/{email}/can-upload")
async def check_upload_permission(email: str, session: Session = Depends(get_session)):
    """
    CRITICAL PAYWALL ENDPOINT: Check if a user can upload more blueprints
    
    This endpoint enforces our freemium business model and prevents revenue leakage.
    """
    try:
        logger.info(f"🔒 CHECKING UPLOAD PERMISSION: {email}")
        
        if not user_service.validate_email_format(email):
            return {
                "can_upload": False,
                "reason": "invalid_email",
                "uploads_remaining": 0,
                "subscription_required": False,
                "error": "Invalid email format"
            }
        
        # Get comprehensive eligibility status
        eligibility = user_service.check_free_report_eligibility(email, session)
        can_upload = user_service.can_upload_new_report(email, session)
        has_subscription = user_service.has_active_subscription(email, session)
        
        if has_subscription:
            # Paying customers get unlimited uploads
            return {
                "can_upload": True,
                "reason": "active_subscription",
                "uploads_remaining": -1,  # Unlimited
                "subscription_required": False,
                "user_status": "paying_customer"
            }
        elif can_upload:
            # New user or user who hasn't used their free report
            return {
                "can_upload": True,
                "reason": "free_report_available",
                "uploads_remaining": 1,
                "subscription_required": False,
                "user_status": "new_user" if eligibility["reason"] == "new_user" else "existing_user",
                "free_report_used": eligibility["free_report_used"]
            }
        else:
            # User has used free report and needs to upgrade
            return {
                "can_upload": False,
                "reason": "free_report_exhausted",
                "uploads_remaining": 0,
                "subscription_required": True,
                "user_status": "needs_upgrade",
                "message": "You've used your free report. Please upgrade to continue."
            }
            
    except Exception as e:
        logger.error(f"Error checking upload permission for {email}: {e}")
        # Fail closed - don't allow upload on error
        return {
            "can_upload": False,
            "reason": "system_error",
            "uploads_remaining": 0,
            "subscription_required": False,
            "error": "System error checking permissions"
        }