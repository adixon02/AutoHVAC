"""
Simple in-memory job processor for development without Celery/Redis
"""
import time
import asyncio
from typing import Dict, Any
from services.job_service import job_service
from services.database_rate_limiter import database_rate_limiter as rate_limiter
from services.pdf_service import pdf_service
from services.manualj import calculate_manualj
from app.parser.schema import BlueprintSchema, Room
from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser
from app.parser.ai_cleanup import cleanup, AICleanupError
from services.envelope_extractor import extract_envelope_data, EnvelopeExtractorError
from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
import os
import tempfile
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Constants for AI analysis safeguards
MAX_PAGES = 50
MAX_TOKENS = 16000
OPENAI_TIMEOUT = 120  # seconds

class MissingAIKeyError(Exception):
    """Raised when OPENAI_API_KEY is missing or blank"""
    pass

class AIAnalysisTimeoutError(Exception):
    """Raised when AI analysis times out"""
    pass

class PDFTooLargeError(Exception):
    """Raised when PDF exceeds size limits"""
    pass

async def update_progress(project_id: str, percent: int, stage: str):
    """Update job progress in database with retry logic and isolated session"""
    for attempt in range(2):
        try:
            # Create isolated session for each progress update
            async with AsyncSessionLocal() as session:
                await job_service.update_project(
                    project_id, 
                    {"progress_percent": percent, "current_stage": stage},
                    session
                )
            logger.info(f"📊 Progress: {project_id} - {percent}% - {stage}")
            return
        except Exception as e:
            if attempt == 0:  # First attempt failed, retry once
                await asyncio.sleep(0.1)  # 100ms backoff
                continue
            else:
                logger.exception(f"Failed to update progress after 2 attempts: {e}", extra={"jobId": project_id})
                raise

