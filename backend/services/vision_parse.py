"""
Vision Parse - GPT-5 Vision integration for blueprint analysis
Handles communication with OpenAI Vision API and response parsing
"""

import json
import logging
import time
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import ValidationError

from services.vision_config import vision_config, ModelConfig
from services.takeoff_schema import (
    BlueprintTakeoff, Room, BuildingEnvelope, ClimateData,
    HVACLoad, GPTResponse, SourceType, RoomType
)
from services.pdf_to_images import PageImage

logger = logging.getLogger(__name__)


class VisionParser:
    """Parse blueprints using GPT-5 Vision API"""
    
    def __init__(self):
        """Initialize Vision Parser with OpenAI client"""
        if not vision_config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for vision parsing")
        
        self.client = OpenAI(api_key=vision_config.openai_api_key)
        self.models = vision_config.models
        
    def parse_blueprint(
        self,
        page_images: List[PageImage],
        zip_code: str,
        project_id: str,
        filename: str
    ) -> BlueprintTakeoff:
        """
        Parse blueprint images using GPT-5 Vision
        
        Args:
            page_images: List of PageImage objects to analyze
            zip_code: Project location ZIP code
            project_id: Unique project identifier
            filename: Original blueprint filename
            
        Returns:
            BlueprintTakeoff with all parsed data
        """
        start_time = time.time()
        logger.info(f"Starting vision parsing for {len(page_images)} pages with ZIP {zip_code}")
        
        # Prepare images for API
        from services.pdf_to_images import pdf_converter
        image_contents = pdf_converter.prepare_for_vision_api(page_images)
        
        # Create comprehensive prompt
        prompt = self._create_analysis_prompt(zip_code, len(page_images))
        
        # Try each model until one succeeds
        response = None
        model_used = None
        
        for model_config in self.models:
            try:
                logger.info(f"Attempting blueprint analysis with {model_config.name}")
                response = self._call_vision_api(
                    model_config=model_config,
                    image_contents=image_contents,
                    prompt=prompt
                )
                
                if response:
                    model_used = model_config.name
                    logger.info(f"Successfully received response from {model_used}")
                    break
                    
            except Exception as e:
                logger.warning(f"{model_config.name} failed: {e}")
                continue
        
        if not response:
            raise Exception("All vision models failed to analyze blueprint")
        
        # Parse and validate response
        takeoff = self._parse_response(
            response=response,
            project_id=project_id,
            filename=filename,
            zip_code=zip_code,
            model_used=model_used,
            pages_analyzed=[p.page_num for p in page_images],
            processing_time=time.time() - start_time
        )
        
        logger.info(f"Vision parsing complete: {takeoff.num_rooms} rooms, {takeoff.total_area_sqft:.0f} sq ft")
        
        return takeoff
    
    def _create_analysis_prompt(self, zip_code: str, num_pages: int) -> str:
        """Create comprehensive prompt for GPT-5 Vision analysis"""
        return f"""You are an expert architectural blueprint analyzer and HVAC engineer using GPT-5's advanced vision capabilities.

CRITICAL INFORMATION:
- PROJECT ZIP CODE: {zip_code}
- NUMBER OF PAGES: {num_pages} blueprint pages provided
- TASK: Complete blueprint analysis and HVAC load calculations

ANALYSIS REQUIREMENTS:

1. MULTI-PAGE ANALYSIS:
   - Examine ALL {num_pages} provided pages
   - Identify which pages contain floor plans
   - Combine information from multiple pages if needed
   - Note page numbers for reference

2. ROOM DETECTION:
   - Identify EVERY room, closet, hallway, and space
   - Read dimension annotations (e.g., "12'-6" x 10'-0")
   - Detect room labels and types
   - Calculate exact area in square feet
   - Count exterior walls for each room
   - Note window and door locations/sizes

3. SCALE EXTRACTION:
   - Find scale notation (e.g., 1/4"=1'-0" or 1/8"=1'-0")
   - Apply scale consistently to all measurements
   - Verify dimensions against scale

4. BUILDING ENVELOPE:
   - Total conditioned area
   - Number of floors
   - Foundation type (slab/crawl/basement)
   - Building orientation if marked

5. HVAC LOAD CALCULATIONS:
   For ZIP code {zip_code}, determine:
   - Climate zone (ASHRAE)
   - Design temperatures (winter/summer)
   - Calculate heating BTU/hr for each room
   - Calculate cooling BTU/hr for each room
   - Size equipment with appropriate safety factors

6. DATA CONFIDENCE:
   For each value, track source:
   - "labeled": Directly from blueprint text
   - "scaled": Calculated from scale
   - "assumed": Estimated based on context

RESPONSE FORMAT:
Provide a JSON response that strictly conforms to this schema:

{{
  "blueprint_takeoff": {{
    "project_id": "provided_by_system",
    "filename": "provided_by_system",
    "rooms": [
      {{
        "id": "room_001",
        "name": "Living Room",
        "room_type": "living_room",
        "width_ft": 15.5,
        "length_ft": 12.0,
        "ceiling_height_ft": 8.0,
        "windows": [
          {{
            "width_ft": 4.0,
            "height_ft": 5.0,
            "orientation": "S",
            "glazing_type": "double_pane",
            "source": "labeled"
          }}
        ],
        "doors": [
          {{
            "width_ft": 3.0,
            "height_ft": 7.0,
            "type": "interior",
            "material": "wood",
            "source": "assumed"
          }}
        ],
        "exterior_walls": 2,
        "floor_number": 1,
        "location_description": "Front of house, south side",
        "heating_btu_hr": 3500,
        "cooling_btu_hr": 4200,
        "source": "labeled",
        "confidence": 0.95
      }}
    ],
    "building_envelope": {{
      "total_area_sqft": 2000,
      "num_floors": 2,
      "foundation_type": "slab",
      "wall_r_value": 13.0,
      "ceiling_r_value": 30.0,
      "floor_r_value": 19.0,
      "orientation_degrees": 0,
      "air_changes_per_hour": 0.5,
      "source": "scaled"
    }},
    "climate_data": {{
      "zip_code": "{zip_code}",
      "climate_zone": "4A",
      "winter_design_temp_f": 14,
      "summer_design_temp_f": 91,
      "summer_design_humidity": 50,
      "latitude": null,
      "longitude": null,
      "elevation_ft": null,
      "source": "labeled"
    }},
    "hvac_loads": {{
      "room_loads": {{"room_001": {{"heating": 3500, "cooling": 4200}}}},
      "total_heating_btu_hr": 45000,
      "total_cooling_btu_hr": 52000,
      "heating_system_tons": 3.75,
      "cooling_system_tons": 4.33,
      "heating_components": {{
        "walls": 15000,
        "windows": 8000,
        "infiltration": 12000,
        "doors": 3000,
        "floors": 7000
      }},
      "cooling_components": {{
        "walls": 12000,
        "windows": 15000,
        "solar": 10000,
        "internal": 8000,
        "infiltration": 7000
      }},
      "calculation_method": "ACCA Manual J",
      "safety_factor": 1.1,
      "timestamp": "2024-01-01T00:00:00Z"
    }},
    "scale_notation": "1/4\\"=1'-0\\"",
    "pages_analyzed": [1, 2],
    "confidence_score": 0.85,
    "processing_time_seconds": 0,
    "model_used": "gpt-5"
  }},
  "reasoning": "Optional: Explain your analysis process",
  "warnings": ["Any issues or uncertainties"]
}}

IMPORTANT:
- Analyze ALL {num_pages} pages provided
- Use ZIP {zip_code} for climate-specific calculations
- Ensure all rooms are detected and measured
- Provide specific BTU/hr calculations for each room
- Return ONLY valid JSON (no markdown formatting)"""
    
    def _call_vision_api(
        self,
        model_config: ModelConfig,
        image_contents: List[Dict[str, Any]],
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call OpenAI Vision API with specified model
        
        Args:
            model_config: Model configuration to use
            image_contents: Prepared image content blocks
            prompt: Analysis prompt
            
        Returns:
            Parsed JSON response or None if failed
        """
        try:
            # Build messages
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        *image_contents
                    ]
                }
            ]
            
            # Get API parameters
            api_params = model_config.get_api_params()
            api_params["messages"] = messages
            
            # Add extra body parameters if supported
            extra_body = model_config.get_extra_body()
            if extra_body:
                api_params["extra_body"] = extra_body
            
            # Make API call
            logger.debug(f"Calling {model_config.name} with {len(image_contents)} images")
            response = self.client.chat.completions.create(**api_params)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON from response
            json_response = self._extract_json(content)
            
            if json_response:
                logger.debug(f"Successfully parsed JSON response from {model_config.name}")
                return json_response
            else:
                logger.warning(f"Failed to extract valid JSON from {model_config.name} response")
                return None
                
        except Exception as e:
            logger.error(f"Error calling {model_config.name}: {e}")
            return None
    
    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from API response content
        
        Args:
            content: Raw response content
            
        Returns:
            Parsed JSON dictionary or None
        """
        try:
            # Try direct JSON parsing
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in markdown code blocks
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find raw JSON object
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        
        logger.warning("Could not extract valid JSON from response")
        return None
    
    def _parse_response(
        self,
        response: Dict[str, Any],
        project_id: str,
        filename: str,
        zip_code: str,
        model_used: str,
        pages_analyzed: List[int],
        processing_time: float
    ) -> BlueprintTakeoff:
        """
        Parse and validate API response into BlueprintTakeoff
        
        Args:
            response: Raw API response dictionary
            project_id: Project identifier
            filename: Blueprint filename
            zip_code: Location ZIP code
            model_used: Model that provided response
            pages_analyzed: List of page numbers analyzed
            processing_time: Processing time in seconds
            
        Returns:
            Validated BlueprintTakeoff object
        """
        try:
            # Check if response is wrapped in GPTResponse
            if "blueprint_takeoff" in response:
                takeoff_data = response["blueprint_takeoff"]
            else:
                takeoff_data = response
            
            # Set system-provided values
            takeoff_data["project_id"] = project_id
            takeoff_data["filename"] = filename
            takeoff_data["model_used"] = model_used
            takeoff_data["pages_analyzed"] = pages_analyzed
            takeoff_data["processing_time_seconds"] = processing_time
            
            # Ensure ZIP code is set
            if "climate_data" not in takeoff_data:
                takeoff_data["climate_data"] = {}
            takeoff_data["climate_data"]["zip_code"] = zip_code
            
            # Set defaults for missing climate data
            climate_defaults = {
                "climate_zone": vision_config.default_climate_zone,
                "winter_design_temp_f": 20.0,
                "summer_design_temp_f": 90.0,
                "summer_design_humidity": 50.0,
                "source": SourceType.ASSUMED
            }
            for key, value in climate_defaults.items():
                if key not in takeoff_data["climate_data"]:
                    takeoff_data["climate_data"][key] = value
            
            # Ensure rooms have required fields
            if "rooms" in takeoff_data:
                for i, room in enumerate(takeoff_data["rooms"]):
                    # Generate ID if missing
                    if "id" not in room:
                        room["id"] = f"room_{i+1:03d}"
                    
                    # Set defaults for missing fields
                    room_defaults = {
                        "ceiling_height_ft": vision_config.default_ceiling_height_ft,
                        "windows": [],
                        "doors": [],
                        "exterior_walls": 0,
                        "floor_number": 1,
                        "location_description": "",
                        "source": SourceType.SCALED,
                        "confidence": 0.7
                    }
                    for key, value in room_defaults.items():
                        if key not in room:
                            room[key] = value
            
            # Ensure building envelope has required fields
            if "building_envelope" not in takeoff_data:
                takeoff_data["building_envelope"] = {}
            
            envelope_defaults = {
                "total_area_sqft": sum(r.get("area_sqft", r.get("width_ft", 10) * r.get("length_ft", 10)) 
                                      for r in takeoff_data.get("rooms", [])),
                "num_floors": 1,
                "foundation_type": "slab",
                "wall_r_value": vision_config.default_wall_r_value,
                "ceiling_r_value": vision_config.default_ceiling_r_value,
                "floor_r_value": vision_config.default_floor_r_value,
                "air_changes_per_hour": vision_config.default_air_changes_per_hour,
                "source": SourceType.ASSUMED
            }
            for key, value in envelope_defaults.items():
                if key not in takeoff_data["building_envelope"]:
                    takeoff_data["building_envelope"][key] = value
            
            # Set default scale if missing
            if "scale_notation" not in takeoff_data:
                takeoff_data["scale_notation"] = "1/4\"=1'-0\""
            
            # Set confidence score if missing
            if "confidence_score" not in takeoff_data:
                takeoff_data["confidence_score"] = 0.7
            
            # Create and validate BlueprintTakeoff
            takeoff = BlueprintTakeoff(**takeoff_data)
            
            logger.info(f"Successfully parsed blueprint: {takeoff.num_rooms} rooms, {takeoff.total_area_sqft:.0f} sq ft")
            
            return takeoff
            
        except ValidationError as e:
            logger.error(f"Validation error parsing response: {e}")
            logger.debug(f"Response data: {json.dumps(response, indent=2)}")
            
            # Try to create partial takeoff with available data
            if vision_config.allow_partial_results:
                return self._create_fallback_takeoff(
                    response=response,
                    project_id=project_id,
                    filename=filename,
                    zip_code=zip_code,
                    model_used=model_used,
                    pages_analyzed=pages_analyzed,
                    processing_time=processing_time
                )
            else:
                raise
    
    def _create_fallback_takeoff(
        self,
        response: Dict[str, Any],
        project_id: str,
        filename: str,
        zip_code: str,
        model_used: str,
        pages_analyzed: List[int],
        processing_time: float
    ) -> BlueprintTakeoff:
        """Create a minimal valid takeoff when full parsing fails"""
        logger.warning("Creating fallback takeoff with partial data")
        
        # Extract any rooms we can find
        rooms = []
        raw_rooms = response.get("rooms", []) if "blueprint_takeoff" not in response else \
                   response.get("blueprint_takeoff", {}).get("rooms", [])
        
        for i, room_data in enumerate(raw_rooms):
            try:
                room = Room(
                    id=room_data.get("id", f"room_{i+1:03d}"),
                    name=room_data.get("name", f"Room {i+1}"),
                    room_type=RoomType.OTHER,
                    width_ft=float(room_data.get("width_ft", 10)),
                    length_ft=float(room_data.get("length_ft", 10)),
                    source=SourceType.ASSUMED,
                    confidence=0.3
                )
                rooms.append(room)
            except Exception as e:
                logger.debug(f"Skipping invalid room: {e}")
        
        # Ensure at least one room
        if not rooms:
            rooms = [
                Room(
                    id="room_001",
                    name="Detected Space",
                    room_type=RoomType.OTHER,
                    width_ft=10.0,
                    length_ft=10.0,
                    source=SourceType.ASSUMED,
                    confidence=0.1
                )
            ]
        
        # Create minimal valid takeoff
        takeoff = BlueprintTakeoff(
            project_id=project_id,
            filename=filename,
            rooms=rooms,
            building_envelope=BuildingEnvelope(
                total_area_sqft=sum(r.area_sqft for r in rooms),
                num_floors=1,
                source=SourceType.ASSUMED
            ),
            climate_data=ClimateData(
                zip_code=zip_code,
                climate_zone=vision_config.default_climate_zone,
                winter_design_temp_f=20.0,
                summer_design_temp_f=90.0,
                source=SourceType.ASSUMED
            ),
            scale_notation="Unknown",
            pages_analyzed=pages_analyzed,
            confidence_score=0.3,
            processing_time_seconds=processing_time,
            model_used=model_used
        )
        
        return takeoff


# Global parser instance
vision_parser = VisionParser()