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
from services.report_generator import ValueReportGenerator

# Import job storage
from app.services.job_storage import job_storage

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
    # Removed device_fingerprint parameter
    openai_api_key: Optional[str] = Form(None),
    # 🎯 ENHANCED USER INPUTS: Strategic fields for maximum load calculation accuracy
    project_label: Optional[str] = Form(None),  # Project name
    square_footage: Optional[str] = Form(None),  # Most critical for accurate calculations (conditioned space only)
    number_of_stories: Optional[str] = Form(None),  # User confirmation vs AI detection
    
    # 🏠 FOUNDATION AND BASEMENT INTELLIGENCE: Critical for thermal envelope
    foundation_type: Optional[str] = Form(None),  # slab_on_grade, crawlspace, basement
    basement_type: Optional[str] = Form(None),  # full, daylight (only if foundation_type=basement)
    basement_status: Optional[str] = Form(None),  # finished, unfinished (only if foundation_type=basement)
    
    # 🔥 HVAC SYSTEM INTELLIGENCE: Enhanced equipment sizing
    duct_type: Optional[str] = Form(None),  # ducted, ductless
    duct_location: Optional[str] = Form(None),  # conditioned, attic, crawlspace (only if duct_type=ducted)
    heating_fuel: Optional[str] = Form(None),  # gas_propane, heat_pump, dual_fuel
    
    # 🏠 BUILDING PERFORMANCE: Thermal envelope optimization
    window_performance: Optional[str] = Form(None),  # Thermal envelope accuracy
    building_orientation: Optional[str] = Form(None),  # Solar gain calculations
    
    # 🔄 LEGACY COMPATIBILITY: Kept for backward compatibility
    duct_config: Optional[str] = Form(None),  # Legacy field
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
        logger.info(f"🔒 PAYWALL CHECK: Checking upload permission for {email}")
        
        if not user_service.validate_email_format(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # ENHANCED ANTI-FRAUD: Check both email AND device fingerprint
        can_upload = user_service.can_upload_new_report(email, session)
        
        # Check if user can process immediately or needs to upgrade
        should_process_immediately = can_upload
        needs_upgrade = not can_upload
        
        if should_process_immediately:
            logger.info(f"✅ PROCESSING IMMEDIATELY: {email} can upload and process")
        else:
            logger.info(f"📋 UPLOAD TO PENDING: {email} can upload but needs upgrade to process")
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # CRITICAL: Get user info FIRST to determine is_first_report
        user = user_service.get_or_create_user(email, session)
        is_first_report = not user.free_report_used and should_process_immediately
        
        # CRITICAL: Create job record IMMEDIATELY to prevent 404 race condition
        from datetime import datetime
        initial_status = "processing" if should_process_immediately else "pending_upgrade"
        job_data = {
            "status": initial_status,
            "progress": 0,
            "filename": file.filename,
            "project_label": project_label or file.filename,  # Use project name if provided
            "zip_code": zip_code,
            "email": email,  # Track which user this belongs to
            "user_inputs": {},  # Store for analytics - will be updated later
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None,
            "needs_upgrade": needs_upgrade,
            "saved_file_path": None,  # Will store S3 path for pending jobs
            "is_first_report": is_first_report
        }
        
        # Save to PostgreSQL (with Redis cache)
        job_storage.save_job(job_id, job_data)
        
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
        
        # Save uploaded file temporarily AND to S3 for data collection
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 📊 DATA COLLECTION: Save original blueprint to S3
        s3_path = await storage_service.save_upload(job_id, content, file.filename)
        job_storage.update_job(job_id, {"saved_file_path": s3_path})
        
        # User already created above, just use the existing user object
        
        # 🎯 COLLECT ENHANCED USER INPUTS: Maximum accuracy data for pipeline_v3
        form_inputs = {
            # Core building characteristics
            "square_footage": square_footage,
            "number_of_stories": number_of_stories,
            
            # Foundation and basement intelligence
            "foundation_type": foundation_type,
            "basement_type": basement_type,
            "basement_status": basement_status,
            
            # HVAC system intelligence
            "duct_type": duct_type,
            "duct_location": duct_location,
            "heating_fuel": heating_fuel,
            
            # Building performance
            "window_performance": window_performance,
            "building_orientation": building_orientation,
            
            # Legacy compatibility
            "duct_config": duct_config
        }
        
        # Filter out None/empty values - only pass real user inputs
        form_inputs = {k: v for k, v in form_inputs.items() if v and v != "not_sure"}
        
        # 🔄 MAP TO PIPELINE_V3 FORMAT: Convert form fields to pipeline expected names
        user_inputs = {}
        
        # 📏 CRITICAL: Conditioned square footage (most important for accuracy)
        if "square_footage" in form_inputs:
            try:
                user_inputs["conditioned_sqft"] = float(form_inputs["square_footage"])
                # Also set legacy field for backward compatibility
                user_inputs["total_sqft"] = user_inputs["conditioned_sqft"]
                logger.info(f"📏 CONDITIONED SQFT: User provided {user_inputs['conditioned_sqft']:.0f} sqft (current living space)")
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Invalid square footage: {form_inputs['square_footage']}")
        
        # 🏠 STORIES: User confirmation vs AI detection
        if "number_of_stories" in form_inputs:
            story_mapping = {"1": 1, "2": 2, "3+": 3}
            user_inputs["floor_count"] = story_mapping.get(form_inputs["number_of_stories"], 2)
            logger.info(f"🏠 STORIES: User confirmed {user_inputs['floor_count']} floors vs AI detection")
        
        # 🏠 FOUNDATION INTELLIGENCE: Critical for thermal envelope calculations
        if "foundation_type" in form_inputs:
            user_inputs["foundation_type"] = form_inputs["foundation_type"]
            user_inputs["foundationType"] = form_inputs["foundation_type"]  # Also pass camelCase
            logger.info(f"🏗️ FOUNDATION: {form_inputs['foundation_type']} affects thermal envelope")
            
        if "basement_type" in form_inputs:
            user_inputs["basement_type"] = form_inputs["basement_type"]
            user_inputs["basementType"] = form_inputs["basement_type"]  # Also pass camelCase
            logger.info(f"🏠 BASEMENT TYPE: {form_inputs['basement_type']}")
            
        if "basement_status" in form_inputs:
            user_inputs["basement_status"] = form_inputs["basement_status"]
            user_inputs["basementStatus"] = form_inputs["basement_status"]  # Also pass camelCase
            if form_inputs["basement_status"] == "unfinished":
                logger.info(f"📐 SIZING STRATEGY: Unfinished basement - sizing for future finishing")
        
        # 🔥 HVAC SYSTEM INTELLIGENCE: Enhanced ductwork mapping
        # IMPORTANT: Pass BOTH the original fields AND the computed duct_config for maximum compatibility
        if "duct_type" in form_inputs:
            # Pass through the original duct_type as-is for pipeline_v3
            user_inputs["ductType"] = form_inputs["duct_type"]
            
            if "duct_location" in form_inputs:
                # Pass through the original duct_location as-is for pipeline_v3
                user_inputs["ductLocation"] = form_inputs["duct_location"]
                
                # Also create the combined duct_config for backward compatibility
                duct_type = form_inputs["duct_type"]
                duct_location = form_inputs["duct_location"]
                
                if duct_type == "ducted" and duct_location:
                    if duct_location == "conditioned":
                        user_inputs["duct_config"] = "ducted_conditioned"
                    elif duct_location == "attic":
                        user_inputs["duct_config"] = "ducted_attic"
                    elif duct_location == "crawlspace":
                        user_inputs["duct_config"] = "ducted_crawl"
                elif duct_type == "ductless":
                    user_inputs["duct_config"] = "ductless"
                    
                logger.info(f"🌀 DUCT SYSTEM: type={duct_type}, location={duct_location} → config={user_inputs.get('duct_config', 'unknown')}")
        
        # Legacy duct_config support
        elif "duct_config" in form_inputs:
            user_inputs["duct_config"] = form_inputs["duct_config"]
            # Decompose legacy duct_config into separate fields for pipeline_v3
            if form_inputs["duct_config"] == "ductless":
                user_inputs["ductType"] = "ductless"
                user_inputs["ductLocation"] = None
            elif form_inputs["duct_config"].startswith("ducted_"):
                user_inputs["ductType"] = "ducted"
                location_map = {
                    "ducted_attic": "attic",
                    "ducted_crawl": "crawlspace",
                    "ducted_conditioned": "conditioned"
                }
                user_inputs["ductLocation"] = location_map.get(form_inputs["duct_config"], "attic")
            logger.info(f"🌀 DUCT SYSTEM (legacy): {form_inputs['duct_config']}")
        
        # 🔥 HEATING SYSTEM: Equipment sizing intelligence
        if "heating_fuel" in form_inputs:
            user_inputs["heating_fuel"] = form_inputs["heating_fuel"]
            # Also pass in camelCase for consistency with frontend
            user_inputs["heatingFuel"] = form_inputs["heating_fuel"]
            logger.info(f"🔥 HEATING: {form_inputs['heating_fuel']} affects equipment recommendations")
        
        # 🪟 BUILDING PERFORMANCE: Thermal envelope optimization
        if "window_performance" in form_inputs:
            user_inputs["window_performance"] = form_inputs["window_performance"]
            user_inputs["windowPerformance"] = form_inputs["window_performance"]
            
        if "building_orientation" in form_inputs:
            user_inputs["building_orientation"] = form_inputs["building_orientation"]
            user_inputs["buildingOrientation"] = form_inputs["building_orientation"]
        
        # 🏗️ Pass through all other fields in both snake_case and camelCase
        if "number_of_stories" in form_inputs:
            user_inputs["numberOfStories"] = form_inputs["number_of_stories"]
            
        if "square_footage" in form_inputs:
            user_inputs["squareFootage"] = form_inputs["square_footage"]
        
        # Update job with user inputs
        job_storage.update_job(job_id, {"user_inputs": user_inputs})
        
        # Log active pipeline integrations
        active_inputs = [k for k in user_inputs.keys() if k in ['conditioned_sqft', 'total_sqft', 'floor_count', 'foundation_type', 'duct_config', 'heating_fuel']]
        logger.info(f"🎯 PIPELINE INTEGRATED: {active_inputs}")
        logger.info(f"📊 TOTAL USER INPUTS: {len(user_inputs)} fields collected for maximum accuracy")
        
        if should_process_immediately:
            # Start processing in background with enhanced user inputs
            asyncio.create_task(process_blueprint_async(
                job_id, temp_file_path, zip_code, api_key, email, session, is_first_report, user_inputs, project_label
            ))
            
            logger.info(f"Started job {job_id} for file {file.filename}, zip {zip_code}")
            
            return UploadResponse(
                job_id=job_id,
                status="processing",
                message="Blueprint upload successful. Processing started."
            )
        else:
            # Save job as pending upgrade
            logger.info(f"Saved job {job_id} for file {file.filename} - pending upgrade")
            
            # Clean up temp file since we're not processing immediately
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
            return UploadResponse(
                job_id=job_id,
                status="pending_upgrade",
                message="Blueprint uploaded successfully. Upgrade to Pro to process your report."
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
    is_first_report: bool,
    user_inputs: dict = None,
    project_label: str = None
):
    """
    Process blueprint asynchronously using pipeline_v3
    """
    try:
        # Update progress
        job_storage.update_job(job_id, {"status": "processing", "progress": 10})
        
        logger.info(f"Job {job_id}: Starting pipeline_v3 processing")
        
        # 🎯 ENHANCED PIPELINE: Feed user inputs for maximum accuracy
        logger.info(f"🚀 PIPELINE V3: Starting with user inputs: {list(user_inputs.keys()) if user_inputs else 'None'}")
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            run_pipeline_v3,
            pdf_path, 
            zip_code, 
            user_inputs,  # 🎯 Enhanced user inputs for maximum accuracy
            api_key
        )
        
        # Pipeline_v3 returns a dictionary - check if it has heating load data
        if result and "heating_load_btu_hr" in result:
            # Generate high-value professional report
            report_generator = ValueReportGenerator()
            
            # Determine user subscription status
            user = user_service.get_or_create_user(email, session)
            subscription_status = "paid" if user_service.has_active_subscription(email, session) else "free"
            
            # Generate professional report
            class ResultObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            professional_report = report_generator.generate_complete_report(
                pipeline_result=ResultObj(result),
                zip_code=zip_code,
                user_subscription_status=subscription_status,
                report_context="user"
            )
            
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
                "processing_time_seconds": result.get("processing_time", 0),
                "professional_report": professional_report  # 🎯 HIGH-VALUE REPORT
            }
            
            # Add completion timestamp
            from datetime import datetime
            completion_time = datetime.utcnow().isoformat()
            
            job_storage.update_job(job_id, {
                "status": "completed",
                "progress": 100,
                "result": result_data,
                "completed_at": completion_time
            })
            
            # CRITICAL: Mark free report as used on successful completion
            if is_first_report:
                success = user_service.mark_free_report_used(email, session)
                if success:
                    logger.info(f"🔒 PAYWALL: Marked free report as used for {email}")
                else:
                    logger.error(f"🔒 PAYWALL ERROR: Failed to mark free report used for {email}")
            
            # 📊 DATA COLLECTION: Save comprehensive job data to S3
            try:
                job_data = job_storage.get_job(job_id)
                if job_data:
                    await storage_service.save_complete_job_data(job_id, job_data)
                logger.info(f"📊 DATA: Saved complete dataset for job {job_id}")
            except Exception as e:
                logger.error(f"📊 DATA ERROR: Failed to save complete data for {job_id}: {e}")
                # Don't fail the job if data collection fails
            
            logger.info(f"Job {job_id}: Completed successfully - {result['heating_load_btu_hr']:,.0f} BTU/hr heating")
            
        else:
            from datetime import datetime
            job_storage.update_job(job_id, {
                "status": "failed",
                "error": f"Pipeline processing failed: No valid result returned",
                "completed_at": datetime.utcnow().isoformat()
            })
            
            # 📊 DATA COLLECTION: Save failure data for analysis
            try:
                job_data = job_storage.get_job(job_id)
                if job_data:
                    await storage_service.save_complete_job_data(job_id, job_data)
                logger.info(f"📊 DATA: Saved failure data for job {job_id}")
            except Exception as data_error:
                logger.error(f"📊 DATA ERROR: Failed to save failure data for {job_id}: {data_error}")
            
            logger.error(f"Job {job_id}: Pipeline failed - no valid result")
            
    except Exception as e:
        from datetime import datetime
        
        job_storage.update_job(job_id, {
            "status": "failed", 
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })
        
        # 📊 DATA COLLECTION: Save error data for analysis
        try:
            job_data = job_storage.get_job(job_id)
            if job_data:
                await storage_service.save_complete_job_data(job_id, job_data)
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
    # DEBUG: Log job lookup attempts
    logger.info(f"🔍 JOB LOOKUP: Searching for job {job_id}")
    logger.info(f"🔍 TOTAL JOBS: {job_storage.get_job_count()} total jobs")
    logger.info(f"🔍 RECENT JOBS: {job_storage.get_recent_jobs()}")
    
    job = job_storage.get_job(job_id)
    if not job:
        logger.error(f"❌ JOB NOT FOUND: {job_id} not in storage")
        raise HTTPException(status_code=404, detail="Job not found")
    
    logger.info(f"✅ JOB FOUND: {job_id} with status {job['status']}")
    
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
    job = job_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed. Status: {job['status']}")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "filename": job["filename"],
        "zip_code": job["zip_code"],
        "result": job["result"]
    }