async def run_ai_analysis(project_id: str, file_path: str, session: AsyncSession):
    """
    Run AI analysis on the PDF with comprehensive error handling and safeguards
    
    Args:
        project_id: Job identifier
        file_path: Path to the PDF file
        session: Database session
        
    Raises:
        MissingAIKeyError: If OpenAI API key is missing
        PDFTooLargeError: If PDF exceeds size limits
        AIAnalysisTimeoutError: If AI calls timeout
        AICleanupError: If AI processing fails
        EnvelopeExtractorError: If envelope extraction fails
    """
    logger.info("AI_ANALYSIS_START", extra={"jobId": project_id})
    
    try:
        # 1. Fast-fail on missing OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or not openai_key.strip():
            raise MissingAIKeyError("OPENAI_API_KEY environment variable is missing or blank")
        
        # 2. Check PDF size constraints
        await update_progress(project_id, 65, "ai_analysis")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Check file size and page count
        try:
            pdf_doc = fitz.open(file_path)
            num_pages = len(pdf_doc)
            pdf_doc.close()
            
            if num_pages > MAX_PAGES:
                raise PDFTooLargeError(
                    f"PDF has {num_pages} pages (max: {MAX_PAGES}). "
                    f"Please split large blueprints by floor or zone."
                )
                
            logger.info(f"PDF validation passed: {num_pages} pages", extra={"jobId": project_id})
            
        except fitz.fitz.FileDataError as e:
            raise AICleanupError(f"Invalid or corrupted PDF file: {e}")
        
        # 3. Extract geometry with timeout protection
        await update_progress(project_id, 70, "extracting_geometry")
        
        try:
            geometry_parser = GeometryParser()
            raw_geometry = await asyncio.wait_for(
                asyncio.to_thread(geometry_parser.parse, file_path),
                timeout=OPENAI_TIMEOUT
            )
            logger.info("Geometry extraction completed", extra={"jobId": project_id})
            
        except asyncio.TimeoutError:
            raise AIAnalysisTimeoutError(f"Geometry extraction timed out after {OPENAI_TIMEOUT}s")
        except Exception as e:
            raise AICleanupError(f"Geometry extraction failed: {e}")
        
        # 4. Extract text with timeout protection
        await update_progress(project_id, 75, "extracting_text")
        
        try:
            text_parser = TextParser()
            raw_text = await asyncio.wait_for(
                asyncio.to_thread(text_parser.parse, file_path),
                timeout=OPENAI_TIMEOUT
            )
            logger.info("Text extraction completed", extra={"jobId": project_id})
            
        except asyncio.TimeoutError:
            raise AIAnalysisTimeoutError(f"Text extraction timed out after {OPENAI_TIMEOUT}s")
        except Exception as e:
            raise AICleanupError(f"Text extraction failed: {e}")
        
        # 5. AI cleanup with timeout protection
        await update_progress(project_id, 80, "ai_processing")
        
        try:
            blueprint_schema = await asyncio.wait_for(
                cleanup(raw_geometry, raw_text),
                timeout=OPENAI_TIMEOUT
            )
            logger.info("AI cleanup completed", extra={"jobId": project_id})
            
        except asyncio.TimeoutError:
            raise AIAnalysisTimeoutError(f"AI cleanup timed out after {OPENAI_TIMEOUT}s")
        except AICleanupError:
            raise  # Re-raise AI-specific errors
        except Exception as e:
            raise AICleanupError(f"AI cleanup failed: {e}")
        
        # 6. Envelope extraction with timeout protection  
        await update_progress(project_id, 85, "envelope_analysis")
        
        try:
            # Extract text content for envelope analysis
            pdf_doc = fitz.open(file_path)
            full_text = ""
            for page in pdf_doc:
                full_text += page.get_text()
            pdf_doc.close()
            
            # Check token count estimate (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(full_text) // 4
            if estimated_tokens > MAX_TOKENS:
                logger.warning(
                    f"Text content may exceed token limit: ~{estimated_tokens} tokens",
                    extra={"jobId": project_id}
                )
                # Truncate text to stay under limit
                full_text = full_text[:MAX_TOKENS * 4]
            
            envelope_data = await asyncio.wait_for(
                extract_envelope_data(full_text, zip_code="90210"),
                timeout=OPENAI_TIMEOUT
            )
            logger.info("Envelope extraction completed", extra={"jobId": project_id})
            
        except asyncio.TimeoutError:
            raise AIAnalysisTimeoutError(f"Envelope extraction timed out after {OPENAI_TIMEOUT}s")
        except EnvelopeExtractorError:
            raise  # Re-raise envelope-specific errors
        except Exception as e:
            raise EnvelopeExtractorError(f"Envelope extraction failed: {e}")
        
        # 7. Store parsed data in project
        await update_progress(project_id, 90, "storing_analysis")
        
        # Store the blueprint schema in the project for later use
        await job_service.update_project(
            project_id,
            {
                "parsed_schema_json": blueprint_schema.dict(),
                "envelope_data_json": envelope_data.__dict__ if envelope_data else None
            },
            session
        )
        
        logger.info("AI_ANALYSIS_COMPLETE", extra={"jobId": project_id})
        
    except (MissingAIKeyError, PDFTooLargeError, AIAnalysisTimeoutError, 
            AICleanupError, EnvelopeExtractorError) as e:
        logger.exception("AI_ANALYSIS_CRASH", extra={"jobId": project_id})
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        await job_service.set_project_failed(project_id, error_msg, session)
        raise
    except Exception as e:
        logger.exception("AI_ANALYSIS_UNEXPECTED_ERROR", extra={"jobId": project_id})
        error_msg = f"Unexpected AI analysis error: {type(e).__name__}: {str(e)[:200]}"
        await job_service.set_project_failed(project_id, error_msg, session)
        raise AICleanupError(error_msg)

