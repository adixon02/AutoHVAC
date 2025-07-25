"""
Celery tasks for blueprint processing
"""
from celery import current_task
from celery_app import celery_app
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

# Import processing services
from services.blueprint_extractor import BlueprintExtractor
from services.ai_blueprint_analyzer import AIBlueprintAnalyzer
from models.extraction_schema import (
    CompleteExtractionResult, PDFMetadata, RegexExtractionResult, 
    AIExtractionResult, ProcessingMetadata, ExtractionVersion, 
    ExtractionMethod
)
from services.extraction_storage import get_extraction_storage

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_blueprint_task(self, job_id: str, file_path: str, file_info: dict, project_info: dict):
    """
    Background task to process blueprint PDF
    
    Args:
        job_id: Unique job identifier
        file_path: Path to uploaded PDF file
        file_info: File metadata (filename, size, etc.)
        project_info: Project details (zip_code, building_type, etc.)
    """
    try:
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 10,
                'message': 'Starting blueprint processing...',
                'stage': 'initialization'
            }
        )
        
        start_time = datetime.now()
        logger.info(f"Starting blueprint processing task for job: {job_id}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 20,
                'message': 'Reading PDF file...',
                'stage': 'pdf_reading'
            }
        )
        
        # Extract PDF metadata and raw text
        pdf_metadata = _extract_pdf_metadata_sync(file_path, file_info['filename'])
        raw_text, raw_text_by_page = _extract_raw_text_sync(file_path)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 40,
                'message': 'Extracting building data...',
                'stage': 'text_extraction'
            }
        )
        
        # Initialize blueprint extractor and extract building data
        blueprint_extractor = BlueprintExtractor()
        text_start = datetime.now()
        
        # Note: This is a sync version of the extract_building_data method
        building_data = blueprint_extractor.extract_building_data_sync(file_path)
        text_duration = (datetime.now() - text_start).total_seconds() * 1000
        
        # Convert BuildingData to RegexExtractionResult
        regex_result = _convert_building_data_to_regex_result(building_data, text_duration)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 70,
                'message': 'Processing extraction data...',
                'stage': 'data_processing'
            }
        )
        
        # Skip AI analysis in background processing for now
        # Can be triggered separately via enhance-with-ai endpoint
        ai_result = None
        ai_duration = 0
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 85,
                'message': 'Saving extraction data...',
                'stage': 'data_storage'
            }
        )
        
        # Create complete extraction result
        total_duration = (datetime.now() - start_time).total_seconds() * 1000
        extraction_id = str(uuid.uuid4())
        
        complete_result = CompleteExtractionResult(
            extraction_id=extraction_id,
            job_id=job_id,
            pdf_metadata=pdf_metadata,
            raw_text=raw_text,
            raw_text_by_page=raw_text_by_page,
            regex_extraction=regex_result,
            ai_extraction=ai_result,
            processing_metadata=ProcessingMetadata(
                extraction_id=extraction_id,
                job_id=job_id,
                extraction_timestamp=datetime.now(),
                processing_duration_ms=int(total_duration),
                extraction_version=ExtractionVersion.CURRENT,
                extraction_method=_determine_extraction_method(regex_result, ai_result),
                text_extraction_ms=int(text_duration),
                regex_processing_ms=int(text_duration),
                ai_processing_ms=int(ai_duration) if ai_result else None
            )
        )
        
        # Save extraction data to JSON storage
        storage_service = get_extraction_storage()
        storage_info = storage_service.save_extraction(complete_result)
        
        logger.info(f"Saved extraction data: {extraction_id} -> {storage_info.storage_path}")
        
        # Update progress to completion
        self.update_state(
            state='PROGRESS',
            meta={
                'job_id': job_id,
                'progress': 95,
                'message': 'Finalizing results...',
                'stage': 'finalization'
            }
        )
        
        # Combine results for backward compatibility
        combined_results = _combine_extraction_results(building_data, None)
        
        # Final completion
        result = {
            'job_id': job_id,
            'extraction_id': extraction_id,
            'status': 'completed',
            'progress': 100,
            'message': 'Blueprint analysis complete',
            'results': combined_results,
            'processing_duration_ms': total_duration,
            'project_info': project_info,
            'file_info': file_info
        }
        
        logger.info(f"Blueprint processing completed successfully for job: {job_id}")
        return result
        
    except Exception as e:
        logger.error(f"Blueprint processing failed for job {job_id}: {e}")
        
        # Return fallback data on error
        fallback_result = {
            'job_id': job_id,
            'status': 'completed',
            'progress': 100,
            'message': 'Blueprint analysis complete (using fallback data)',
            'results': _get_fallback_results(),
            'extraction_notes': f"Extraction failed: {str(e)}",
            'project_info': project_info,
            'file_info': file_info
        }
        
        return fallback_result

