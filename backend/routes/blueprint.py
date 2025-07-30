from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import stripe
import logging
import mimetypes
import os
import hashlib
import traceback
import sys
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from services.job_service import job_service
from services.user_service import user_service
from services.database_rate_limiter import database_rate_limiter as rate_limiter
from core.email import email_service
from models.schemas import JobResponse, PaymentRequiredResponse, UploadResponse
from models.enums import DuctConfig, HeatingFuel
from core.stripe_config import get_stripe_client, STRIPE_PRICE_ID
from app.config import DEBUG, DEV_VERIFIED_EMAILS

logger = logging.getLogger(__name__)

# New comprehensive Celery task for HVAC load calculations
from tasks.calculate_hvac_loads import calculate_hvac_loads
from services.s3_storage import storage_service
import aiofiles
import os

# Use Celery for production job processing
USE_CELERY = True

# Debug mode for detailed error responses
DEBUG_EXCEPTIONS = True  # Set to False in production

# AI-first configuration
AI_PARSING_ENABLED = os.getenv("AI_PARSING_ENABLED", "true").lower() != "false"
LEGACY_ELEMENT_LIMIT = int(os.getenv("LEGACY_ELEMENT_LIMIT", "20000"))
FILE_SIZE_WARNING_MB = int(os.getenv("FILE_SIZE_WARNING_MB", "20"))

router = APIRouter()

def validate_email_format(email: str) -> bool:
    """Basic email format validation to prevent obvious spam"""
    # Basic regex pattern for email validation
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    if not email_pattern.match(email):
        return False
    
    # Block obvious spam patterns
    spam_patterns = [
        r'^test@test\.',
        r'^asdf@asdf\.',
        r'^aaa+@',
        r'^123+@',
        r'^xxx+@',
        r'^fuck',
        r'^shit',
        r'@mailinator\.',
        r'@throwaway\.',
    ]
    
    email_lower = email.lower()
    for pattern in spam_patterns:
        if re.search(pattern, email_lower):
            return False
    
    return True

def should_use_ai_parsing() -> bool:
    """Check if AI parsing should be used (default: True)"""
    return AI_PARSING_ENABLED

def get_s3_file_info(project_id: str) -> dict:
    """Get file information from S3 for debugging"""
    info = {
        "project_id": project_id,
        "exists": storage_service.file_exists(project_id)
    }
    
    if info["exists"]:
        try:
            # Get file metadata from S3
            content = storage_service.get_file_content(project_id)
            info["size"] = len(content)
            info["first_16_bytes"] = content[:16].hex() if len(content) >= 16 else content.hex()
            # Hash first 64KB
            chunk = content[:65536]
            info["sha1_first_64k"] = hashlib.sha1(chunk).hexdigest()
        except Exception as e:
            info["read_error"] = f"{type(e).__name__}: {str(e)}"
    
    return info

def create_debug_error_response(e: Exception, context: str, project_id: str = None, file_path: str = None) -> dict:
    """Create detailed error response for debugging"""
    error_info = {
        "error": "Failed to validate PDF file. Please ensure it's a valid PDF document.",
        "type": type(e).__name__,
        "message": str(e),
        "context": context
    }
    
    if DEBUG_EXCEPTIONS:
        # Get the line number where the exception occurred
        tb = traceback.extract_tb(sys.exc_info()[2])
        if tb:
            last_frame = tb[-1]
            error_info["line_number"] = last_frame.lineno
            error_info["function"] = last_frame.name
            error_info["filename"] = last_frame.filename
        
        error_info["traceback"] = traceback.format_exc()
        
        if project_id:
            error_info["project_id"] = project_id
        
        if project_id:
            error_info["s3_file_info"] = get_s3_file_info(project_id)
    
    return error_info