async def process_job_background(project_id: str, file_path: str, filename: str, email: str = "", zip_code: str = "90210"):
    """Process a job in the background using FastAPI's background tasks"""
    logger.info(f"🚀 BACKGROUND: Job processor started for {project_id} (file={filename}, path={file_path}, email={email})")
    try:
        # Job is already set to processing in upload endpoint
        logger.debug(f"{project_id} – job already in processing state")
        
        # Open PDF and update progress (5%)
        await update_progress(project_id, 5, "opened_pdf")
        
        # TODO: Add actual PDF parsing with PyMuPDF here
        # For now, simulate with sleep
        await asyncio.sleep(1)
        
        # After geometry parsing (25%)
        await update_progress(project_id, 25, "geometry_complete")
        
        # Check if assumptions are already collected (new multi-step flow)
        project = await job_service.get_project(project_id)
        if not project:
            raise Exception("Project not found")
        
        if not project.assumptions_collected:
            # Legacy flow - wait for assumptions modal
            logger.debug(f"{project_id} – waiting for assumptions (legacy flow)")
            assumptions_received = await job_service.wait_for_assumptions(project_id, timeout=900.0)
            
            if not assumptions_received:
                logger.warning(f"{project_id} – timeout waiting for assumptions")
                await job_service.set_project_failed(project_id, "Timeout waiting for user assumptions")
                await rate_limiter.decrement_active_jobs(email, project_id)
                return
            
            logger.debug(f"{project_id} – assumptions received, continuing processing")
        else:
            # New multi-step flow - assumptions already collected
            logger.debug(f"{project_id} – assumptions already collected in multi-step flow")
        
        # Real AI analysis (65% -> 90%)
        async with AsyncSessionLocal() as ai_session:
            await run_ai_analysis(project_id, file_path, ai_session)
        
        # Get the updated project with assumptions
        project = await job_service.get_project(project_id)
        if not project:
            raise Exception("Project not found")
        
        # Use real parsed schema if available, otherwise use mock data
        if project.parsed_schema_json:
            # Load real parsed schema from database
            logger.debug(f"{project_id} – using real parsed schema")
            blueprint_schema = BlueprintSchema.parse_obj(project.parsed_schema_json)
        else:
            # Fallback to mock data for development
            logger.debug(f"{project_id} – using mock schema (parsed data not available)")
            mock_rooms = [
                Room(name="Living Room", dimensions_ft=(20.0, 15.0), floor=1, windows=3, orientation="S", area=300.0),
                Room(name="Kitchen", dimensions_ft=(12.0, 10.0), floor=1, windows=1, orientation="N", area=120.0),
                Room(name="Master Bedroom", dimensions_ft=(16.0, 12.0), floor=1, windows=2, orientation="E", area=192.0),
            ]
            
            blueprint_schema = BlueprintSchema(
                project_id=uuid.UUID(project.id),
                zip_code=zip_code,
                sqft_total=sum(room.area for room in mock_rooms),
                stories=1,
                rooms=mock_rooms
            )
        
        # Calculate Manual J loads with user assumptions
        logger.info(f"{project_id} – starting Manual J calculation (duct_config={project.duct_config}, heating_fuel={project.heating_fuel})")
        manualj_result = calculate_manualj(
            blueprint_schema, 
            duct_config=project.duct_config or "ducted_attic",
            heating_fuel=project.heating_fuel or "gas"
        )
        logger.info(f"{project_id} – Manual J calculation completed")
        
        # Update progress after calculations (95%)
        await update_progress(project_id, 95, "calculations_complete")
        
        # Format result for storage
        result = {
            "heating_total": manualj_result["heating_total"],
            "cooling_total": manualj_result["cooling_total"],
            "zones": manualj_result["zones"],
            "climate_zone": manualj_result["climate_zone"],
            "equipment_recommendations": manualj_result["equipment_recommendations"],
            "design_parameters": manualj_result["design_parameters"],
            "processing_info": {
                "filename": filename,
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "timestamp": time.time()
            }
        }
        
        try:
            logger.debug(f"{project_id} – starting get_project")
            # Get project details for PDF generation
            project = await job_service.get_project(project_id)
            if not project:
                raise Exception("Project not found")
            logger.debug(f"{project_id} – finished get_project")
            
            # Generate PDF report
            try:
                logger.debug(f"{project_id} – starting PDF generation")
                pdf_path = pdf_service.generate_report_pdf(
                    project_id=project_id,
                    project_label=project.project_label,
                    filename=filename,
                    job_result=result
                )
                
                # Update progress before completion (100%)
                await update_progress(project_id, 100, "completed")
                
                # Update job with result and PDF path
                await job_service.set_project_completed(project_id, result, pdf_path)
                logger.info(f"{project_id} – SUCCESS: Job completed with PDF report: {pdf_path}")
                logger.debug(f"{project_id} – finished PDF generation")
                
            except Exception as pdf_error:
                logger.exception(f"{project_id} – error in PDF generation: {pdf_error}")
                # Still mark as completed but without PDF
                await update_progress(project_id, 100, "completed")
                await job_service.set_project_completed(project_id, result)
                logger.info(f"{project_id} – SUCCESS: Job completed without PDF due to PDF generation error")
            
            logger.debug(f"{project_id} – starting cleanup")
            # Cleanup temp file
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"{project_id} – deleted temp file {file_path}")
            
            # Release rate limiter
            await rate_limiter.decrement_active_jobs(email, project_id)
            logger.debug(f"{project_id} – finished cleanup")
            
        except Exception as e:
            logger.exception(f"{project_id} – error in job completion: {e}")
            await job_service.set_project_failed(project_id, str(e))
            await rate_limiter.decrement_active_jobs(email, project_id)
            if os.path.exists(file_path):
                os.unlink(file_path)
            return
        
    except Exception as e:
        logger.exception(f"💥 FATAL: Job {project_id} crashed: {type(e).__name__}: {str(e)}")
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        await job_service.set_project_failed(project_id, error_msg)
        await rate_limiter.decrement_active_jobs(email, project_id)
        if os.path.exists(file_path):
            os.unlink(file_path)

# FastAPI's BackgroundTasks calls process_job_background directly
# No threading or event loop management needed - everything runs in the main async loop