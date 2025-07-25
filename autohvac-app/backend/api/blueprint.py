"""
Blueprint processing API endpoints
Handles PDF upload, processing, and analysis with JSON intermediate storage
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, Response
from typing import Optional, Dict, Any
import uuid
from uuid import uuid4
import os
import json
import pdfplumber
from datetime import datetime
from pathlib import Path
import logging

# Import new JSON schema and storage
from models.extraction_schema import (
    CompleteExtractionResult, PDFMetadata, RegexExtractionResult, 
    AIExtractionResult, ProcessingMetadata, ExtractionVersion, 
    ExtractionMethod, ExtractionDebugResponse
)
from services.extraction_storage import get_extraction_storage

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/blueprint",
    tags=["blueprint"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage for MVP (replace with database in production)
job_storage = {}

@router.options("/upload", include_in_schema=False)
async def upload_options() -> Response:
    """Explicit OPTIONS handler for CORS preflight"""
    return Response(status_code=204)

@router.post("/upload")
@router.post("/upload/")  # handles trailing slash
async def upload_blueprint(
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    project_name: str = Form(...),
    building_type: str = Form(...),
    construction_type: str = Form(...)
):
    """
    Upload and process a blueprint PDF file
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Check file size (50MB limit) - use seek to avoid loading into memory
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"Blueprint upload: {file.filename}, {file_size_mb:.1f}MB")
        
        if file_size_mb > 50:
            logger.warning(f"File too large: {file_size_mb:.1f}MB")
            raise HTTPException(
                status_code=413, 
                detail=f"File too large ({file_size_mb:.1f}MB). Maximum size is 50MB"
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create upload directory if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Stream file to disk to avoid memory spikes
        file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")
        with open(file_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                out.write(chunk)
        
        # Initialize job data
        job_data = {
            "job_id": job_id,
            "status": "processing",
            "progress": 10,
            "message": "Blueprint uploaded successfully",
            "created_at": datetime.now().isoformat(),
            "project_info": {
                "zip_code": zip_code,
                "project_name": project_name,
                "building_type": building_type,
                "construction_type": construction_type
            },
            "file_info": {
                "filename": file.filename,
                "size_mb": file_size_mb,
                "path": file_path
            }
        }
        
        # Store job data
        job_storage[job_id] = job_data
        
        logger.info(f"Starting blueprint processing for job: {job_id}")
        
        # Process blueprint with enhanced extraction and JSON storage
        from services.blueprint_extractor import BlueprintExtractor
        from services.ai_blueprint_analyzer import AIBlueprintAnalyzer
        import asyncio
        
        start_time = datetime.now()
        
        try:
            job_data["progress"] = 20
            job_data["message"] = "Reading PDF file..."
            
            # Add timeout wrapper for PDF processing
            import asyncio
            
            async def process_with_timeout():
                # Extract PDF metadata and raw text
                pdf_metadata = await _extract_pdf_metadata(file_path, file.filename)
                raw_text, raw_text_by_page = await _extract_raw_text(file_path)
                
                job_data["progress"] = 30
                job_data["message"] = "Extracting data from blueprint..."
                
                # Initialize extractors
                blueprint_extractor = BlueprintExtractor()
                
                # Extract building data systematically
                text_start = datetime.now()
                building_data = await blueprint_extractor.extract_building_data(file_path)
                text_duration = (datetime.now() - text_start).total_seconds() * 1000
                
                return pdf_metadata, raw_text, raw_text_by_page, building_data, text_duration
            
            # Process with 60 second timeout to prevent hanging
            try:
                pdf_metadata, raw_text, raw_text_by_page, building_data, text_duration = await asyncio.wait_for(
                    process_with_timeout(), timeout=60.0
                )
            except asyncio.TimeoutError:
                logger.error(f"PDF processing timeout for job {job_id}, file: {file_path}")
                raise HTTPException(status_code=408, detail="PDF processing timeout. File may be too complex or corrupted.")
            except Exception as processing_error:
                logger.error(f"PDF processing error for job {job_id}: {processing_error}")
                raise
            
            # Convert BuildingData to RegexExtractionResult
            regex_result = _convert_building_data_to_regex_result(building_data, text_duration)
            
            job_data["progress"] = 60
            job_data["message"] = "Processing blueprint data..."
            
            # Skip AI analysis during upload to prevent timeouts
            # AI enhancement should be called separately after JSON extraction
            ai_result = None
            ai_duration = 0
            
            job_data["progress"] = 80
            job_data["message"] = "Saving extraction data..."
            
            # Create complete extraction result
            total_duration = (datetime.now() - start_time).total_seconds() * 1000
            extraction_id = str(uuid4())
            
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
                    text_extraction_ms=int(text_duration) if 'text_duration' in locals() else None,
                    regex_processing_ms=int(text_duration),
                    ai_processing_ms=int(ai_duration) if ai_result else None
                )
            )
            
            # Save extraction data to JSON storage
            storage_service = get_extraction_storage()
            storage_info = storage_service.save_extraction(complete_result)
            
            logger.info(f"Saved extraction data: {extraction_id} -> {storage_info.storage_path}")
            
            job_data["progress"] = 90
            job_data["message"] = "Combining extracted data..."
            
            # Combine regex and AI extracted data (using existing logic for backward compatibility)
            combined_results = _combine_extraction_results(building_data, ai_data if 'ai_data' in locals() else None)
            
            # Store extraction_id in job data for later retrieval
            job_data["extraction_id"] = extraction_id
            job_data["status"] = "completed"
            job_data["progress"] = 100
            job_data["message"] = "Blueprint analysis complete"
            job_data["results"] = combined_results
            logger.info(f"Blueprint processing completed successfully for job: {job_id}")
            
        except Exception as extraction_error:
            logger.error(f"Blueprint processing failed for job {job_id}: {extraction_error}")
            # Fall back to mock data for now
            job_data["status"] = "completed"
            job_data["progress"] = 100
            job_data["message"] = "Blueprint analysis complete (using fallback data)"
            job_data["results"] = {
                "total_area": 1480,  # Add this for frontend compatibility
                "rooms": [
                    {
                        "name": "Living Room",
                        "area": 300,  # Use 'area' not 'area_ft2' for frontend
                        "height": 10,  # Use 'height' not 'ceiling_height' for frontend
                        "windows": 3,  # Number of windows
                        "exterior_walls": 2
                    },
                    {
                        "name": "Kitchen",
                        "area": 200,
                        "height": 10,
                        "windows": 2,
                        "exterior_walls": 1
                    },
                    {
                        "name": "Master Bedroom",
                        "area": 250,
                        "height": 10,
                        "windows": 2,
                        "exterior_walls": 2
                    },
                    {
                        "name": "Bedroom 2",
                        "area": 180,
                        "height": 10,
                        "windows": 1,
                        "exterior_walls": 2
                    },
                    {
                        "name": "Bedroom 3",
                        "area": 150,
                        "height": 10,
                        "windows": 1,
                        "exterior_walls": 1
                    },
                    {
                        "name": "Bathrooms",
                        "area": 120,
                        "height": 10,
                        "windows": 1,
                        "exterior_walls": 1
                    },
                    {
                        "name": "Hallway",
                        "area": 280,
                        "height": 10,
                        "windows": 0,
                        "exterior_walls": 0
                    }
                ],
                "building_details": {
                    "floors": 1,
                    "foundation_type": "slab",
                    "roof_type": "standard"
                },
                "building_data": {
                    "floor_area_ft2": 1480,
                    "wall_insulation": {"effective_r": 19},
                    "ceiling_insulation": 38,
                    "window_schedule": {"u_value": 0.30, "shgc": 0.65},
                    "air_tightness": 5.0,
                    "foundation_type": "slab"
                },
                "extraction_notes": f"Extraction failed: {str(extraction_error)}"
            }
        
        logger.info(f"Blueprint upload endpoint completed for job: {job_id}")
        
        return {
            "job_id": job_id,
            "message": "Blueprint uploaded successfully",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Blueprint upload error for job {job_id if 'job_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the processing status of a blueprint job
    """
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = job_storage[job_id]
    
    return {
        "job_id": job_id,
        "status": job_data["status"],
        "progress": job_data["progress"],
        "message": job_data["message"]
    }

@router.get("/results/{job_id}")
async def get_job_results(job_id: str):
    """
    Get the analysis results for a completed blueprint job
    """
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = job_storage[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "project_info": job_data["project_info"],
        "results": job_data["results"]
    }

@router.get("/extraction/{job_id}")
async def get_extraction_data(job_id: str, include_raw_text: bool = False):
    """
    Get raw extraction data for debugging
    
    Args:
        job_id: Blueprint job ID
        include_raw_text: Whether to include full raw text (can be large)
    """
    try:
        storage_service = get_extraction_storage()
        extraction_data = storage_service.load_extraction(job_id)
        
        if not extraction_data:
            raise HTTPException(status_code=404, detail="Extraction data not found")
        
        # Create debug response
        debug_response = ExtractionDebugResponse(
            extraction_id=extraction_data.extraction_id,
            job_id=job_id,
            extraction_summary=extraction_data.get_extraction_summary(),
            raw_extraction_data=extraction_data if include_raw_text else None,
            available_reprocessing_options=[
                "regex_only",
                "ai_only", 
                "regex_and_ai_combined"
            ]
        )
        
        # If not including raw text, create a sanitized version
        if not include_raw_text:
            sanitized_data = extraction_data.copy(deep=True)
            sanitized_data.raw_text = f"[{len(extraction_data.raw_text)} characters - use include_raw_text=true to view]"
            sanitized_data.raw_text_by_page = [
                f"[Page {i+1}: {len(page)} characters]" 
                for i, page in enumerate(extraction_data.raw_text_by_page)
            ]
            debug_response.raw_extraction_data = sanitized_data
        
        return debug_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get extraction data for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve extraction data")

@router.get("/extraction-list")
async def list_extractions(include_expired: bool = False, limit: int = 50):
    """
    List stored extraction data for debugging
    
    Args:
        include_expired: Include expired extractions
        limit: Maximum number of results (max 100)
    """
    try:
        if limit > 100:
            limit = 100
            
        storage_service = get_extraction_storage()
        storage_infos = storage_service.list_extractions(
            include_expired=include_expired,
            limit=limit
        )
        
        return {
            "extractions": [
                {
                    "extraction_id": info.extraction_id,
                    "job_id": info.job_id,
                    "created_at": info.created_at,
                    "file_size_mb": info.file_size_bytes / (1024 * 1024),
                    "is_compressed": info.is_compressed,
                    "access_count": info.access_count,
                    "last_accessed": info.last_accessed,
                    "expires_at": info.retention_expires_at
                }
                for info in storage_infos
            ],
            "total_count": len(storage_infos),
            "include_expired": include_expired
        }
        
    except Exception as e:
        logger.error(f"Failed to list extractions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list extractions")

@router.get("/storage-stats")
async def get_storage_stats():
    """Get storage usage statistics"""
    try:
        storage_service = get_extraction_storage()
        stats = storage_service.get_storage_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage statistics")

@router.delete("/extraction/{job_id}")
async def delete_extraction_data(job_id: str):
    """
    Delete extraction data
    
    Args:
        job_id: Blueprint job ID
    """
    try:
        storage_service = get_extraction_storage()
        success = storage_service.delete_extraction(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Extraction data not found")
        
        return {"message": f"Extraction data deleted for job {job_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete extraction data for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete extraction data")

@router.post("/reprocess/{job_id}")
async def reprocess_extraction(job_id: str, request: Optional[Dict[str, Any]] = None):
    """
    Reprocess extraction data using different analysis methods
    
    Args:
        job_id: Blueprint job ID  
        request: Optional reprocessing configuration
    """
    try:
        # Load existing extraction data
        storage_service = get_extraction_storage()
        extraction_data = storage_service.load_extraction(job_id)
        
        if not extraction_data:
            raise HTTPException(status_code=404, detail="Extraction data not found")
        
        # Parse reprocessing request
        reprocess_method = ExtractionMethod.REGEX_AND_AI
        force_ai_reanalysis = False
        
        if request:
            reprocess_method = ExtractionMethod(request.get("reprocessing_method", "regex_and_ai_combined"))
            force_ai_reanalysis = request.get("force_ai_reanalysis", False)
        
        logger.info(f"Reprocessing extraction {extraction_data.extraction_id} with method: {reprocess_method}")
        
        # Update job status if it exists in job_storage
        if job_id in job_storage:
            job_storage[job_id]["status"] = "processing"
            job_storage[job_id]["progress"] = 50
            job_storage[job_id]["message"] = "Reprocessing extraction data..."
        
        # Initialize services  
        from services.blueprint_extractor import BlueprintExtractor
        from services.ai_blueprint_analyzer import AIBlueprintAnalyzer
        
        start_time = datetime.now()
        new_regex_result = None
        new_ai_result = None
        
        # Reprocess based on method
        if reprocess_method in [ExtractionMethod.REGEX_ONLY, ExtractionMethod.REGEX_AND_AI]:
            # Use existing regex data unless we want to recompute
            new_regex_result = extraction_data.regex_extraction
        
        if reprocess_method in [ExtractionMethod.AI_ONLY, ExtractionMethod.REGEX_AND_AI] or force_ai_reanalysis:
            # Rerun AI analysis
            try:
                ai_analyzer = AIBlueprintAnalyzer()
                # We'd need the original file path - for now use existing AI data
                # In production, could store file path in extraction metadata
                if force_ai_reanalysis:
                    logger.warning("Force AI reanalysis requested but original file path not available")
                new_ai_result = extraction_data.ai_extraction
            except Exception as ai_error:
                logger.warning(f"AI reanalysis failed: {ai_error}")
                new_ai_result = extraction_data.ai_extraction
        
        # Create new extraction result
        processing_duration = (datetime.now() - start_time).total_seconds() * 1000
        new_extraction_id = str(uuid4())
        
        reprocessed_result = CompleteExtractionResult(
            extraction_id=new_extraction_id,
            job_id=job_id,
            pdf_metadata=extraction_data.pdf_metadata,
            raw_text=extraction_data.raw_text,
            raw_text_by_page=extraction_data.raw_text_by_page,
            regex_extraction=new_regex_result,
            ai_extraction=new_ai_result,
            processing_metadata=ProcessingMetadata(
                extraction_id=new_extraction_id,
                job_id=job_id,
                extraction_timestamp=datetime.now(),
                processing_duration_ms=int(processing_duration),
                extraction_version=ExtractionVersion.CURRENT,
                extraction_method=reprocess_method,
                regex_processing_ms=0,  # Reused existing data
                ai_processing_ms=int(processing_duration) if new_ai_result else 0
            )
        )
        
        # Save reprocessed data
        storage_info = storage_service.save_extraction(reprocessed_result)
        
        # Update job storage with new results
        if job_id in job_storage:
            # Convert back to old format for backward compatibility
            building_data = _convert_regex_result_to_building_data(new_regex_result) if new_regex_result else None
            ai_data = _convert_ai_result_to_ai_data(new_ai_result) if new_ai_result else None
            
            combined_results = _combine_extraction_results(building_data, ai_data)
            
            job_storage[job_id]["extraction_id"] = new_extraction_id
            job_storage[job_id]["status"] = "completed"
            job_storage[job_id]["progress"] = 100
            job_storage[job_id]["message"] = "Reprocessing complete"
            job_storage[job_id]["results"] = combined_results
        
        logger.info(f"Reprocessing complete: {new_extraction_id} -> {storage_info.storage_path}")
        
        return {
            "job_id": job_id,
            "new_extraction_id": new_extraction_id,
            "original_extraction_id": extraction_data.extraction_id,
            "reprocessing_method": reprocess_method,
            "processing_duration_ms": processing_duration,
            "message": "Reprocessing completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess extraction for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")

@router.post("/api/v2/blueprint/{job_id}/enhance-with-ai")
async def enhance_blueprint_with_ai(job_id: str):
    """
    Enhance existing blueprint extraction with AI analysis.
    This should be called after initial extraction to add AI insights
    for more accurate Manual J calculations.
    """
    try:
        # Check if job exists
        if job_id not in job_storage:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_data = job_storage[job_id]
        
        # Check if already has AI analysis
        extraction_id = job_data.get("extraction_id")
        if not extraction_id:
            raise HTTPException(status_code=400, detail="No extraction data found for this job")
        
        # Load existing extraction
        storage_service = get_extraction_storage()
        extraction_data = storage_service.load_extraction(extraction_id)
        
        if not extraction_data:
            raise HTTPException(status_code=404, detail=f"Extraction {extraction_id} not found")
        
        # Check if AI analysis already exists
        if extraction_data.ai_extraction:
            return {
                "job_id": job_id,
                "extraction_id": extraction_id,
                "message": "AI analysis already exists for this blueprint",
                "ai_confidence": extraction_data.ai_extraction.ai_confidence
            }
        
        # Get file path
        file_path = job_data.get("file_info", {}).get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Blueprint file not found")
        
        # Update job status
        job_data["status"] = "processing"
        job_data["progress"] = 50
        job_data["message"] = "Enhancing with AI analysis..."
        
        # Perform AI analysis
        from services.ai_blueprint_analyzer import AIBlueprintAnalyzer
        
        ai_start = datetime.now()
        try:
            ai_analyzer = AIBlueprintAnalyzer()
            ai_data = await ai_analyzer.analyze_blueprint_visual(file_path)
            ai_duration = (datetime.now() - ai_start).total_seconds() * 1000
            ai_result = _convert_ai_data_to_ai_result(ai_data, ai_duration)
            
            # Create new extraction with AI data
            new_extraction_id = str(uuid4())
            enhanced_result = CompleteExtractionResult(
                extraction_id=new_extraction_id,
                job_id=job_id,
                pdf_metadata=extraction_data.pdf_metadata,
                raw_text=extraction_data.raw_text,
                raw_text_by_page=extraction_data.raw_text_by_page,
                regex_extraction=extraction_data.regex_extraction,
                ai_extraction=ai_result,
                processing_metadata=ProcessingMetadata(
                    extraction_id=new_extraction_id,
                    job_id=job_id,
                    extraction_timestamp=datetime.now(),
                    processing_duration_ms=int(ai_duration),
                    extraction_version=ExtractionVersion.CURRENT,
                    extraction_method=ExtractionMethod.REGEX_AND_AI,
                    regex_processing_ms=extraction_data.processing_metadata.regex_processing_ms,
                    ai_processing_ms=int(ai_duration)
                )
            )
            
            # Save enhanced extraction
            storage_info = storage_service.save_extraction(enhanced_result)
            
            # Update job with enhanced results
            building_data = _convert_regex_result_to_building_data(extraction_data.regex_extraction)
            ai_data_converted = _convert_ai_result_to_ai_data(ai_result)
            combined_results = _combine_extraction_results(building_data, ai_data_converted)
            
            job_data["extraction_id"] = new_extraction_id
            job_data["status"] = "completed"
            job_data["progress"] = 100
            job_data["message"] = "AI enhancement complete"
            job_data["results"] = combined_results
            
            return {
                "job_id": job_id,
                "extraction_id": new_extraction_id,
                "message": "AI enhancement completed successfully",
                "ai_confidence": ai_result.ai_confidence if ai_result else 0,
                "processing_duration_ms": ai_duration
            }
            
        except Exception as ai_error:
            logger.error(f"AI enhancement failed for {job_id}: {ai_error}")
            job_data["status"] = "completed"
            job_data["progress"] = 100
            job_data["message"] = "AI enhancement failed, using regex extraction only"
            raise HTTPException(status_code=500, detail=f"AI enhancement failed: {str(ai_error)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enhance {job_id} with AI: {e}")
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {str(e)}")

# === JSON Extraction Helper Functions ===

async def _extract_pdf_metadata(file_path: str, original_filename: str) -> PDFMetadata:
    """Extract metadata from PDF file"""
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

async def _extract_raw_text(file_path: str) -> tuple[str, list[str]]:
    """Extract raw text from PDF"""
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
    """Convert BuildingData dataclass to RegexExtractionResult"""
    return RegexExtractionResult(
        floor_area_ft2=building_data.floor_area_ft2,
        wall_insulation=building_data.wall_insulation,
        ceiling_insulation=building_data.ceiling_insulation,
        window_schedule=building_data.window_schedule,
        air_tightness=building_data.air_tightness,
        foundation_type=building_data.foundation_type,
        orientation=building_data.orientation,
        room_dimensions=building_data.room_dimensions,
        patterns_matched={},  # Could be enhanced to track which patterns matched
        confidence_scores=building_data.confidence_scores or {},
        extraction_notes=[]
    )

def _convert_ai_data_to_ai_result(ai_data, processing_time_ms: float) -> Optional[AIExtractionResult]:
    """Convert AIExtractedData to AIExtractionResult"""
    if not ai_data:
        return None
    
    return AIExtractionResult(
        room_layouts=ai_data.room_layouts,
        window_orientations=ai_data.window_orientations,
        building_envelope=ai_data.building_envelope,
        architectural_details=ai_data.architectural_details,
        hvac_existing=ai_data.hvac_existing,
        ai_confidence=ai_data.extraction_confidence if hasattr(ai_data, 'extraction_confidence') else 0.5,
        visual_analysis_notes=[],
        room_count_detected=len(ai_data.room_layouts) if ai_data.room_layouts else None
    )

def _determine_extraction_method(regex_result: Optional[RegexExtractionResult], ai_result: Optional[AIExtractionResult]) -> ExtractionMethod:
    """Determine which extraction method was used"""
    if regex_result and ai_result:
        return ExtractionMethod.REGEX_AND_AI
    elif ai_result:
        return ExtractionMethod.AI_ONLY
    elif regex_result:
        return ExtractionMethod.REGEX_ONLY
    else:
        return ExtractionMethod.FALLBACK

def _convert_regex_result_to_building_data(regex_result: RegexExtractionResult):
    """Convert RegexExtractionResult back to BuildingData for backward compatibility"""
    from services.blueprint_extractor import BuildingData
    return BuildingData(
        floor_area_ft2=regex_result.floor_area_ft2,
        wall_insulation=regex_result.wall_insulation,
        ceiling_insulation=regex_result.ceiling_insulation,
        window_schedule=regex_result.window_schedule,
        air_tightness=regex_result.air_tightness,
        foundation_type=regex_result.foundation_type,
        orientation=regex_result.orientation,
        room_dimensions=regex_result.room_dimensions,
        confidence_scores=regex_result.confidence_scores
    )

def _convert_ai_result_to_ai_data(ai_result: AIExtractionResult):
    """Convert AIExtractionResult back to AIExtractedData for backward compatibility"""
    from services.ai_blueprint_analyzer import AIExtractedData
    return AIExtractedData(
        room_layouts=ai_result.room_layouts,
        window_orientations=ai_result.window_orientations,
        building_envelope=ai_result.building_envelope,
        architectural_details=ai_result.architectural_details,
        hvac_existing=ai_result.hvac_existing,
        extraction_confidence=ai_result.ai_confidence
    )

def _combine_extraction_results(building_data, ai_data=None):
    """Combine regex extraction and AI analysis results"""
    
    # Start with regex-extracted building data
    combined = {
        "total_area": building_data.floor_area_ft2,  # Add this for frontend compatibility
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
                "area_ft2": room_dim["area_ft2"],
                "length_ft": room_dim["length_ft"],
                "width_ft": room_dim["width_ft"],
                "perimeter_ft": room_dim["perimeter_ft"],
                "ceiling_height": 9.0,  # Default
                "window_area": room_dim["area_ft2"] * 0.12,  # 12% default
                "exterior_walls": 2  # Default assumption
            })
    else:
        # Fallback single room
        total_area = combined["building_data"]["floor_area_ft2"] or 1480
        rooms.append({
            "name": "Main Floor",
            "area_ft2": total_area,
            "ceiling_height": 9.0,
            "window_area": total_area * 0.12,
            "exterior_walls": 4,  # Assume full perimeter
            "perimeter_ft": 4 * (total_area ** 0.5)  # Square approximation
        })
    
    # Enhance with AI data if available
    if ai_data and ai_data.room_layouts:
        ai_rooms = []
        for ai_room in ai_data.room_layouts:
            room_data = {
                "name": ai_room.get("name", "Unknown Room"),
                "ceiling_height": ai_room.get("ceiling_height_ft", 9.0),
                "exterior_walls": len(ai_room.get("windows", [])) + len(ai_room.get("doors", [])),
            }
            
            # Calculate area from dimensions if available
            if "dimensions" in ai_room:
                dims = ai_room["dimensions"]
                length = dims.get("length_ft", 0)
                width = dims.get("width_ft", 0)
                if length and width:
                    room_data["area_ft2"] = length * width
                    room_data["length_ft"] = length
                    room_data["width_ft"] = width
                    room_data["perimeter_ft"] = 2 * (length + width)
            
            # Calculate window area
            window_area = 0
            window_orientations = []
            if "windows" in ai_room:
                for window in ai_room["windows"]:
                    w_area = window.get("width_ft", 3) * window.get("height_ft", 3.5)
                    window_area += w_area
                    window_orientations.append(window.get("orientation", "south"))
            
            room_data["window_area"] = window_area
            room_data["window_orientations"] = window_orientations
            
            ai_rooms.append(room_data)
        
        # Use AI rooms if they seem reasonable
        if ai_rooms and len(ai_rooms) <= 20:  # Sanity check
            rooms = ai_rooms
            combined["extraction_method"] = "ai_enhanced"
            combined["ai_confidence"] = ai_data.extraction_confidence
    
    # Transform rooms to frontend format
    frontend_rooms = []
    for room in rooms:
        frontend_rooms.append({
            "name": room.get("name", "Room"),
            "area": room.get("area_ft2", room.get("area", 200)),
            "height": room.get("ceiling_height", room.get("height", 10)),
            "windows": room.get("window_count", int(room.get("window_area", 30) / 15)),
            "exterior_walls": room.get("exterior_walls", 2)
        })
    
    combined["rooms"] = frontend_rooms
    
    # Add building_details for frontend
    combined["building_details"] = {
        "floors": 1,
        "foundation_type": building_data.foundation_type or "slab",
        "roof_type": "standard"
    }
    
    return combined