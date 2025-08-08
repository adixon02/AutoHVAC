"""
Simplified Blueprint Parser - Clean, single flow pipeline
No complex modes, just straightforward processing
"""

import logging
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

from services.pipeline_orchestrator import pipeline_orchestrator
from services.pipeline_context import pipeline_context
from services.metrics_collector import metrics_collector
from services.error_types import NeedsInputError

logger = logging.getLogger(__name__)


class SimplifiedBlueprintParser:
    """
    Simplified blueprint parser with one clear processing flow
    No modes, no complex branching, just clean stage execution
    """
    
    def __init__(self):
        """Initialize the simplified parser"""
        self.orchestrator = pipeline_orchestrator
        
    def parse_blueprint(
        self,
        pdf_path: str,
        zip_code: str,
        project_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse a blueprint PDF with simplified, deterministic flow
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Building location ZIP code
            project_id: Unique project identifier
            filename: Original filename (optional)
            
        Returns:
            Dict with parsing results in standard format
        """
        start_time = time.time()
        
        if not filename:
            filename = Path(pdf_path).name
        
        logger.info(f"Starting simplified blueprint parsing for {filename}")
        logger.info(f"PDF: {pdf_path}, ZIP: {zip_code}, Project: {project_id}")
        
        try:
            # Check for scale override
            scale_override = os.getenv("SCALE_OVERRIDE")
            if scale_override:
                try:
                    override_value = float(scale_override)
                    pipeline_context.set_scale(override_value, source="environment_override")
                    logger.info(f"Using scale override: {override_value} px/ft")
                except ValueError:
                    logger.warning(f"Invalid SCALE_OVERRIDE value: {scale_override}")
            
            # Run the clean pipeline
            result = self.orchestrator.run_pipeline(
                pdf_path=pdf_path,
                zip_code=zip_code,
                project_id=project_id,
                filename=filename
            )
            
            # Convert to standard output format
            output = self._format_output(result)
            
            processing_time = time.time() - start_time
            logger.info(f"Blueprint parsing completed in {processing_time:.2f}s")
            logger.info(f"Results: {output['num_rooms']} rooms, {output['total_area']:.0f} sqft")
            
            return output
            
        except NeedsInputError as e:
            # User input required - return error details
            logger.warning(f"User input required: {e.message}")
            return {
                "success": False,
                "error_type": "needs_input",
                "error_message": e.message,
                "input_type": e.input_type,
                "details": e.details,
                "processing_time": time.time() - start_time
            }
            
        except Exception as e:
            # Unexpected error
            logger.error(f"Blueprint parsing failed: {e}")
            return {
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _format_output(self, result) -> Dict[str, Any]:
        """
        Format pipeline result to standard output format
        
        Args:
            result: PipelineResult from orchestrator
            
        Returns:
            Dict in standard format for API response
        """
        # Build rooms list
        rooms = []
        for room_geom, room_sem, room_load in zip(
            result.geometry_extraction.rooms,
            result.semantic_analysis.room_semantics,
            result.load_calculation.room_loads
        ):
            rooms.append({
                "id": room_geom.id,
                "name": room_sem.name,
                "type": room_sem.room_type,
                "area": room_geom.area_sqft,
                "width": room_geom.bounding_box[2] - room_geom.bounding_box[0],
                "height": room_geom.bounding_box[3] - room_geom.bounding_box[1],
                "windows": room_sem.windows_count,
                "doors": room_sem.doors_count,
                "exterior_walls": room_sem.exterior_walls,
                "loads": {
                    "heating_total": room_load.heating_btu_hr,
                    "cooling_total": room_load.cooling_btu_hr,
                    "heating_components": room_load.heating_components,
                    "cooling_components": room_load.cooling_components
                }
            })
        
        # Build output
        return {
            "success": True,
            "project_id": result.project_id,
            "filename": result.filename,
            "zip_code": result.zip_code,
            
            # Summary metrics
            "total_area": result.total_area_sqft,
            "num_rooms": result.num_rooms,
            "num_floors": result.geometry_extraction.num_floors,
            
            # Detailed data
            "rooms": rooms,
            
            # Building envelope
            "envelope": {
                "wall_r_value": result.semantic_analysis.building_envelope.wall_r_value,
                "ceiling_r_value": result.semantic_analysis.building_envelope.ceiling_r_value,
                "floor_r_value": result.semantic_analysis.building_envelope.floor_r_value,
                "window_u_value": result.semantic_analysis.building_envelope.window_u_value,
                "door_u_value": result.semantic_analysis.building_envelope.door_u_value,
                "air_changes_per_hour": result.semantic_analysis.building_envelope.air_changes_per_hour,
                "foundation_type": result.semantic_analysis.building_envelope.foundation_type
            },
            
            # Climate data
            "climate": {
                "zone": result.semantic_analysis.climate_zone,
                "design_temps": result.load_calculation.design_temperatures
            },
            
            # HVAC totals
            "hvac_summary": {
                "total_heating_btu_hr": result.load_calculation.total_heating_btu_hr,
                "total_cooling_btu_hr": result.load_calculation.total_cooling_btu_hr,
                "heating_system_tons": result.load_calculation.heating_system_tons,
                "cooling_system_tons": result.load_calculation.cooling_system_tons,
                "calculation_method": result.load_calculation.calculation_method,
                "safety_factor": result.load_calculation.safety_factor
            },
            
            # Metadata
            "metadata": {
                "page_used": result.page_classification.selected_page + 1,
                "scale_detected": result.scale_detection.scale_notation,
                "scale_px_per_ft": result.scale_detection.pixels_per_foot,
                "confidence_score": result.overall_confidence,
                "processing_time": result.processing_time_seconds,
                "pipeline_version": result.pipeline_version,
                "warnings": result.warnings
            },
            
            # Stage details (for debugging)
            "stage_details": {
                "page_classification": {
                    "page_scores": result.page_classification.page_scores,
                    "confidence": result.page_classification.confidence
                },
                "scale_detection": {
                    "method": result.scale_detection.detection_method,
                    "confidence": result.scale_detection.confidence
                },
                "geometry_extraction": {
                    "method": result.geometry_extraction.extraction_method,
                    "confidence": result.geometry_extraction.confidence
                },
                "semantic_analysis": {
                    "method": result.semantic_analysis.analysis_method,
                    "confidence": result.semantic_analysis.confidence
                }
            }
        }


# Global instance
simplified_parser = SimplifiedBlueprintParser()