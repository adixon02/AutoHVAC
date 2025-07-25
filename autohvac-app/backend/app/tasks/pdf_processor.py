"""
Async PDF Processor - Memory-Optimized Background Processing
Handles large PDF files with chunked processing and memory management
"""
import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import logging
import traceback

# Import existing services for PDF processing
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.blueprint_extractor import extract_building_data_from_pdf
from services.ai_blueprint_analyzer import AIBlueprintAnalyzer

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Memory-optimized PDF processor for large files"""
    
    def __init__(self):
        self.ai_analyzer = AIBlueprintAnalyzer()
    
    async def process_pdf_chunked(
        self, 
        file_path: str, 
        project_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process PDF in memory-efficient chunks
        """
        try:
            logger.info(f"Starting chunked PDF processing: {file_path}")
            
            # Step 1: Extract basic text data (memory-efficient)
            logger.info("Extracting text data from PDF...")
            text_data = await asyncio.to_thread(
                extract_building_data_from_pdf, 
                file_path
            )
            
            # Step 2: AI-enhanced analysis (if text extraction successful)
            if text_data and any(text_data.values()):
                logger.info("Running AI-enhanced analysis...")
                try:
                    ai_data = await asyncio.to_thread(
                        self.ai_analyzer.analyze_blueprint,
                        file_path,
                        project_info
                    )
                    
                    # Merge text and AI results
                    combined_result = {
                        "extraction_method": "combined",
                        "text_extraction": text_data,
                        "ai_analysis": ai_data,
                        "confidence": "high" if ai_data else "medium"
                    }
                    
                except Exception as ai_error:
                    logger.warning(f"AI analysis failed, using text extraction only: {ai_error}")
                    combined_result = {
                        "extraction_method": "text_only",
                        "text_extraction": text_data,
                        "ai_analysis": None,
                        "confidence": "medium"
                    }
            else:
                # Fallback to AI-only if text extraction failed
                logger.info("Text extraction failed, trying AI-only analysis...")
                try:
                    ai_data = await asyncio.to_thread(
                        self.ai_analyzer.analyze_blueprint,
                        file_path,
                        project_info
                    )
                    
                    combined_result = {
                        "extraction_method": "ai_only",
                        "text_extraction": None,
                        "ai_analysis": ai_data,
                        "confidence": "medium"
                    }
                    
                except Exception as ai_error:
                    logger.error(f"Both text and AI extraction failed: {ai_error}")
                    raise Exception("Failed to extract any data from PDF")
            
            # Step 3: Generate professional output format
            professional_result = self._format_professional_output(
                combined_result, 
                project_info
            )
            
            logger.info("PDF processing completed successfully")
            return professional_result
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _format_professional_output(
        self, 
        extraction_result: Dict[str, Any], 
        project_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format extraction results into professional output
        """
        try:
            # Get the best available data
            text_data = extraction_result.get("text_extraction", {})
            ai_data = extraction_result.get("ai_analysis", {})
            
            # Combine building data
            building_data = {}
            if text_data:
                building_data.update(text_data)
            if ai_data and isinstance(ai_data, dict):
                building_data.update(ai_data.get("building_data", {}))
            
            # Extract room data
            rooms = []
            if ai_data and "rooms" in ai_data:
                rooms = ai_data["rooms"]
            elif text_data and "rooms" in text_data:
                rooms = text_data["rooms"]
            
            # Create professional format
            result = {
                "project_info": project_info,
                "extraction_summary": {
                    "method": extraction_result["extraction_method"],
                    "confidence": extraction_result["confidence"],
                    "rooms_detected": len(rooms),
                    "building_data_extracted": bool(building_data)
                },
                "building_data": building_data,
                "rooms": rooms,
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "version": "2.0.0"
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to format professional output: {e}")
            return {
                "project_info": project_info,
                "extraction_summary": {
                    "method": "error",
                    "confidence": "none",
                    "error": str(e)
                },
                "building_data": {},
                "rooms": [],
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "version": "2.0.0"
                }
            }

# Global processor instance
pdf_processor = PDFProcessor()

async def process_pdf_async(
    job_id: str,
    file_path: str,
    project_info: Dict[str, Any],
    job_storage: Dict[str, Any]
):
    """
    Background task for processing PDF files
    Updates job storage with progress and results
    """
    try:
        logger.info(f"Starting background PDF processing for job {job_id}")
        
        # Update job status to processing
        job_storage[job_id].update({
            "status": "processing",
            "progress": 10,
            "message": "PDF processing started...",
            "updated_at": datetime.now().isoformat()
        })
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Update progress
        job_storage[job_id].update({
            "progress": 25,
            "message": "Analyzing PDF structure...",
            "updated_at": datetime.now().isoformat()
        })
        
        # Process PDF with memory optimization
        result = await pdf_processor.process_pdf_chunked(file_path, project_info)
        
        # Update progress
        job_storage[job_id].update({
            "progress": 90,
            "message": "Finalizing results...",
            "updated_at": datetime.now().isoformat()
        })
        
        # Store results
        job_storage[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "PDF processing completed successfully",
            "updated_at": datetime.now().isoformat(),
            "result": result
        })
        
        logger.info(f"Background processing completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for job {job_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Update job with error
        job_storage[job_id].update({
            "status": "error",
            "progress": 0,
            "message": f"Processing failed: {str(e)}",
            "updated_at": datetime.now().isoformat(),
            "error": str(e)
        })
        
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up file {file_path}: {cleanup_error}")