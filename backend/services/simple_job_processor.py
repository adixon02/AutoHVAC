"""
Simple in-memory job processor for development without Celery/Redis
"""
import threading
import time
import asyncio
from typing import Dict, Any
from services.job_service import job_service
from services.rate_limiter import rate_limiter
from services.pdf_service import pdf_service
from services.manualj import calculate_manualj
from app.parser.schema import BlueprintSchema, Room
from database import AsyncSessionLocal
import uuid
import logging

logger = logging.getLogger(__name__)

async def process_job_sync(project_id: str, file_content: bytes, filename: str, email: str = "", zip_code: str = "90210"):
    """Process a job synchronously (for development without Celery)"""
    try:
        logger.info(f"{project_id} – starting job processing (file={filename}, size={len(file_content)}, email={email})")
        async with AsyncSessionLocal() as session:
            try:
                logger.debug(f"{project_id} – starting set_project_processing")
                # Update job status
                await job_service.set_project_processing(project_id, session)
                logger.debug(f"{project_id} – finished set_project_processing")
                
                logger.debug(f"{project_id} – starting blueprint parsing simulation")
                # Simulate blueprint parsing time
                await asyncio.sleep(1)
                logger.debug(f"{project_id} – finished blueprint parsing simulation")
                
                # Check if assumptions are already collected (new multi-step flow)
                project = await job_service.get_project(project_id, session)
                if not project:
                    raise Exception("Project not found")
                
                if not project.assumptions_collected:
                    # Legacy flow - wait for assumptions modal
                    logger.debug(f"{project_id} – waiting for assumptions (legacy flow)")
                    assumptions_received = await job_service.wait_for_assumptions(project_id, timeout=900.0)
                    
                    if not assumptions_received:
                        logger.warning(f"{project_id} – timeout waiting for assumptions")
                        await job_service.set_project_failed(project_id, "Timeout waiting for user assumptions", session)
                        await rate_limiter.decrement_active_jobs(email, project_id)
                        return
                    
                    logger.debug(f"{project_id} – assumptions received, continuing processing")
                else:
                    # New multi-step flow - assumptions already collected
                    logger.debug(f"{project_id} – assumptions already collected in multi-step flow")
                # Simulate additional processing time
                await asyncio.sleep(1)
                logger.debug(f"{project_id} – finished final processing")
                
            except Exception as e:
                logger.exception(f"{project_id} – error in job processing setup: {e}")
                await job_service.set_project_failed(project_id, str(e), session)
                await rate_limiter.decrement_active_jobs(email, project_id)
                return
            
            # Get the updated project with assumptions
            project = await job_service.get_project(project_id, session)
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
                    "file_size": len(file_content),
                    "timestamp": time.time()
                }
            }
            
            try:
                logger.debug(f"{project_id} – starting get_project")
                # Get project details for PDF generation
                project = await job_service.get_project(project_id, session)
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
                    
                    # Update job with result and PDF path
                    await job_service.set_project_completed(project_id, result, pdf_path, session)
                    logger.info(f"{project_id} – SUCCESS: Job completed with PDF report: {pdf_path}")
                    logger.debug(f"{project_id} – finished PDF generation")
                    
                except Exception as pdf_error:
                    logger.exception(f"{project_id} – error in PDF generation: {pdf_error}")
                    # Still mark as completed but without PDF
                    await job_service.set_project_completed(project_id, result, session=session)
                    logger.info(f"{project_id} – SUCCESS: Job completed without PDF due to PDF generation error")
                
                logger.debug(f"{project_id} – starting rate limiter decrement")
                # Release rate limiter
                await rate_limiter.decrement_active_jobs(email, project_id)
                logger.debug(f"{project_id} – finished rate limiter decrement")
                
            except Exception as e:
                logger.exception(f"{project_id} – error in job completion: {e}")
                await job_service.set_project_failed(project_id, str(e), session)
                await rate_limiter.decrement_active_jobs(email, project_id)
                return
        
    except Exception as e:
        logger.exception(f"{project_id} – fatal error in process_job_sync: {e}")
        async with AsyncSessionLocal() as session:
            await job_service.set_project_failed(project_id, str(e), session)
            await rate_limiter.decrement_active_jobs(email, project_id)

def process_job_async(project_id: str, file_content: bytes, filename: str, email: str = "", zip_code: str = "90210"):
    """Process a job in a background thread (for development without Celery)"""
    def run_async_job():
        # Create new event loop for the thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_job_sync(project_id, file_content, filename, email, zip_code)
            )
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_async_job)
    thread.daemon = True
    thread.start()