@router.get("/shared-report/{report_id}")
async def get_shared_report(report_id: str):
    """
    🚀 VIRAL SHARING: Public shared report for viral growth
    
    This endpoint enables contractors to share reports with clients/colleagues,
    driving organic traffic and new user acquisition.
    """
    # For MVP, we'll return a sample shared report
    # In production, you'd store report data and retrieve by report_id
    
    report_generator = ValueReportGenerator()
    
    # Mock shared report data (in production, retrieve from database)
    class SharedResultData:
        def __init__(self):
            self.heating_load_btu_hr = 61393
            self.cooling_load_btu_hr = 23314
            self.heating_tons = 5.1
            self.cooling_tons = 1.9
            self.heating_per_sqft = 33.1
            self.cooling_per_sqft = 12.6
            self.total_conditioned_area_sqft = 1853
            self.zones_created = 2
            self.spaces_detected = 8
            self.confidence_score = 0.92
            self.bonus_over_garage = True
            self.garage_detected = True
    
    shared_report = report_generator.generate_complete_report(
        pipeline_result=SharedResultData(),
        zip_code="99006",
        user_subscription_status="free",  # Always treat shared as free version
        report_context="shared"  # 🎯 VIRAL CONTEXT
    )
    
    return {
        "report_id": report_id,
        "status": "public",
        "report": shared_report,
        "viral_message": "Professional HVAC load calculations made simple"
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