"""
Comprehensive HVAC Load Calculation Task

This task implements the complete pipeline from PDF blueprint to ACCA Manual J compliant 
load calculations with full auditability and error handling.

Pipeline stages:
1. File validation and temporary storage
2. Geometry extraction from PDF
3. Text extraction from PDF  
4. AI cleanup and structuring
5. ACCA Manual J load calculations
6. Climate data integration
7. Audit trail creation
8. Result storage and cleanup
"""

from celery import Celery
import time
import io
import os
import tempfile
import asyncio
import logging
import hashlib
import traceback
from typing import Dict, Any, Optional
from utils.json_utils import safe_dict, ensure_json_serializable

from services.job_service import job_service
from services.manualj import calculate_manualj_with_audit
from services.climate_data import get_climate_data
from services.blueprint_parser import parse_blueprint_to_json, BlueprintParsingError
from services.envelope_extractor import extract_envelope_data, EnvelopeExtractorError
from services.audit_tracker import create_calculation_audit
from services.s3_storage import storage_service
from services.error_types import (
    CriticalError, NonCriticalError, AuditError, 
    ValidationError, categorize_exception, log_error_with_context
)
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Log S3 configuration at worker startup
logger.info(f"[WORKER STARTUP] S3 storage service initialized")
logger.info(f"[WORKER STARTUP] S3 bucket: {storage_service.bucket_name}")
logger.info(f"[WORKER STARTUP] AWS region: {storage_service.aws_region}")