# All parameters now collected upfront in upload endpoint

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
    zip_code: str = Form(...),
    file: UploadFile = File(...),
    duct_config: str = Form("ducted_attic"),
    heating_fuel: str = Form("gas"),
    request: Request = None,
    session: AsyncSession = Depends(get_async_session)
):
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    print(f">>> UPLOAD ENDPOINT HIT: email={email}, file={file.filename}, size={file.size}")
    logger.error(f">>> UPLOAD ENDPOINT HIT: email={email}, file={file.filename}, size={file.size}")
    logger.info(f"🔍 UPLOAD STARTED: email={email}, file={file.filename}, size={file.size}, project={project_label}")
    
    try:
        # Validate email format first
        logger.info("🔍 Step 1: Validating email format")
        if not validate_email_format(email):
            raise HTTPException(
                status_code=400,
                detail="Invalid email format. Please provide a valid email address."
            )
        
        # Validate assumptions
        logger.info("🔍 Step 2: Starting assumption validation")
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
        logger.info("🔍 Step 2 PASSED: Assumption validation successful")
        
        # Validate file upload
        logger.info("🔍 Step 3: Starting file validation")
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
        
        # Warn for large files
        if file.size > FILE_SIZE_WARNING_MB * 1024 * 1024:
            logger.warning(f"Large file uploaded: {file.size / 1024 / 1024:.1f}MB. Processing may take longer.")
            # Add to audit/response later
            large_file_warning = f"Large blueprint detected ({file.size / 1024 / 1024:.1f}MB). AI processing may take 2-3 minutes. Please do not refresh or leave the page."
        else:
            large_file_warning = None
        
        # Validate project label
        if not project_label.strip():
            raise HTTPException(status_code=400, detail="Project label is required")
        
        if len(project_label) > 255:
            raise HTTPException(status_code=400, detail="Project label must be less than 255 characters")
        
        # Validate zip code
        if not zip_code or not zip_code.strip():
            raise HTTPException(status_code=400, detail="Zip code is required")
        
        zip_code = zip_code.strip()
        if not zip_code.isdigit() or len(zip_code) != 5:
            raise HTTPException(status_code=400, detail="Zip code must be exactly 5 digits")
        
        logger.info("🔍 Step 3 PASSED: File and input validation successful")
        
        # Check rate limits (5 concurrent jobs per user)
        logger.info("🔍 Step 4: Starting rate limit check")
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
        logger.info("🔍 Step 4 PASSED: Rate limit check successful")
        
        # Ensure user exists (create if needed)
        logger.info("🔍 Step 5: Ensuring user exists")
        await user_service.get_or_create_user(email, session)
        
        # Check free report usage and subscription status
        logger.info("🔍 Step 6: Starting subscription and free report check")
        can_use_free = await user_service.can_use_free_report(email, session)
        has_subscription = await user_service.has_active_subscription(email, session)
        
        # Only require email verification if they've used their free report and don't have a subscription
        if not can_use_free and not has_subscription:
            logger.info("🔍 Step 6a: User has used free report, checking email verification")
            try:
                await user_service.require_verified(email, session)
            except HTTPException as e:
                if e.status_code == 403:
                    # Send verification email if not verified
                    token = await user_service.create_email_token(email, session)
                    await email_service.send_verification_email(email, token)
                raise
        else:
            logger.info("🔍 Step 5 SKIPPED: Email verification not required for first free report")
    
        # Bypass subscription check in debug mode for whitelisted emails
        if DEBUG or email in DEV_VERIFIED_EMAILS:
            can_use_free = True
        
        if not can_use_free and not has_subscription:
            # Generate Stripe checkout session
            try:
                stripe_client = get_stripe_client()
                frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
                checkout_session = stripe_client.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price': STRIPE_PRICE_ID,
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url=f'{frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
                    cancel_url=f'{frontend_url}/payment/cancel', 
                    customer_email=email,
                    metadata={'user_email': email}
                )
                
                # Return structured payment required response
                payment_response = {
                    "error": "free_report_used",
                    "message": "You've used your free analysis. Upgrade to Pro for unlimited reports.",
                    "checkout_url": checkout_session.url,
                    "upgrade_benefits": [
                        "Unlimited blueprint analyses",
                        "Priority processing",
                        "Bulk upload support",
                        "API access",
                        "Premium support"
                    ],
                    "cta_text": "Unlock Unlimited Reports",
                    "cta_button_text": "Upgrade to Pro"
                }
                
                raise HTTPException(
                    status_code=402,
                    detail=payment_response,
                    headers={"X-Checkout-URL": checkout_session.url}
                )
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Payment system error. Please try again."
                )
        logger.info("🔍 Step 6 PASSED: Subscription check successful")
        
        # Create project in database with all parameters
        logger.info("🔍 Step 7: About to create project in database")
        try:
            # Extract analytics data from request
            analytics_data = {}
            if request:
                # Get client IP (handle proxy headers)
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    analytics_data["client_ip"] = forwarded_for.split(",")[0].strip()
                else:
                    analytics_data["client_ip"] = request.client.host if request.client else None
                
                # Get user agent and referrer
                analytics_data["user_agent"] = request.headers.get("User-Agent", "")[:512]
                analytics_data["referrer"] = request.headers.get("Referer", "")[:512]
            
            project_id = await job_service.create_project_with_assumptions(
                user_email=email,
                project_label=project_label.strip(),
                filename=file.filename,
                file_size=file.size,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                analytics_data=analytics_data,
                session=session
            )
            logger.info(f"✅ Step 7 PASSED: Project {project_id} created successfully for user {email}")
            logger.info("job_created", extra={"jobId": project_id, "email": email})
        except HTTPException as e:
            # Database creation failed - return the error to user
            logger.error(f"❌ Step 7 FAILED: Database creation failed for user {email}: {e.detail}")
            raise e
        except Exception as e:
            # Unexpected error during project creation
            logger.error(f"❌ Step 7 FAILED: Unexpected error creating project for user {email}: {str(e)}")
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
        
        logger.info("🔍 Step 8: Streaming file to disk")
        try:
            # Read file content
            file_content = await file.read()
            
            # CRITICAL: Save file to S3 FIRST, before any validation
            s3_key = await storage_service.save_upload(project_id, file_content)
            logger.info(f"🔍 Saved PDF to S3: {s3_key}, size={len(file_content)} bytes")
            
            # Validate file exists in S3
            if not storage_service.file_exists(project_id):
                # Mark job as failed instead of cleaning up immediately
                await job_service.set_project_failed(project_id, "File upload failed", session)
                raise HTTPException(status_code=400, detail="File upload failed")
            
            # Enhanced PDF validation using saved file (NOT memory bytes)
            if file_ext == '.pdf':
                # Basic format check on bytes
                if file_content[:4] != b'%PDF':
                    await job_service.set_project_failed(project_id, "Invalid PDF file", session)
                    raise HTTPException(status_code=400, detail="Invalid PDF file")
                
                # Download PDF from S3 to temp file for validation
                temp_pdf_path = storage_service.download_to_temp_file(project_id)
                
                # Use PDF thread manager for safe validation
                from services.pdf_thread_manager import pdf_thread_manager
                
                def validate_pdf_from_disk(pdf_path: str):
                    """Validate PDF within same thread context"""
                    import fitz
                    error_msg = None
                    page_count = 0
                    
                    try:
                        # Open from disk
                        doc = fitz.open(pdf_path)
                        
                        try:
                            if doc.is_encrypted:
                                error_msg = "PDF is password protected. Please upload an unprotected version."
                                return False, error_msg, 0
                            
                            page_count = len(doc)
                            if page_count == 0:
                                error_msg = "PDF contains no pages"
                                return False, error_msg, 0
                            
                            if page_count > 100:
                                error_msg = f"PDF has {page_count} pages. Please limit to 100 pages or fewer for processing."
                                return False, error_msg, page_count
                            
                            # Quick complexity check on first few pages (only for legacy parser)
                            total_elements = 0
                            
                            if should_use_ai_parsing():
                                logger.info(f"AI parsing enabled - skipping element count validation for {page_count} pages")
                            else:
                                for page_num in range(min(3, page_count)):
                                    try:
                                        page = doc[page_num]
                                        drawings = page.get_drawings()
                                        total_elements += len(drawings)
                                        
                                        if len(drawings) > LEGACY_ELEMENT_LIMIT:
                                            error_msg = f"Blueprint is too complex for traditional parsing (page {page_num + 1} has {len(drawings)} elements). AI parsing is recommended for complex blueprints."
                                            return False, error_msg, page_count
                                    except Exception:
                                        # If we can't check complexity, continue
                                        break
                                
                                logger.info(f"Legacy parser validation: {page_count} pages, {total_elements} elements in first 3 pages")
                            
                            logger.info(f"PDF validation passed: {page_count} pages{f', {total_elements} elements' if not should_use_ai_parsing() else ''}")
                            return True, None, page_count
                            
                        finally:
                            # ALWAYS close the document
                            doc.close()
                            
                    except Exception as e:
                        # Store error as string BEFORE any cleanup
                        error_msg = f"Cannot process this PDF file. It may be corrupted or in an unsupported format: {str(e)[:100]}"
                        return False, error_msg, 0
                
                try:
                    # Validate using thread-safe operation
                    is_valid, error_message, pages = pdf_thread_manager.process_pdf_with_retry(
                        pdf_path=temp_pdf_path,
                        processor_func=validate_pdf_from_disk,
                        operation_name="pdf_validation",
                        max_retries=2
                    )
                    
                    if not is_valid:
                        await job_service.set_project_failed(project_id, error_message, session)
                        raise HTTPException(status_code=400, detail=error_message)
                        
                except FileNotFoundError as e:
                    error_msg = f"PDF file not found during validation: {str(e)}"
                    logger.error(f"FileNotFoundError during PDF validation: {error_msg}")
                    await job_service.set_project_failed(project_id, error_msg, session)
                    error_response = create_debug_error_response(e, "PDF validation - file not found", project_id, temp_pdf_path)
                    raise HTTPException(status_code=400, detail=error_response)
                except PermissionError as e:
                    error_msg = f"Permission denied accessing PDF: {str(e)}"
                    logger.error(f"PermissionError during PDF validation: {error_msg}")
                    await job_service.set_project_failed(project_id, error_msg, session)
                    error_response = create_debug_error_response(e, "PDF validation - permission denied", project_id, temp_pdf_path)
                    raise HTTPException(status_code=400, detail=error_response)
                except Exception as e:
                    # Log the actual exception before masking it
                    logger.error(f"❌ PDF validation exception: {type(e).__name__}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    logger.error(f"Temp file path: {temp_pdf_path}")
                    
                    await job_service.set_project_failed(project_id, f"PDF validation failed: {type(e).__name__}: {str(e)}", session)
                    error_response = create_debug_error_response(e, "PDF validation", project_id, temp_pdf_path)
                    raise HTTPException(status_code=400, detail=error_response)
            
            # Clean up temp file after validation
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_pdf_path}: {e}")
            
            logger.info(f"✅ PDF validation completed successfully for project {project_id}")
            
            logger.error("🔍 Step 9: Starting background job processor")
            logger.error(f"Adding background task for job {project_id}")
            print(f">>> BLUEPRINT UPLOAD: About to start background job for {project_id}")
            print(f">>> USE_CELERY = {USE_CELERY}")
            
            if USE_CELERY:
                try:
                    # Log file state before Celery task
                    # Log S3 file info before Celery task
                    pre_celery_info = get_s3_file_info(project_id)
                    logger.info(f"[PRE_CELERY] S3 file info for {project_id}: {pre_celery_info}")
                    logger.info(f"About to start Celery task. File info: {pre_celery_info}")
                    
                    # Double-check file exists in S3 before dispatching Celery task
                    if not storage_service.file_exists(project_id):
                        error_msg = f"File not found in S3 before Celery dispatch: {project_id}"
                        logger.error(error_msg)
                        await job_service.set_project_failed(project_id, error_msg, session)
                        raise HTTPException(status_code=500, detail=error_msg)
                    
                    # Start comprehensive HVAC load calculation task
                    # CRITICAL: Pass only project_id - worker will reconstruct path from RENDER_DISK_PATH
                    calculate_hvac_loads.delay(
                        project_id=project_id, 
                        filename=file.filename, 
                        email=email, 
                        zip_code=zip_code,
                        duct_config=duct_config,
                        heating_fuel=heating_fuel
                    )
                    
                    # Log file state after Celery task dispatch
                    # Log S3 file info after Celery task
                    post_celery_info = get_s3_file_info(project_id)
                    logger.info(f"[POST_CELERY] S3 file info for {project_id}: {post_celery_info}")
                    logger.info(f"Celery task dispatched. File info: {post_celery_info}")
                    
                    # One final check to ensure file still exists in S3
                    if not storage_service.file_exists(project_id):
                        logger.warning(f"File not found in S3 after Celery dispatch (non-critical): {project_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to start Celery task: {type(e).__name__}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    error_response = create_debug_error_response(e, "Celery task dispatch", project_id)
                    await job_service.set_project_failed(project_id, f"Failed to start background job: {str(e)}", session)
                    raise HTTPException(status_code=500, detail=error_response)
            else:
                print(f">>> ERROR: USE_CELERY is False but Celery is expected")
                error_response = {"error": "Job processing not configured correctly", "USE_CELERY": USE_CELERY}
                raise HTTPException(status_code=500, detail=error_response)
                    
            logger.error(f"Celery task started for job {project_id}")
            logger.error("🔍 Step 9 PASSED: Background job processor started")
                
        except HTTPException:
            # Re-raise HTTP exceptions
            await rate_limiter.decrement_active_jobs(email, project_id)
            raise
        except Exception as e:
            logger.error(f"❌ Step 8/9 FAILED: File processing error: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if project_id:
                logger.error(f"[UPLOAD_EXCEPTION] Error for project {project_id}")
            
            await job_service.set_project_failed(project_id, str(e), session)
            await rate_limiter.decrement_active_jobs(email, project_id)
            
            error_response = create_debug_error_response(e, "File processing", project_id)
            raise HTTPException(status_code=500, detail=error_response)
        
        logger.info(f"✅ UPLOAD SUCCESS: Returning jobId {project_id} for {email}")
        
        # Add parsing path info to response
        response = UploadResponse(
            job_id=project_id,
            status="pending",
            project_label=project_label.strip()
        )
        
        # Add warnings if needed
        if large_file_warning:
            response.message = large_file_warning
        
        # Log parsing path for metrics
        logger.info(f"[PARSING PATH] Project {project_id}: Will use {'AI (GPT-4V)' if should_use_ai_parsing() else 'Legacy (Python)'} parser")
        
        return response
        
    except HTTPException as e:
        logger.error(f"❌ UPLOAD HTTP ERROR: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.exception(f"❌ UPLOAD FATAL ERROR: {type(e).__name__}: {str(e)}")
        error_response = create_debug_error_response(e, "Upload endpoint", project_id if 'project_id' in locals() else None)
        raise HTTPException(status_code=500, detail=error_response)

# JSON Download Endpoints

@router.get("/{project_id}/json")
async def download_blueprint_json(
    project_id: str,
    include_raw_data: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Download the parsed blueprint JSON for a project
    
    Args:
        project_id: The project ID
        include_raw_data: Whether to include raw geometry/text data
        session: Database session
        
    Returns:
        JSON response with the parsed blueprint data
    """
    try:
        # Get project from database
        project = await job_service.get_project(project_id, session)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if JSON exists
        if not project.parsed_schema_json:
            raise HTTPException(
                status_code=404, 
                detail="Blueprint JSON not available - project may not be completed or parsing failed"
            )
        
        blueprint_json = project.parsed_schema_json.copy()
        
        # Optionally remove raw data to reduce response size
        if not include_raw_data:
            blueprint_json.pop('raw_geometry', None)
            blueprint_json.pop('raw_text', None)
        
        # Add download metadata
        response_data = {
            "project_id": project_id,
            "project_label": project.project_label,
            "filename": project.filename,
            "status": project.status,
            "download_timestamp": datetime.now().isoformat(),
            "blueprint_data": blueprint_json
        }
        
        logger.info(f"Blueprint JSON downloaded for project {project_id}")
        
        return JSONResponse(
            content=response_data,
            headers={
                "Content-Disposition": f"attachment; filename={project.project_label}_blueprint.json",
                "Content-Type": "application/json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading blueprint JSON for {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download blueprint JSON")


@router.get("/{project_id}/json/raw")
async def download_raw_blueprint_data(
    project_id: str,
    data_type: str = "all",  # "all", "geometry", "text", "metadata"
    session: AsyncSession = Depends(get_async_session)
):
    """
    Download raw blueprint parsing data for debugging/analysis
    
    Args:
        project_id: The project ID  
        data_type: Type of raw data to return
        session: Database session
        
    Returns:
        JSON response with raw parsing data
    """
    try:
        # Get project from database
        project = await job_service.get_project(project_id, session)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if JSON exists
        if not project.parsed_schema_json:
            raise HTTPException(
                status_code=404, 
                detail="Blueprint JSON not available"
            )
        
        blueprint_json = project.parsed_schema_json
        response_data = {
            "project_id": project_id,
            "project_label": project.project_label,
            "filename": project.filename,
            "download_timestamp": datetime.now().isoformat(),
            "data_type": data_type
        }
        
        # Extract requested data type
        if data_type == "all":
            response_data["raw_data"] = {
                "raw_geometry": blueprint_json.get('raw_geometry', {}),
                "raw_text": blueprint_json.get('raw_text', {}),
                "parsing_metadata": blueprint_json.get('parsing_metadata', {}),
                "geometric_elements": blueprint_json.get('geometric_elements', []),
                "dimensions": blueprint_json.get('dimensions', []),
                "labels": blueprint_json.get('labels', [])
            }
        elif data_type == "geometry":
            response_data["raw_data"] = {
                "raw_geometry": blueprint_json.get('raw_geometry', {}),
                "geometric_elements": blueprint_json.get('geometric_elements', [])
            }
        elif data_type == "text":
            response_data["raw_data"] = {
                "raw_text": blueprint_json.get('raw_text', {}),
                "dimensions": blueprint_json.get('dimensions', []),
                "labels": blueprint_json.get('labels', [])
            }
        elif data_type == "metadata":
            response_data["raw_data"] = {
                "parsing_metadata": blueprint_json.get('parsing_metadata', {})
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid data_type. Must be 'all', 'geometry', 'text', or 'metadata'")
        
        logger.info(f"Raw blueprint data ({data_type}) downloaded for project {project_id}")
        
        return JSONResponse(
            content=response_data,
            headers={
                "Content-Disposition": f"attachment; filename={project.project_label}_raw_{data_type}.json",
                "Content-Type": "application/json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading raw blueprint data for {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download raw blueprint data")


@router.get("/{project_id}/json/summary")  
async def get_blueprint_json_summary(
    project_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a summary of the parsed blueprint JSON without downloading the full data
    
    Args:
        project_id: The project ID
        session: Database session
        
    Returns:
        JSON summary of the blueprint parsing results
    """
    try:
        # Get project from database
        project = await job_service.get_project(project_id, session)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if JSON exists
        if not project.parsed_schema_json:
            raise HTTPException(
                status_code=404, 
                detail="Blueprint JSON not available"
            )
        
        blueprint_json = project.parsed_schema_json
        parsing_metadata = blueprint_json.get('parsing_metadata', {})
        
        # Create summary
        summary = {
            "project_id": project_id,
            "project_label": project.project_label,
            "filename": project.filename,
            "status": project.status,
            "summary_timestamp": datetime.now().isoformat(),
            
            # Basic parsing results
            "total_rooms": len(blueprint_json.get('rooms', [])),
            "total_area_sqft": blueprint_json.get('sqft_total', 0),
            "stories": blueprint_json.get('stories', 1),
            "zip_code": blueprint_json.get('zip_code', ''),
            
            # Parsing metadata summary
            "parsing_results": {
                "selected_page": parsing_metadata.get('selected_page', 1),
                "total_pages_analyzed": parsing_metadata.get('pdf_page_count', 1),
                "processing_time_seconds": parsing_metadata.get('processing_time_seconds', 0),
                "overall_confidence": parsing_metadata.get('overall_confidence', 0),
                "geometry_status": parsing_metadata.get('geometry_status', 'unknown'),
                "text_status": parsing_metadata.get('text_status', 'unknown'),
                "ai_status": parsing_metadata.get('ai_status', 'unknown')
            },
            
            # Data availability
            "data_available": {
                "rooms": len(blueprint_json.get('rooms', [])) > 0,
                "dimensions": len(blueprint_json.get('dimensions', [])) > 0,
                "labels": len(blueprint_json.get('labels', [])) > 0,
                "geometric_elements": len(blueprint_json.get('geometric_elements', [])) > 0,
                "raw_geometry": bool(blueprint_json.get('raw_geometry')),
                "raw_text": bool(blueprint_json.get('raw_text'))
            },
            
            # Room summary
            "room_summary": [
                {
                    "name": room.get('name', 'Unknown'),
                    "area": room.get('area', 0),
                    "room_type": room.get('room_type', 'unknown'),
                    "confidence": room.get('confidence', 0),
                    "floor": room.get('floor', 1)
                }
                for room in blueprint_json.get('rooms', [])
            ]
        }
        
        # Add error summary if any
        errors = parsing_metadata.get('errors_encountered', [])
        if errors:
            summary["parsing_errors"] = {
                "total_errors": len(errors),
                "error_summary": [
                    {
                        "stage": error.get('stage', 'unknown'),
                        "error_type": error.get('error_type', 'unknown'),
                        "error": error.get('error', '')[:100]  # Truncate long errors
                    }
                    for error in errors
                ]
            }
        
        logger.info(f"Blueprint JSON summary generated for project {project_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating blueprint JSON summary for {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate blueprint summary")


# Legacy endpoint preserved for backward compatibility