from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import stripe
import logging
import mimetypes
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from services.user_service import user_service
from services.rate_limiter import rate_limiter
from core.email import email_service
from models.schemas import JobResponse, PaymentRequiredResponse, UploadResponse
from models.enums import DuctConfig, HeatingFuel
from core.stripe_config import get_stripe_client, STRIPE_PRICE_ID
from app.config import DEBUG, DEV_VERIFIED_EMAILS

logger = logging.getLogger(__name__)

# Force simple processor for development (no Redis required)
# TODO: Set USE_CELERY=True once Redis/Celery are running locally for full stage-based processing
# NOTE: Front-end progress bar shows 5 stages (25% -> 100%) which matches Celery pipeline,
#       but simple processor jumps directly to completion. Consider updating UI copy for dev mode.
USE_CELERY = False
from services.simple_job_processor import process_job_async
import aiofiles
import os

router = APIRouter()

class AssumptionRequest(BaseModel):
    duct_config: DuctConfig
    heating_fuel: HeatingFuel

@router.options("/upload")
async def upload_options():
    return JSONResponse(
        content={"message": "OK"}, 
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/test-upload")
async def test_upload(
    email: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        print(f"▶️ test-upload hit: filename={file.filename}, size={file.size}, email={email}")
        
        # Test file reading
        content = await file.read()
        print(f"   ▶️ read bytes: {len(content)}")
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "size": file.size,
            "email": email,
            "bytes_read": len(content)
        })
    except Exception as e:
        print("❌ test-upload error:", repr(e))
        raise

