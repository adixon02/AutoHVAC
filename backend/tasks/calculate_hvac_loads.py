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
from typing import Dict, Any, Optional

from services.job_service import job_service
from services.manualj import calculate_manualj_with_audit
from services.climate_data import get_climate_data
from app.parser.geometry_parser_safe import create_safe_parser, GeometryParserTimeout, GeometryParserComplexity
from app.parser.text_parser import TextParser
from app.parser.ai_cleanup import cleanup, AICleanupError
from services.pdf_page_analyzer import PDFPageAnalyzer
from services.envelope_extractor import extract_envelope_data, EnvelopeExtractorError
from services.audit_tracker import create_calculation_audit
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

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
    file_content: bytes,
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
        file_content: PDF file bytes
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
        'errors_encountered': []
    }
    
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
    
    temp_file_path = None
    
    try:
        # Stage 1: File validation and setup
        update_progress_sync("initializing", 5, "Validating PDF file")
        
        # Validate file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > MAX_PDF_SIZE_MB:
            raise ValueError(f"PDF file too large: {file_size_mb:.1f}MB (max: {MAX_PDF_SIZE_MB}MB)")
        
        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # Quick PDF validation
        if not file_content.startswith(b'%PDF'):
            raise ValueError("Invalid PDF file format")
            
        # Validate climate data availability
        climate_data = get_climate_data(zip_code)
        if not climate_data.get('found', False):
            logger.warning(f"Climate data not found for zip {zip_code}, using defaults")
        
        audit_data['climate_data'] = climate_data
        logger.info(f"HVAC calculation started for {project_id} - {filename} - {zip_code}")
        
        # Stage 1.5: Multi-page analysis and best page selection
        update_progress_sync("analyzing_pages", 10, "Analyzing PDF pages for floor plan")
        
        selected_page_number = None
        page_analysis_summary = None
        
        try:
            logger.info(f"Starting multi-page analysis for {project_id}")
            
            # Analyze all pages to find the best floor plan
            page_analyzer = PDFPageAnalyzer(timeout_per_page=30, max_pages=20)
            selected_page_number, page_analyses = page_analyzer.analyze_pdf_pages(temp_file_path)
            
            # Convert to 0-based for internal use
            selected_page_zero_based = selected_page_number - 1
            
            # Generate analysis summary for audit
            page_analysis_summary = page_analyzer.get_analysis_summary(page_analyses)
            audit_data['page_analysis'] = page_analysis_summary
            
            logger.info(f"Multi-page analysis completed for {project_id}")
            logger.info(f"Selected page {selected_page_number} out of {len(page_analyses)} pages")
            logger.info(f"Best page score: {page_analysis_summary['best_score']}")
            
            # Update progress with page selection info
            update_progress_sync("page_selected", 15, f"Selected page {selected_page_number} as best floor plan")
            
        except Exception as e:
            error_msg = f"Multi-page analysis failed: {str(e)}"
            logger.error(f"Multi-page analysis error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'page_analysis', 'error': error_msg})
            
            # Fall back to first page
            selected_page_zero_based = 0
            selected_page_number = 1
            logger.warning(f"Falling back to page 1 for {project_id}")
            update_progress_sync("page_selected", 15, "Using first page (multi-page analysis failed)")

        # Stage 2: Geometry extraction with timeout protection
        update_progress_sync("extracting_geometry", 20, f"Analyzing geometry from page {selected_page_number}")
        
        try:
            logger.info(f"Starting geometry extraction for {project_id}")
            logger.info(f"PDF file: {temp_file_path}, size: {len(file_content)} bytes")
            
            # Create safe parser with 300-second timeout and complexity checks
            geometry_parser = create_safe_parser(timeout=300, enable_complexity_checks=True)
            
            logger.info(f"Calling geometry parser for page {selected_page_number} with timeout protection...")
            raw_geometry = geometry_parser.parse(temp_file_path, page_number=selected_page_zero_based)
            logger.info(f"Geometry parsing completed successfully for page {selected_page_number}")
            
            # Validate geometry extraction results
            if not raw_geometry or not hasattr(raw_geometry, 'lines'):
                raise ValueError("No geometric data extracted from PDF")
                
            geometry_summary = {
                'lines_found': len(getattr(raw_geometry, 'lines', [])),
                'rectangles_found': len(getattr(raw_geometry, 'rectangles', [])),
                'polylines_found': len(getattr(raw_geometry, 'polylines', [])),
                'page_dimensions': [
                    getattr(raw_geometry, 'page_width', 0),
                    getattr(raw_geometry, 'page_height', 0)
                ],
                'scale_factor': getattr(raw_geometry, 'scale_factor', 1.0)
            }
            audit_data['geometry_summary'] = geometry_summary
            
            logger.info(f"Geometry extraction completed: {geometry_summary}")
            
        except GeometryParserTimeout as e:
            error_msg = f"Geometry extraction timed out for page {selected_page_number}: {str(e)}"
            logger.error(f"Geometry extraction timeout for {project_id}: {error_msg}")
            audit_data['errors_encountered'].append({'stage': 'geometry', 'error': error_msg, 'error_type': 'timeout'})
            update_progress_sync("failed", 0, f"Page {selected_page_number} geometry extraction timed out after 300 seconds (5 minutes)")
            raise ValueError(error_msg)
        except GeometryParserComplexity as e:
            error_msg = f"Page {selected_page_number} is too complex to process: {str(e)}"
            logger.error(f"Geometry complexity error for {project_id}: {error_msg}")
            audit_data['errors_encountered'].append({'stage': 'geometry', 'error': error_msg, 'error_type': 'complexity'})
            update_progress_sync("failed", 0, f"Page {selected_page_number} is too complex - try a simpler blueprint or different page")
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Geometry extraction failed: {str(e)}"
            logger.error(f"Geometry extraction error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'geometry', 'error': error_msg, 'error_type': type(e).__name__})
            update_progress_sync("failed", 0, f"Geometry extraction failed: {str(e)[:100]}")
            raise ValueError(error_msg)
        
        # Stage 3: Text extraction from selected page
        update_progress_sync("extracting_text", 35, f"Extracting text and labels from page {selected_page_number}")
        
        try:
            text_parser = TextParser()
            raw_text = text_parser.parse(temp_file_path, page_number=selected_page_zero_based)
            
            # Validate text extraction results
            if not raw_text:
                raise ValueError("No text data extracted from PDF")
                
            text_summary = {
                'words_found': len(getattr(raw_text, 'words', [])),
                'room_labels': len(getattr(raw_text, 'room_labels', [])),
                'dimensions': len(getattr(raw_text, 'dimensions', [])),
                'notes_found': len(getattr(raw_text, 'notes', []))
            }
            audit_data['text_summary'] = text_summary
            
            logger.info(f"Text extraction completed: {text_summary}")
            
        except Exception as e:
            error_msg = f"Text extraction failed: {str(e)}"
            logger.error(f"Text extraction error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'text', 'error': error_msg})
            update_progress_sync("failed", 0, f"Text extraction failed: {str(e)[:100]}")
            raise ValueError(error_msg)
        
        # Stage 4: AI cleanup and structuring
        update_progress_sync("ai_processing", 50, "AI analysis and data structuring")
        
        try:
            # Check for OpenAI API key
            if not os.getenv("OPENAI_API_KEY"):
                raise AICleanupError("OPENAI_API_KEY not configured")
            
            # Run AI cleanup with timeout protection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                blueprint_schema = loop.run_until_complete(
                    asyncio.wait_for(
                        cleanup(raw_geometry, raw_text),
                        timeout=AI_TIMEOUT_SECONDS
                    )
                )
            finally:
                loop.close()
            
            # Validate AI cleanup results
            if not blueprint_schema or not blueprint_schema.rooms:
                raise AICleanupError("No rooms identified in blueprint")
            
            # Store schema for audit
            audit_data['blueprint_schema'] = blueprint_schema.dict()
            audit_data['rooms_identified'] = len(blueprint_schema.rooms)
            audit_data['total_area'] = blueprint_schema.sqft_total
            
            logger.info(f"AI processing completed: {len(blueprint_schema.rooms)} rooms, {blueprint_schema.sqft_total} sqft")
            
        except asyncio.TimeoutError:
            error_msg = f"AI processing timed out after {AI_TIMEOUT_SECONDS} seconds"
            logger.error(f"AI processing timeout for {project_id}: {error_msg}")
            audit_data['errors_encountered'].append({'stage': 'ai', 'error': error_msg})
            update_progress_sync("failed", 0, f"AI processing timed out after {AI_TIMEOUT_SECONDS}s")
            raise AICleanupError(error_msg)
        except Exception as e:
            error_msg = f"AI processing failed: {str(e)}"
            logger.error(f"AI processing error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'ai', 'error': error_msg})
            update_progress_sync("failed", 0, f"AI processing failed: {str(e)[:100]}")
            raise AICleanupError(error_msg)
        
        # Stage 5: Envelope analysis (optional enhancement)
        update_progress_sync("envelope_analysis", 65, "Analyzing building envelope")
        
        envelope_data = None
        try:
            # Extract full text for envelope analysis
            import fitz
            pdf_doc = fitz.open(temp_file_path)
            full_text = ""
            for page in pdf_doc:
                full_text += page.get_text()
            pdf_doc.close()
            
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
                    audit_data['envelope_data'] = envelope_data.__dict__
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
                'climate_zone': manualj_results['climate_zone'],
                'calculation_method': manualj_results['design_parameters'].get('calculation_method', 'ACCA Manual J'),
                'zones_calculated': len(manualj_results['zones'])
            }
            
            logger.info(f"Manual J calculations completed: {manualj_results['heating_total']} BTU/h heating, {manualj_results['cooling_total']} BTU/h cooling")
            
        except Exception as e:
            error_msg = f"Manual J calculations failed: {str(e)}"
            logger.error(f"Manual J calculation error for {project_id}: {error_msg}", exc_info=True)
            audit_data['errors_encountered'].append({'stage': 'calculations', 'error': error_msg})
            update_progress_sync("failed", 0, f"Load calculations failed: {str(e)[:100]}")
            raise ValueError(error_msg)
        
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
                'rooms_identified': len(blueprint_schema.rooms),
                'total_area': blueprint_schema.sqft_total,
                'stories': blueprint_schema.stories,
                'geometry_confidence': 'high' if geometry_summary['lines_found'] > 50 else 'medium',
                'selected_page': selected_page_number,
                'page_selection_score': page_analysis_summary.get('best_score', 0.0) if page_analysis_summary else 0.0,
                'total_pages_analyzed': page_analysis_summary.get('total_pages_analyzed', 1) if page_analysis_summary else 1
            },
            
            'processing_stages': audit_data['stages_completed'],
            'data_sources': {
                'climate_data_source': 'ASHRAE/IECC',
                'construction_assumptions': manualj_results['design_parameters'].get('construction_vintage', 'estimated'),
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
                page_selection_data=page_analysis_summary
            )
            final_results['comprehensive_audit_id'] = audit_id
        except Exception as e:
            logger.warning(f"Failed to create comprehensive audit record: {e}")
        
        # Stage 8: Store results and complete
        update_progress_sync("completed", 100, "Calculation completed successfully")
        
        # Update project with final results
        job_service.sync_update_project(project_id, {
            'status': 'completed',
            'result': final_results,
            'progress_percent': 100,
            'current_stage': 'completed'
        })
        
        logger.info(f"HVAC calculation completed successfully for {project_id}")
        return final_results
        
    except Exception as e:
        # Comprehensive error handling
        error_type = type(e).__name__
        error_message = str(e)
        
        # Log detailed error information
        logger.exception(f"HVAC calculation failed for {project_id}: {error_type}: {error_message}")
        
        # Store error information in audit
        audit_data['final_error'] = {
            'type': error_type,
            'message': error_message,
            'timestamp': time.time(),
            'total_processing_time': time.time() - calculation_start_time
        }
        
        # Update project with failure status
        job_service.sync_update_project(project_id, {
            'status': 'failed',
            'error': f"{error_type}: {error_message[:500]}",  # Truncate long errors
            'progress_percent': 0,
            'current_stage': 'failed'
        })
        
        # Try to save audit data even on failure
        try:
            create_calculation_audit(
                blueprint_schema=None,
                calculation_result=None,
                climate_data=climate_data if 'climate_data' in locals() else None,
                envelope_data=None,
                user_id=email,
                duct_config=duct_config,
                heating_fuel=heating_fuel,
                processing_metadata=audit_data,
                error_details={'type': error_type, 'message': error_message},
                page_selection_data=page_analysis_summary if 'page_analysis_summary' in locals() else None
            )
        except Exception as audit_error:
            logger.warning(f"Failed to save error audit data: {audit_error}")
        
        # Re-raise the original exception
        raise
        
    finally:
        # Cleanup temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {cleanup_error}")


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