celery_app = Celery(
    'autohvac',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Production safeguards
MAX_PDF_SIZE_MB = 50
MAX_PDF_PAGES = 100
AI_TIMEOUT_SECONDS = 300
MAX_PROCESSING_TIME = 300   # 5 minutes max as requested


@celery_app.task(
    acks_late=True, 
    reject_on_worker_lost=True, 
    time_limit=MAX_PROCESSING_TIME,
    soft_time_limit=MAX_PROCESSING_TIME - 30  # 30 seconds before hard limit
)
def calculate_hvac_loads(
    project_id: str,
    filename: str, 
    email: str,
    zip_code: str,
    duct_config: str = "ducted_attic",
    heating_fuel: str = "gas"
) -> Dict[str, Any]:
    """
    Complete HVAC load calculation pipeline with ACCA Manual J compliance
    
    Args:
        project_id: Unique project identifier
        filename: Original filename for reference
        email: User email for notifications/logging
        zip_code: Project location for climate data
        duct_config: Duct system configuration
        heating_fuel: Heating system fuel type
        
    Returns:
        Dict with complete calculation results and audit information
        
    Raises:
        Various exceptions for different failure modes, all logged and stored
    """
    
    calculation_start_time = time.time()
    audit_data = {
        'project_id': project_id,
        'filename': filename, 
        'email': email,
        'zip_code': zip_code,
        'duct_config': duct_config,
        'heating_fuel': heating_fuel,
        'start_time': calculation_start_time,
        'stages_completed': [],
        'errors_encountered': [],
        'page_analysis': None  # Initialize to prevent KeyError in error paths
    }
    
    # Initialize variables that might be referenced in error paths
    climate_data = None
    blueprint_schema = None
    parsing_metadata = None
    selected_page_analysis = None
    manualj_results = None
    envelope_data = None
    
    def update_progress_sync(stage: str, percent: int, message: str = None):
        """Update job progress synchronously for Celery worker"""
        try:
            updates = {
                "current_stage": stage,
                "progress_percent": percent
            }
            if message:
                updates["status_message"] = message
                
            success = job_service.sync_update_project(project_id, updates)
            if success:
                audit_data['stages_completed'].append({
                    'stage': stage,
                    'percent': percent,
                    'timestamp': time.time(),
                    'message': message
                })
                logger.info(f"Progress: {project_id} - {percent}% - {stage} - {message or ''}")
            else:
                logger.warning(f"Failed to update progress for {project_id}")
        except Exception as e:
            logger.exception(f"Error updating progress for {project_id}: {e}")
    
    logger.info(f"[CELERY TASK] Starting task for project {project_id}")
    
    # Check if file exists in S3
    file_exists = storage_service.file_exists(project_id)
    
    logger.info(f"[CELERY START] S3 file check for {project_id}: exists={file_exists}")
    
    if not file_exists:
        error_msg = f"PDF file not found in S3 at start of Celery task: {project_id}"
        logger.error(f"[CELERY TASK] {error_msg}")
        
        audit_data['errors_encountered'].append({
            'stage': 'file_check',
            'error': error_msg,
            'timestamp': time.time()
        })
        job_service.sync_set_project_failed(project_id, error_msg)
        raise FileNotFoundError(error_msg)
    
    # Download file from S3 to temporary location for processing
    try:
        file_path = storage_service.download_to_temp_file(project_id)
        logger.info(f"[CELERY TASK] Downloaded file from S3 to temp location: {file_path}")
    except Exception as e:
        error_msg = f"Failed to download file from S3: {str(e)}"
        logger.error(f"[CELERY TASK] {error_msg}")
        audit_data['errors_encountered'].append({
            'stage': 'file_download',
            'error': error_msg,
            'timestamp': time.time()
        })
        job_service.sync_set_project_failed(project_id, error_msg)
        raise
    
    try:
        # Stage 1: File validation and setup
        update_progress_sync("initializing", 5, "Validating PDF file")
        
        # Verify file exists and is accessible
        if not os.path.exists(file_path):
            raise ValidationError(f"PDF file not found at {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise ValidationError(f"Cannot read PDF file at {file_path}")
        
        # Validate file size
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb > MAX_PDF_SIZE_MB:
            raise ValidationError(f"PDF file too large: {file_size_mb:.1f}MB (max: {MAX_PDF_SIZE_MB}MB)")
        
        # Quick PDF validation by reading header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                raise ValidationError("Invalid PDF file format")
            
        # Validate climate data availability
        try:
            climate_data = get_climate_data(zip_code)
            if not climate_data.get('found', False):
                logger.warning(f"Climate data not found for zip {zip_code}, using defaults")
        except Exception as e:
            logger.warning(f"Error getting climate data for zip {zip_code}: {e}, using defaults")
            climate_data = {'found': False, 'error': str(e)}
        
        audit_data['climate_data'] = climate_data
        logger.info(f"HVAC calculation started for {project_id} - {filename} - {zip_code}")
        
        # NEW JSON-FIRST APPROACH: Single-stage PDF to JSON conversion
        update_progress_sync("parsing_blueprint", 20, "Converting PDF to comprehensive JSON representation")
        
        # Log metrics before parsing
        parsing_start_time = time.time()
        logger.info(f"[METRICS] Starting blueprint parsing for {project_id}")
        logger.info(f"[METRICS] PDF file: {file_path}, size: {file_size_mb:.1f}MB")
        logger.info(f"[METRICS] User: {email}, Zip: {zip_code}")
        
        # Initialize variables to prevent UnboundLocalError
        parsing_metadata = None
        parsing_duration = 0
        
        try:
            logger.info(f"Starting JSON-first blueprint parsing for {project_id}")
            logger.info(f"PDF file: {file_path}, size: {file_size} bytes")
            
            # Use the new blueprint parser service for complete PDF to JSON conversion
            # CRITICAL: Use the file path from disk, not temp file
            blueprint_schema = parse_blueprint_to_json(
                pdf_path=file_path,
                filename=filename,
                zip_code=zip_code,
                project_id=project_id
            )
            
            # Log parsing completion metrics
            parsing_end_time = time.time()
            parsing_duration = parsing_end_time - parsing_start_time
            logger.info(f"[METRICS] Blueprint parsing completed in {parsing_duration:.2f}s")
            
            # Store the comprehensive JSON in the database as canonical representation
            job_service.sync_update_project(project_id, {
                'parsed_schema_json': safe_dict(blueprint_schema)
            })
            
            # Extract metadata for audit
            parsing_metadata = blueprint_schema.parsing_metadata
            
            # Now log the parsing path after parsing_metadata is assigned
            logger.info(f"[METRICS] Parsing path used: {parsing_metadata.ai_status.value if hasattr(parsing_metadata, 'ai_status') else 'unknown'}")
            audit_data['blueprint_schema'] = safe_dict(blueprint_schema)
            audit_data['rooms_identified'] = len(blueprint_schema.rooms)
            audit_data['total_area'] = blueprint_schema.sqft_total
            audit_data['parsing_metadata'] = safe_dict(parsing_metadata)
            
            # Extract page analysis info
            if parsing_metadata and hasattr(parsing_metadata, 'page_analyses') and parsing_metadata.page_analyses:
                selected_page_analysis = next(
                    (p for p in parsing_metadata.page_analyses if p.selected), 
                    parsing_metadata.page_analyses[0] if parsing_metadata.page_analyses else None
                )
                if selected_page_analysis:
                    audit_data['page_analysis'] = {
                        'selected_page': parsing_metadata.selected_page,
                        'total_pages_analyzed': len(parsing_metadata.page_analyses),
                        'best_score': selected_page_analysis.score,
                        'page_details': [safe_dict(p) for p in parsing_metadata.page_analyses]
                    }
            
            # Report parsing results
            logger.info(f"Blueprint parsing completed successfully:")
            if parsing_metadata:
                logger.info(f"  - Selected page: {getattr(parsing_metadata, 'selected_page', 'unknown')}")
                logger.info(f"  - Overall confidence: {getattr(parsing_metadata, 'overall_confidence', 0.0):.2f}")
                logger.info(f"  - Processing time: {getattr(parsing_metadata, 'processing_time_seconds', 0.0):.2f}s")
            logger.info(f"  - Rooms identified: {len(blueprint_schema.rooms)}")
            logger.info(f"  - Total area: {blueprint_schema.sqft_total} sqft")
            
            update_progress_sync("blueprint_parsed", 50, f"Successfully parsed {len(blueprint_schema.rooms)} rooms from page {getattr(parsing_metadata, 'selected_page', 1) if parsing_metadata else 1}")
            
        except BlueprintParsingError as e:
            error_msg = f"Blueprint parsing failed: {str(e)}"
            logger.error(f"Blueprint parsing error for {project_id}: {error_msg}")
            audit_data['errors_encountered'].append({
                'stage': 'blueprint_parsing', 
                'error': error_msg, 
                'error_type': 'BlueprintParsingError',
                'parsing_metadata': safe_dict(parsing_metadata) if parsing_metadata else None
            })
            update_progress_sync("failed", 0, f"Blueprint parsing failed: {str(e)[:100]}")
            raise CriticalError(error_msg, {'error_type': 'BlueprintParsingError'})
        except Exception as e:
            error_msg = f"Unexpected blueprint parsing error: {str(e)}"
            logger.error(f"Unexpected blueprint parsing error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({
                'stage': 'blueprint_parsing', 
                'error': error_msg, 
                'error_type': type(e).__name__,
                'parsing_metadata': safe_dict(parsing_metadata) if parsing_metadata else None
            })
            update_progress_sync("failed", 0, f"Blueprint parsing failed: {str(e)[:100]}")
            # Categorize the error appropriately
            categorized_error = categorize_exception(e)
            raise categorized_error
        
        # Stage 5: Envelope analysis (optional enhancement)
        update_progress_sync("envelope_analysis", 65, "Analyzing building envelope")
        
        envelope_data = None
        try:
            # Extract full text for envelope analysis using thread-safe operation
            from services.pdf_thread_manager import safe_pymupdf_operation
            
            def extract_text_for_envelope(doc):
                full_text = ""
                for page in doc:
                    full_text += page.get_text()
                return full_text
            
            full_text = safe_pymupdf_operation(
                pdf_path=file_path,
                operation_func=extract_text_for_envelope,
                operation_name="envelope_text_extraction"
            )
            
            # Run envelope extraction with timeout
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                envelope_data = loop.run_until_complete(
                    asyncio.wait_for(
                        extract_envelope_data(full_text, zip_code),
                        timeout=AI_TIMEOUT_SECONDS
                    )
                )
                if envelope_data:
                    audit_data['envelope_data'] = safe_dict(envelope_data)
            finally:
                loop.close()
                
        except Exception as e:
            # Envelope analysis is optional - log but don't fail
            logger.warning(f"Envelope analysis failed for {project_id} (non-critical): {e}")
            audit_data['errors_encountered'].append({
                'stage': 'envelope', 
                'error': f"Non-critical: {str(e)}"
            })
        
        # Stage 6: ACCA Manual J Load Calculations
        update_progress_sync("calculating_loads", 80, "Performing ACCA Manual J calculations")
        
        try:
            # Ensure zip code is set correctly
            blueprint_schema.zip_code = zip_code
            
            # Calculate loads with full audit trail
            manualj_results = calculate_manualj_with_audit(
                schema=blueprint_schema,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                climate_data=climate_data,
                construction_vintage='1980-2000',  # Default construction vintage
                envelope_data=envelope_data,
                create_audit=True,
                user_id=email
            )
            
            # Validate calculation results
            if not manualj_results or 'heating_total' not in manualj_results:
                raise ValueError("Manual J calculations produced invalid results")
            
            if manualj_results['heating_total'] <= 0 or manualj_results['cooling_total'] <= 0:
                logger.warning(f"Unusual load calculation results: H={manualj_results['heating_total']}, C={manualj_results['cooling_total']}")
            
            audit_data['calculation_results'] = {
                'heating_total': manualj_results['heating_total'],
                'cooling_total': manualj_results['cooling_total'],
                'climate_zone': manualj_results.get('climate_zone', 'unknown'),
                'calculation_method': manualj_results.get('design_parameters', {}).get('calculation_method', 'ACCA Manual J'),
                'zones_calculated': len(manualj_results.get('zones', []))
            }
            
            logger.info(f"Manual J calculations completed: {manualj_results['heating_total']} BTU/h heating, {manualj_results['cooling_total']} BTU/h cooling")
            
        except Exception as e:
            error_msg = f"Manual J calculations failed: {str(e)}"
            logger.error(f"Manual J calculation error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'calculations', 'error': error_msg})
            update_progress_sync("failed", 0, f"Load calculations failed: {str(e)[:100]}")
            raise CriticalError(error_msg, {'original_error': type(e).__name__})
        
        # Stage 7: Result compilation and audit
        update_progress_sync("finalizing", 95, "Compiling results and creating audit trail")
        
        # Compile final results
        final_results = {
            'project_id': project_id,
            'filename': filename,
            'email': email,
            'zip_code': zip_code,
            'processing_timestamp': time.time(),
            'processing_time_seconds': time.time() - calculation_start_time,
            
            # HVAC calculation results
            'heating_total': manualj_results['heating_total'],
            'cooling_total': manualj_results['cooling_total'],
            'zones': manualj_results['zones'],
            'climate_zone': manualj_results['climate_zone'],
            'equipment_recommendations': manualj_results['equipment_recommendations'],
            'design_parameters': manualj_results['design_parameters'],
            
            # Audit and validation data
            'audit_id': manualj_results.get('audit_id'),
            'calculation_method': 'ACCA Manual J 8th Edition',
            'blueprint_analysis': {
                'rooms_identified': len(blueprint_schema.rooms) if blueprint_schema and hasattr(blueprint_schema, 'rooms') else 0,
                'total_area': getattr(blueprint_schema, 'sqft_total', 0) if blueprint_schema else 0,
                'stories': getattr(blueprint_schema, 'stories', 1) if blueprint_schema else 1,
                'geometry_confidence': 'high' if parsing_metadata and hasattr(parsing_metadata, 'overall_confidence') and parsing_metadata.overall_confidence > 0.8 else 'medium',
                'selected_page': getattr(parsing_metadata, 'selected_page', 1) if parsing_metadata else 1,
                'page_selection_score': getattr(selected_page_analysis, 'score', 0.0) if selected_page_analysis else 0.0,
                'total_pages_analyzed': len(parsing_metadata.page_analyses) if parsing_metadata and hasattr(parsing_metadata, 'page_analyses') else 1
            },
            
            'processing_stages': audit_data['stages_completed'],
            'data_sources': {
                'climate_data_source': 'ASHRAE/IECC',
                'construction_assumptions': manualj_results.get('design_parameters', {}).get('construction_vintage', 'estimated') if manualj_results else 'estimated',
                'envelope_data_extracted': envelope_data is not None
            }
        }
        
        # Create comprehensive audit record
        try:
            audit_id = create_calculation_audit(
                blueprint_schema=blueprint_schema,
                calculation_result=manualj_results,
                climate_data=climate_data,
                envelope_data=envelope_data,
                user_id=email,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                processing_metadata=audit_data,
                page_selection_data=audit_data.get('page_analysis')
            )
            final_results['comprehensive_audit_id'] = audit_id
        except Exception as e:
            logger.error(f"Failed to create comprehensive audit record (non-critical): {type(e).__name__}: {str(e)}")
            logger.info("Calculation results are still valid, continuing without audit record")
        
        # Stage 8: Store results and complete
        update_progress_sync("completed", 100, "Calculation completed successfully")
        
        # Log final metrics
        total_duration = time.time() - calculation_start_time
        logger.info(f"[METRICS] Total processing time: {total_duration:.2f}s")
        logger.info(f"[METRICS] File size: {file_size_mb:.1f}MB")
        logger.info(f"[METRICS] Parsing duration: {parsing_duration:.2f}s")
        logger.info(f"[METRICS] Rooms found: {len(blueprint_schema.rooms) if blueprint_schema and hasattr(blueprint_schema, 'rooms') else 0}")
        logger.info(f"[METRICS] Total area: {getattr(blueprint_schema, 'sqft_total', 0) if blueprint_schema else 0} sqft")
        logger.info(f"[METRICS] Heating load: {manualj_results['heating_total']} BTU/h")
        logger.info(f"[METRICS] Cooling load: {manualj_results['cooling_total']} BTU/h")
        
        # Update project with final results
        # NOTE: File cleanup happens automatically via job_service.sync_set_project_completed
        # Ensure all data is JSON serializable before sending to database
        job_service.sync_set_project_completed(project_id, ensure_json_serializable(final_results))
        
        # Send email notification with report link
        try:
            from core.email import email_service
            from services.user_service import user_service
            from database import SessionLocal
            
            # Check if this is the user's first report
            with SessionLocal() as session:
                is_first_report = user_service.sync_check_is_first_report(email, session)
            
            # Generate report view URL
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            view_url = f"{frontend_url}/report/{project_id}"
            
            # Send async email in background (don't block on email sending)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                email_service.send_report_ready_with_upgrade_cta(
                    to_email=email,
                    project_label=filename.replace('.pdf', '').replace('.png', '').replace('.jpg', '').replace('.jpeg', ''),
                    view_url=view_url,
                    is_first_report=is_first_report
                )
            )
            loop.close()
            logger.info(f"Report completion email sent to {email} for project {project_id}")
        except Exception as e:
            # Don't fail the task if email sending fails
            logger.error(f"Failed to send report ready email: {str(e)}")
        
        logger.info(f"HVAC calculation completed successfully for {project_id}")
        return final_results
        
    except (CriticalError, ValidationError, TimeoutError) as e:
        # Known critical errors - handle specifically
        error_type = type(e).__name__
        error_message = str(e)
        
        log_error_with_context(e, {
            'project_id': project_id,
            'stage': audit_data.get('stages_completed', [])[-1]['stage'] if audit_data.get('stages_completed') else 'unknown',
            'processing_time': time.time() - calculation_start_time
        })
        
        # Store error information in audit
        audit_data['final_error'] = {
            'type': error_type,
            'message': error_message,
            'timestamp': time.time(),
            'total_processing_time': time.time() - calculation_start_time,
            'is_critical': True
        }
        
        # Update project with failure status
        job_service.sync_set_project_failed(project_id, f"{error_type}: {error_message[:500]}")
        
        # Try to save audit data even on failure
        try:
            create_calculation_audit(
                blueprint_schema=blueprint_schema if 'blueprint_schema' in locals() else None,
                calculation_result=None,
                climate_data=climate_data if 'climate_data' in locals() else None,
                envelope_data=envelope_data if 'envelope_data' in locals() else None,
                user_id=email,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                processing_metadata=audit_data,
                error_details={'type': error_type, 'message': error_message},
                page_selection_data=audit_data.get('page_analysis')
            )
        except Exception as audit_error:
            logger.warning(f"Failed to save error audit data: {audit_error}")
        
        # Re-raise the original error
        raise
        
    except Exception as e:
        # Unknown errors - categorize and handle
        categorized_error = categorize_exception(e)
        error_type = type(categorized_error).__name__
        error_message = str(categorized_error)
        
        log_error_with_context(categorized_error, {
            'project_id': project_id,
            'original_error': type(e).__name__,
            'stage': audit_data.get('stages_completed', [])[-1]['stage'] if audit_data.get('stages_completed') else 'unknown',
            'processing_time': time.time() - calculation_start_time
        })
        
        # Store error information in audit
        audit_data['final_error'] = {
            'type': error_type,
            'original_type': type(e).__name__,
            'message': error_message,
            'timestamp': time.time(),
            'total_processing_time': time.time() - calculation_start_time,
            'is_critical': isinstance(categorized_error, CriticalError)
        }
        
        # Update project with failure status and cleanup files
        job_service.sync_set_project_failed(project_id, f"{error_type}: {error_message[:500]}")
        
        # Try to save audit data even on failure
        try:
            create_calculation_audit(
                blueprint_schema=blueprint_schema if 'blueprint_schema' in locals() else None,
                calculation_result=None,
                climate_data=climate_data if 'climate_data' in locals() else None,
                envelope_data=envelope_data if 'envelope_data' in locals() else None,
                user_id=email,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                processing_metadata=audit_data,
                error_details={'type': error_type, 'original_type': type(e).__name__, 'message': error_message},
                page_selection_data=audit_data.get('page_analysis')
            )
        except Exception as audit_error:
            logger.warning(f"Failed to save error audit data: {audit_error}")
        
        # Re-raise the categorized exception
        raise categorized_error
        
    finally:
        # Clean up the temporary file downloaded from S3
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")
        
        logger.info(f"Completed processing for {project_id}")


@celery_app.task
def health_check():
    """Health check task for monitoring Celery workers"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "worker_capabilities": [
            "hvac_load_calculations",
            "pdf_processing", 
            "ai_analysis",
            "manual_j_compliance"
        ]
    }