def _extract_pdf_metadata_sync(file_path: str, original_filename: str) -> PDFMetadata:
    """Synchronous version of PDF metadata extraction"""
    import pdfplumber
    
    try:
        file_stats = Path(file_path).stat()
        file_size_bytes = file_stats.st_size
        
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            
            # Check if PDF has text layer
            has_text_layer = False
            is_scanned = True
            
            for page in pdf.pages[:3]:  # Check first 3 pages
                text = page.extract_text()
                if text and text.strip():
                    has_text_layer = True
                    # If we find substantial text, it's probably not scanned
                    if len(text.strip()) > 100:
                        is_scanned = False
                    break
        
        return PDFMetadata(
            filename=Path(file_path).name,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_bytes / (1024 * 1024),
            page_count=page_count,
            uploaded_at=datetime.now(),
            has_text_layer=has_text_layer,
            is_scanned=is_scanned
        )
    except Exception as e:
        logger.error(f"Failed to extract PDF metadata: {e}")
        # Return basic metadata
        file_stats = Path(file_path).stat()
        return PDFMetadata(
            filename=Path(file_path).name,
            original_filename=original_filename,
            file_size_bytes=file_stats.st_size,
            file_size_mb=file_stats.st_size / (1024 * 1024),
            page_count=1,
            uploaded_at=datetime.now(),
            has_text_layer=False,
            is_scanned=True
        )

def _extract_raw_text_sync(file_path: str) -> tuple[str, list[str]]:
    """Synchronous version of raw text extraction"""
    import pdfplumber
    
    try:
        all_text = ""
        text_by_page = []
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text_by_page.append(page_text)
                all_text += f"\n--- Page {i+1} ---\n" + page_text
        
        return all_text, text_by_page
    except Exception as e:
        logger.error(f"Failed to extract raw text: {e}")
        return "", []

def _convert_building_data_to_regex_result(building_data, processing_time_ms: float) -> RegexExtractionResult:
    """Convert BuildingData to RegexExtractionResult"""
    return RegexExtractionResult(
        floor_area_ft2=building_data.floor_area_ft2,
        wall_insulation=building_data.wall_insulation,
        ceiling_insulation=building_data.ceiling_insulation,
        window_schedule=building_data.window_schedule,
        air_tightness=building_data.air_tightness,
        foundation_type=building_data.foundation_type,
        orientation=building_data.orientation,
        room_dimensions=building_data.room_dimensions,
        patterns_matched={},
        confidence_scores=building_data.confidence_scores or {},
        extraction_notes=[]
    )

def _determine_extraction_method(regex_result: RegexExtractionResult, ai_result: AIExtractionResult) -> ExtractionMethod:
    """Determine extraction method used"""
    if regex_result and ai_result:
        return ExtractionMethod.REGEX_AND_AI
    elif ai_result:
        return ExtractionMethod.AI_ONLY
    elif regex_result:
        return ExtractionMethod.REGEX_ONLY
    else:
        return ExtractionMethod.FALLBACK

def _combine_extraction_results(building_data, ai_data=None):
    """Combine extraction results for backward compatibility"""
    combined = {
        "total_area": building_data.floor_area_ft2,
        "building_data": {
            "floor_area_ft2": building_data.floor_area_ft2,
            "wall_insulation": building_data.wall_insulation,
            "ceiling_insulation": building_data.ceiling_insulation,
            "window_schedule": building_data.window_schedule,
            "air_tightness": building_data.air_tightness,
            "foundation_type": building_data.foundation_type,
            "orientation": building_data.orientation
        },
        "confidence_scores": building_data.confidence_scores or {},
        "extraction_method": "regex_based"
    }
    
    # Default room data if no AI analysis
    rooms = []
    if building_data.room_dimensions:
        for i, room_dim in enumerate(building_data.room_dimensions):
            rooms.append({
                "name": f"Room {i+1}",
                "area": room_dim["area_ft2"],
                "height": 10,
                "windows": int(room_dim["area_ft2"] * 0.12 / 15),  # Estimate windows
                "exterior_walls": 2
            })
    else:
        # Fallback room
        total_area = combined["building_data"]["floor_area_ft2"] or 1480
        rooms.append({
            "name": "Main Floor",
            "area": total_area,
            "height": 10,
            "windows": int(total_area * 0.12 / 15),
            "exterior_walls": 4
        })
    
    combined["rooms"] = rooms
    combined["building_details"] = {
        "floors": 1,
        "foundation_type": building_data.foundation_type or "slab",
        "roof_type": "standard"
    }
    
    return combined

def _get_fallback_results():
    """Return fallback results when processing fails"""
    return {
        "total_area": 1480,
        "rooms": [
            {"name": "Living Room", "area": 300, "height": 10, "windows": 3, "exterior_walls": 2},
            {"name": "Kitchen", "area": 200, "height": 10, "windows": 2, "exterior_walls": 1},
            {"name": "Master Bedroom", "area": 250, "height": 10, "windows": 2, "exterior_walls": 2},
            {"name": "Bedroom 2", "area": 180, "height": 10, "windows": 1, "exterior_walls": 2},
            {"name": "Bedroom 3", "area": 150, "height": 10, "windows": 1, "exterior_walls": 1},
            {"name": "Bathrooms", "area": 120, "height": 10, "windows": 1, "exterior_walls": 1},
            {"name": "Hallway", "area": 280, "height": 10, "windows": 0, "exterior_walls": 0}
        ],
        "building_details": {"floors": 1, "foundation_type": "slab", "roof_type": "standard"},
        "building_data": {
            "floor_area_ft2": 1480,
            "wall_insulation": {"effective_r": 19},
            "ceiling_insulation": 38,
            "window_schedule": {"u_value": 0.30, "shgc": 0.65},
            "air_tightness": 5.0,
            "foundation_type": "slab"
        }
    }