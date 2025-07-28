"""
Elite blueprint parsing orchestrator
Coordinates geometry parsing, text extraction, AI cleanup, and Manual J calculations
"""

from celery import Celery
import time
import io
import os
import tempfile
import asyncio
from typing import Dict, Any

from services.store import job_store
from services.manualj import calculate_manualj
from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser
from app.parser.ai_cleanup import cleanup, AICleanupError

celery_app = Celery(
    'autohvac',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)


@celery_app.task
def process_blueprint(job_id: str, file_content: bytes, filename: str, email: str = "", zip_code: str = "90210"):
    """
    Elite PDF-to-HVAC processing pipeline
    
    Steps:
    1. Save PDF to temporary file
    2. Extract geometry using GeometryParser
    3. Extract text using TextParser  
    4. Clean and structure data with AI
    5. Calculate Manual J loads
    6. Store complete results
    """
    try:
        job_store.update_job(job_id, {
            "status": "processing",
            "stage": "initializing",
            "progress": 0
        })
        
        # Save PDF to temporary file for parsing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            # Stage 1: Extract geometry
            job_store.update_job(job_id, {
                "stage": "extracting_geometry",
                "progress": 20
            })
            
            try:
                print(f"DEBUG: {job_id} – starting geometry extraction")
                geometry_parser = GeometryParser()
                raw_geometry = geometry_parser.parse(temp_path)
                print(f"DEBUG: {job_id} – finished geometry extraction")
            except Exception as e:
                print(f"DEBUG: {job_id} – error in extracting_geometry: {e}")
                # REMOVE in production - debug stub to progress past geometry stage
                if os.getenv("DEBUG") == "true":
                    job_store.update_job(job_id, {
                        "status": "completed",
                        "stage": "complete",
                        "progress": 100,
                        "result": {"note": "DEBUG stub – pipeline short-circuited after geometry error"}
                    })
                    return
                raise
            
            # Stage 2: Extract text
            job_store.update_job(job_id, {
                "stage": "extracting_text", 
                "progress": 40
            })
            
            try:
                print(f"DEBUG: {job_id} – starting text extraction")
                text_parser = TextParser()
                raw_text = text_parser.parse(temp_path)
                print(f"DEBUG: {job_id} – finished text extraction")
            except Exception as e:
                print(f"DEBUG: {job_id} – error in extracting_text: {e}")
                # REMOVE in production - debug stub to progress past text stage
                if os.getenv("DEBUG") == "true":
                    job_store.update_job(job_id, {
                        "status": "completed",
                        "stage": "complete",
                        "progress": 100,
                        "result": {"note": "DEBUG stub – pipeline short-circuited after text error"}
                    })
                    return
                raise
            
            # Stage 3: AI cleanup and structuring
            job_store.update_job(job_id, {
                "stage": "ai_processing",
                "progress": 60
            })
            
            try:
                print(f"DEBUG: {job_id} – starting AI processing")
                # Run AI cleanup asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    blueprint_schema = loop.run_until_complete(
                        cleanup(raw_geometry, raw_text)
                    )
                finally:
                    loop.close()
                print(f"DEBUG: {job_id} – finished AI processing")
            except Exception as e:
                print(f"DEBUG: {job_id} – error in ai_processing: {e}")
                # REMOVE in production - debug stub to progress past AI stage
                if os.getenv("DEBUG") == "true":
                    job_store.update_job(job_id, {
                        "status": "completed",
                        "stage": "complete",
                        "progress": 100,
                        "result": {"note": "DEBUG stub – pipeline short-circuited after AI error"}
                    })
                    return
                raise
            
            # Stage 4: Manual J calculations
            job_store.update_job(job_id, {
                "stage": "calculating_loads",
                "progress": 80
            })
            
            try:
                print(f"DEBUG: {job_id} – starting Manual J calculations")
                hvac_loads = calculate_manualj(blueprint_schema)
                print(f"DEBUG: {job_id} – finished Manual J calculations")
            except Exception as e:
                print(f"DEBUG: {job_id} – error in calculating_loads: {e}")
                # REMOVE in production - debug stub to progress past calculations
                if os.getenv("DEBUG") == "true":
                    job_store.update_job(job_id, {
                        "status": "completed",
                        "stage": "complete",
                        "progress": 100,
                        "result": {"note": "DEBUG stub – pipeline short-circuited after calculations error"}
                    })
                    return
                raise
            
            # Stage 5: Finalize results
            job_store.update_job(job_id, {
                "stage": "finalizing",
                "progress": 95
            })
            
            print(f"DEBUG: {job_id} – starting finalization")
            
            # Compile complete result
            result = {
                "job_id": job_id,
                "filename": filename,
                "email": email,
                "processed_at": time.time(),
                "blueprint": blueprint_schema.dict(),
                "hvac_analysis": hvac_loads,
                "raw_data": {
                    "geometry_summary": {
                        "lines_found": len(raw_geometry.lines),
                        "rectangles_found": len(raw_geometry.rectangles),
                        "polylines_found": len(raw_geometry.polylines),
                        "page_size": [raw_geometry.page_width, raw_geometry.page_height],
                        "scale_detected": raw_geometry.scale_factor
                    },
                    "text_summary": {
                        "words_found": len(raw_text.words),
                        "room_labels_found": len(raw_text.room_labels),
                        "dimensions_found": len(raw_text.dimensions),
                        "notes_found": len(raw_text.notes)
                    }
                },
                "processing_stats": {
                    "total_rooms": len(blueprint_schema.rooms),
                    "total_sqft": blueprint_schema.sqft_total,
                    "stories": blueprint_schema.stories,
                    "climate_zone": hvac_loads.get("climate_zone", "unknown"),
                    "recommended_equipment": hvac_loads.get("equipment_recommendations", {}).get("system_type", "unknown")
                }
            }
            
            # Store final result
            job_store.update_job(job_id, {
                "status": "completed",
                "stage": "complete",
                "progress": 100,
                "result": result
            })
            print(f"DEBUG: {job_id} – finished finalization")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except AICleanupError as e:
        # AI-specific error handling
        job_store.update_job(job_id, {
            "status": "failed",
            "error": f"AI processing failed: {str(e)}",
            "error_type": "ai_cleanup_error",
            "stage": "ai_processing"
        })
        
    except Exception as e:
        # General error handling
        error_msg = str(e)
        error_type = type(e).__name__
        current_stage = job_store.get_job(job_id, {}).get("stage", "unknown")
        
        print(f"DEBUG: {job_id} – fatal error in {current_stage}: {error_type}: {error_msg}")
        
        job_store.update_job(job_id, {
            "status": "failed", 
            "error": error_msg,
            "error_type": error_type,
            "stage": current_stage
        })


@celery_app.task
def health_check():
    """Health check task for monitoring"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


# Legacy task for backward compatibility
@celery_app.task  
def process_blueprint_legacy(job_id: str, file_content: bytes, filename: str):
    """Legacy processing for backward compatibility"""
    try:
        job_store.update_job(job_id, {"status": "processing"})
        
        rooms = []
        
        if filename.lower().endswith('.pdf'):
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    words = first_page.extract_words()
                    
                    for word in words:
                        if "Room" in word['text']:
                            rooms.append({
                                "name": word['text'],
                                "x0": word['x0'],
                                "top": word['top'],
                                "area": 144.0  # Default room size
                            })
        
        # Use legacy load calculation
        from services.manualj import calculate_loads
        loads = calculate_loads(rooms)
        
        result = {
            "job_id": job_id,
            "parsed_at": time.time(),
            "rooms": rooms,
            "loads": loads
        }
        
        job_store.update_job(job_id, {
            "status": "completed",
            "result": result
        })
        
    except Exception as e:
        job_store.update_job(job_id, {
            "status": "failed",
            "error": str(e)
        })