@router.post("/upload", response_model=UploadResponse)
async def upload_blueprint(
    email: str = Form(...),
    project_label: str = Form(...),
    file: UploadFile = File(...),
    duct_config: str = Form("ducted_attic"),
    heating_fuel: str = Form("gas"),
    session: AsyncSession = Depends(get_async_session)
):
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    logger.info(f"🔍 UPLOAD STARTED: email={email}, file={file.filename}, size={file.size}, project={project_label}")
    
    try:
        # Validate assumptions
        logger.info("🔍 Step 1: Starting assumption validation")
        valid_duct_configs = {"ducted_attic", "ducted_crawl", "ductless"}
        valid_heating_fuels = {"gas", "heat_pump", "electric"}
        
        if duct_config not in valid_duct_configs:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid duct_config. Must be one of: {valid_duct_configs}"
            )
        
        if heating_fuel not in valid_heating_fuels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid heating_fuel. Must be one of: {valid_heating_fuels}"
            )
        logger.info("🔍 Step 1 PASSED: Assumption validation successful")
        
        # Validate file upload
        logger.info("🔍 Step 2: Starting file validation")
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
    
        # Validate file type using MIME type and extension
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
        allowed_mime_types = {
            'application/pdf',
            'image/png', 
            'image/jpeg',
            'image/jpg'
        }
        
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail="File must be PDF or image (PNG, JPG, JPEG)"
            )
        
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 50MB"
            )
        
        # Validate project label
        if not project_label.strip():
            raise HTTPException(status_code=400, detail="Project label is required")
        
        if len(project_label) > 255:
            raise HTTPException(status_code=400, detail="Project label must be less than 255 characters")
        logger.info("🔍 Step 2 PASSED: File validation successful")
        
        # Check rate limits (5 concurrent jobs per user)
        logger.info("🔍 Step 3: Starting rate limit check")
        rate_check = await rate_limiter.check_rate_limit(
            key=email,
            limit=10,  # 10 requests per hour
            window_seconds=3600,
            burst_limit=5  # 5 concurrent jobs max
        )
        
        if not rate_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {rate_check['reason']}",
                headers={"Retry-After": str(int(rate_check['reset_time'] - datetime.now().timestamp()))}
            )
        logger.info("🔍 Step 3 PASSED: Rate limit check successful")
        
        # Check if email is verified (unified through user_service)
        logger.info("🔍 Step 4: Starting email verification check")
        try:
            await user_service.require_verified(email, session)
        except HTTPException as e:
            if e.status_code == 403:
                # Send verification email if not verified
                token = await user_service.create_email_token(email, session)
                await email_service.send_verification_email(email, token)
            raise
        logger.info("🔍 Step 4 PASSED: Email verification successful")
        
        # Check free report usage and subscription status
        logger.info("🔍 Step 5: Starting subscription check")
        can_use_free = await user_service.can_use_free_report(email, session)
        has_subscription = await user_service.has_active_subscription(email, session)
    
        # Bypass subscription check in debug mode for whitelisted emails
        if DEBUG or email in DEV_VERIFIED_EMAILS:
            can_use_free = True
        
        if not can_use_free and not has_subscription:
            # Generate Stripe checkout session
            try:
                stripe_client = get_stripe_client()
                checkout_session = stripe_client.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price': STRIPE_PRICE_ID,
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url='http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url='http://localhost:3000/payment/cancel', 
                    customer_email=email,
                    metadata={'user_email': email}
                )
                
                raise HTTPException(
                    status_code=402,
                    detail="Free report already used. Subscription required.",
                    headers={"X-Checkout-URL": checkout_session.url}
                )
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Payment system error. Please try again."
                )
        logger.info("🔍 Step 5 PASSED: Subscription check successful")
        
        # Create project in database with assumptions
        logger.info("🔍 Step 6: About to create project in database")
        try:
            project_id = await job_service.create_project_with_assumptions(
                user_email=email,
                project_label=project_label.strip(),
                filename=file.filename,
                file_size=file.size,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                session=session
            )
            logger.info(f"✅ Step 6 PASSED: Project {project_id} created successfully for user {email}")
        logger.info("job_created", extra={"jobId": project_id, "email": email})
        except HTTPException as e:
            # Database creation failed - return the error to user
            logger.error(f"❌ Step 6 FAILED: Database creation failed for user {email}: {e.detail}")
            raise e
        except Exception as e:
            # Unexpected error during project creation
            logger.error(f"❌ Step 6 FAILED: Unexpected error creating project for user {email}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create project: {str(e)}"
            )
        
        # Mark free report as used if this is their first
        if can_use_free:
            await user_service.mark_free_report_used(email, session)
        
        # Set status to processing immediately
        await job_service.set_project_processing(project_id, session)
        await job_service.update_project(project_id, {"progress_percent": 1}, session)
        
        # Track active job for rate limiting
        await rate_limiter.increment_active_jobs(email, project_id)
        
        logger.info("🔍 Step 7: Streaming file to disk")
        try:
            # Stream file to disk for memory efficiency
            temp_path = f"/tmp/{project_id}.pdf"
            
            async with aiofiles.open(temp_path, 'wb') as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                total_size = 0
                while chunk := await file.read(chunk_size):
                    await f.write(chunk)
                    total_size += len(chunk)
            
            logger.info(f"🔍 Saved PDF to {temp_path}, size={total_size} bytes")
            
            # Validate file exists and has content
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise HTTPException(status_code=400, detail="File is empty")
            
            # Quick PDF validation
            with open(temp_path, 'rb') as f:
                header = f.read(4)
                if file_ext == '.pdf' and header != b'%PDF':
                    os.unlink(temp_path)
                    raise HTTPException(status_code=400, detail="Invalid PDF file")
            
            logger.info("🔍 Step 8: Starting background job processor")
            logger.info(f"Starting background thread for job {project_id}")
            if USE_CELERY:
                # For Celery, we'd need to pass file path instead of content
                process_blueprint.delay(project_id, temp_path, file.filename, email, "90210")
            else:
                process_job_async(project_id, temp_path, file.filename, email, "90210")
            logger.info(f"Background thread started for job {project_id}")
            logger.info("🔍 Step 8 PASSED: Background job processor started")
                
        except HTTPException:
            # Re-raise HTTP exceptions
            await rate_limiter.decrement_active_jobs(email, project_id)
            raise
        except Exception as e:
            logger.error(f"❌ Step 7/8 FAILED: File processing error: {repr(e)}")
            await job_service.set_project_failed(project_id, str(e), session)
            await rate_limiter.decrement_active_jobs(email, project_id)
            raise HTTPException(status_code=500, detail="Failed to process upload")
        
        logger.info(f"✅ UPLOAD SUCCESS: Returning jobId {project_id} for {email}")
        return UploadResponse(
            job_id=project_id,
            status="pending",
            project_label=project_label.strip()
        )
        
    except HTTPException as e:
        logger.error(f"❌ UPLOAD HTTP ERROR: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"❌ UPLOAD FATAL ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/jobs/{job_id}/assumptions")
async def submit_assumptions(
    job_id: str,
    assumptions: AssumptionRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Submit Manual J assumptions to continue processing"""
    
    try:
        # Update project with assumptions and resume job
        updated = await job_service.update_project_assumptions(
            job_id, 
            assumptions.duct_config.value, 
            assumptions.heating_fuel.value, 
            session
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JSONResponse(
            content={
                "message": "Assumptions received, job resumed",
                "job_id": job_id,
                "duct_config": assumptions.duct_config.value,
                "heating_fuel": assumptions.heating_fuel.value
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating assumptions for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update assumptions")