"""
Blueprint Pipeline - Orchestrates the entire blueprint parsing workflow
Coordinates PDF processing, vision parsing, and HVAC calculations
"""

import logging
import time
from typing import Dict, Any, Optional, List
from uuid import uuid4

from services.vision_config import vision_config
from services.pdf_to_images import pdf_converter, PageImage
from services.vision_parse import vision_parser
from services.hvac_calculator import hvac_calculator
from services.takeoff_schema import BlueprintTakeoff

logger = logging.getLogger(__name__)


class BlueprintPipeline:
    """
    Orchestrates the complete blueprint analysis pipeline
    Handles the flow from PDF input to HVAC calculations
    """
    
    def __init__(self):
        """Initialize pipeline components"""
        self.pdf_converter = pdf_converter
        self.vision_parser = vision_parser
        self.hvac_calculator = hvac_calculator
        
        # Validate configuration
        vision_config.validate()
        
    def process_blueprint(
        self,
        pdf_path: str,
        zip_code: str,
        project_id: Optional[str] = None,
        filename: Optional[str] = None,
        specific_pages: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Process a blueprint PDF through the complete pipeline
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Project location ZIP code
            project_id: Optional project ID (generated if not provided)
            filename: Optional filename (extracted from path if not provided)
            specific_pages: Optional list of specific page numbers to analyze
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        # Generate project ID if not provided
        if not project_id:
            project_id = str(uuid4())
        
        # Extract filename if not provided
        if not filename:
            import os
            filename = os.path.basename(pdf_path)
        
        logger.info(f"Starting blueprint pipeline for {filename} (ZIP: {zip_code})")
        
        try:
            # Step 1: Convert PDF to images
            logger.info("Step 1: Converting PDF to images")
            if specific_pages:
                page_images = self.pdf_converter.convert_specific_pages(
                    pdf_path=pdf_path,
                    page_numbers=specific_pages
                )
            else:
                page_images = self.pdf_converter.convert_all_pages(pdf_path=pdf_path)
            
            if not page_images:
                raise ValueError("No pages could be converted from PDF")
            
            logger.info(f"Converted {len(page_images)} pages to images")
            
            # Step 2: Identify floor plan pages (if not specified)
            if not specific_pages and vision_config.auto_detect_floor_plans:
                logger.info("Step 2: Identifying floor plan pages")
                floor_plan_pages = self.pdf_converter.identify_floor_plan_pages(page_images)
                
                # Filter to floor plan pages only
                page_images = [p for p in page_images if p.page_num in floor_plan_pages]
                logger.info(f"Identified {len(page_images)} floor plan pages")
            
            # Step 3: Parse with GPT-5 Vision
            logger.info("Step 3: Parsing blueprint with GPT-5 Vision")
            takeoff = self.vision_parser.parse_blueprint(
                page_images=page_images,
                zip_code=zip_code,
                project_id=project_id,
                filename=filename
            )
            
            # Step 4: Calculate HVAC loads
            logger.info("Step 4: Calculating HVAC loads")
            takeoff = self.hvac_calculator.calculate_loads(takeoff)
            
            # Calculate total processing time
            total_time = time.time() - start_time
            takeoff.processing_time_seconds = total_time
            
            logger.info(f"Pipeline complete in {total_time:.2f}s")
            logger.info(f"Results: {takeoff.num_rooms} rooms, {takeoff.total_area_sqft:.0f} sq ft")
            
            if takeoff.has_hvac_loads:
                logger.info(
                    f"HVAC: {takeoff.hvac_loads.heating_system_tons:.1f} tons heating, "
                    f"{takeoff.hvac_loads.cooling_system_tons:.1f} tons cooling"
                )
            
            # Return success response
            return self._format_response(takeoff, success=True)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            
            # Return error response
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id,
                "processing_time": time.time() - start_time
            }
    
    def _format_response(self, takeoff: BlueprintTakeoff, success: bool = True) -> Dict[str, Any]:
        """
        Format takeoff data for API response
        
        Args:
            takeoff: BlueprintTakeoff object
            success: Whether processing was successful
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "success": success,
            "project_id": takeoff.project_id,
            "total_area": takeoff.total_area_sqft,
            "num_rooms": takeoff.num_rooms,
            "confidence": takeoff.confidence_score,
            "processing_time": takeoff.processing_time_seconds,
            "model_used": takeoff.model_used,
            
            # Room data
            "rooms": [
                {
                    "id": room.id,
                    "name": room.name,
                    "type": room.room_type.value,
                    "area": room.area_sqft,
                    "width": room.width_ft,
                    "length": room.length_ft,
                    "heating_btu_hr": room.heating_btu_hr,
                    "cooling_btu_hr": room.cooling_btu_hr,
                    "confidence": room.confidence,
                    "source": room.source.value
                }
                for room in takeoff.rooms
            ],
            
            # Building envelope
            "building": {
                "total_area": takeoff.building_envelope.total_area_sqft,
                "num_floors": takeoff.building_envelope.num_floors,
                "foundation_type": takeoff.building_envelope.foundation_type,
                "wall_r_value": takeoff.building_envelope.wall_r_value,
                "ceiling_r_value": takeoff.building_envelope.ceiling_r_value,
                "floor_r_value": takeoff.building_envelope.floor_r_value
            },
            
            # Climate data
            "climate": {
                "zip_code": takeoff.climate_data.zip_code,
                "climate_zone": takeoff.climate_data.climate_zone,
                "winter_design_temp": takeoff.climate_data.winter_design_temp_f,
                "summer_design_temp": takeoff.climate_data.summer_design_temp_f,
                "summer_humidity": takeoff.climate_data.summer_design_humidity
            },
            
            # Metadata
            "metadata": {
                "filename": takeoff.filename,
                "scale": takeoff.scale_notation,
                "pages_analyzed": takeoff.pages_analyzed,
                "room_summary": takeoff.get_room_summary()
            }
        }
        
        # Add HVAC loads if calculated
        if takeoff.has_hvac_loads:
            response["hvac"] = {
                "total_heating_btu_hr": takeoff.hvac_loads.total_heating_btu_hr,
                "total_cooling_btu_hr": takeoff.hvac_loads.total_cooling_btu_hr,
                "heating_tons": takeoff.hvac_loads.heating_system_tons,
                "cooling_tons": takeoff.hvac_loads.cooling_system_tons,
                "calculation_method": takeoff.hvac_loads.calculation_method,
                "safety_factor": takeoff.hvac_loads.safety_factor,
                "components": {
                    "heating": takeoff.hvac_loads.heating_components,
                    "cooling": takeoff.hvac_loads.cooling_components
                }
            }
        
        return response
    
    def validate_results(self, takeoff: BlueprintTakeoff) -> List[str]:
        """
        Validate takeoff results and return any warnings
        
        Args:
            takeoff: BlueprintTakeoff to validate
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check confidence
        if takeoff.confidence_score < vision_config.min_overall_confidence:
            warnings.append(f"Low overall confidence: {takeoff.confidence_score:.0%}")
        
        # Check room count
        if takeoff.num_rooms < 3:
            warnings.append(f"Few rooms detected: {takeoff.num_rooms}")
        
        # Check total area
        if takeoff.total_area_sqft < 500:
            warnings.append(f"Small total area: {takeoff.total_area_sqft:.0f} sq ft")
        elif takeoff.total_area_sqft > 10000:
            warnings.append(f"Large total area: {takeoff.total_area_sqft:.0f} sq ft")
        
        # Check for rooms with low confidence
        low_confidence_rooms = [
            r.name for r in takeoff.rooms 
            if r.confidence < vision_config.min_room_confidence
        ]
        if low_confidence_rooms:
            warnings.append(f"Low confidence rooms: {', '.join(low_confidence_rooms)}")
        
        # Check HVAC sizing
        if takeoff.has_hvac_loads:
            if takeoff.hvac_loads.cooling_system_tons > 10:
                warnings.append(f"Large cooling load: {takeoff.hvac_loads.cooling_system_tons:.1f} tons")
            if takeoff.hvac_loads.heating_system_tons > 10:
                warnings.append(f"Large heating load: {takeoff.hvac_loads.heating_system_tons:.1f} tons")
        
        return warnings


# Global pipeline instance
blueprint_pipeline = BlueprintPipeline()