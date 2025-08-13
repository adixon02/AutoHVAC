"""
GPT-4o Vision Blueprint Analyzer - Advanced Blueprint Analysis
Uses OpenAI's GPT-4o Vision API to accurately interpret blueprints
Provides comprehensive room detection and HVAC load calculations
"""

import os
import logging
import json
import base64
import time
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image
import io

from services.page_classifier import page_classifier
from services.gpt4v_prompts import blueprint_prompt_manager
from services.gpt4v_multi_floor_prompts import create_multi_floor_prompt
from services.scale_extractor import scale_extractor

logger = logging.getLogger(__name__)


@dataclass
class RoomSurfaces:
    """Surface classification for a room"""
    exterior_walls: int = 0
    interior_walls: int = 0
    has_exterior_ceiling: bool = False
    has_interior_ceiling: bool = False
    has_exterior_floor: bool = False
    has_interior_floor: bool = False

@dataclass
class VerticalConnections:
    """Vertical connections for a room"""
    has_stairs_up: bool = False
    has_stairs_down: bool = False
    likely_room_above: Optional[str] = None
    likely_room_below: Optional[str] = None

@dataclass
class GPTRoom:
    """Room detected by GPT-4V with HVAC loads and surface classification"""
    name: str
    room_type: str  # bedroom, bathroom, kitchen, etc.
    floor_level: int  # Which floor this room is on
    dimensions_ft: Tuple[float, float]  # width x height in feet
    area_sqft: float
    surfaces: RoomSurfaces  # Surface classification
    vertical_connections: VerticalConnections  # Vertical relationships
    location: str  # description of where in the blueprint
    features: List[str]  # windows, doors, closets, etc.
    confidence: float
    heating_btu_hr: Optional[float] = None  # Heating load (exterior surfaces only)
    cooling_btu_hr: Optional[float] = None  # Cooling load (exterior surfaces only)


@dataclass  
class FloorAnalysis:
    """Floor level analysis from blueprint"""
    current_floor_number: int
    current_floor_name: str
    total_floors_in_building: int
    floors_above: int
    floors_below: int
    is_complete_building: bool

@dataclass
class BuildingEnvelope:
    """Building envelope analysis"""
    total_exterior_wall_area: float
    total_interior_wall_area: float
    perimeter_length_ft: float
    envelope_tightness: str
    stairwells: List[Dict[str, Any]]
    open_floor_connections: List[str]

@dataclass
class GPTBlueprintAnalysis:
    """Complete blueprint analysis from GPT-4V with multi-floor awareness"""
    current_floor_area_sqft: float  # Area of the floor shown
    estimated_total_area_sqft: float  # Total building if known
    floor_analysis: FloorAnalysis  # Floor detection results
    building_envelope: BuildingEnvelope  # Envelope analysis
    rooms: List[GPTRoom]
    building_type: str  # residential, commercial, etc.
    special_features: List[str]  # garage, basement, deck, etc.
    scale: str
    confidence: float
    raw_response: Dict[str, Any]
    zip_code: Optional[str] = None
    climate_zone: Optional[str] = None
    floor_heating_btu_hr: Optional[float] = None  # This floor only
    floor_cooling_btu_hr: Optional[float] = None  # This floor only
    estimated_total_heating_btu_hr: Optional[float] = None  # Whole building estimate
    estimated_total_cooling_btu_hr: Optional[float] = None  # Whole building estimate
    heating_system_tons: Optional[float] = None
    cooling_system_tons: Optional[float] = None
    
    @property
    def total_area_sqft(self) -> float:
        """Backward compatibility property for legacy code expecting total_area_sqft"""
        # Return the best estimate we have
        if self.estimated_total_area_sqft and self.estimated_total_area_sqft > 0:
            return self.estimated_total_area_sqft
        else:
            return self.current_floor_area_sqft
    
    @property
    def total_heating_btu_hr(self) -> Optional[float]:
        """Backward compatibility property for legacy code"""
        return self.estimated_total_heating_btu_hr or self.floor_heating_btu_hr
    
    @property
    def total_cooling_btu_hr(self) -> Optional[float]:
        """Backward compatibility property for legacy code"""
        return self.estimated_total_cooling_btu_hr or self.floor_cooling_btu_hr


class GPT4VBlueprintAnalyzer:
    """
    GPT-4o Vision Blueprint Analyzer
    Uses GPT-4o multimodal API to interpret blueprints with high accuracy
    """
    
    def __init__(self):
        """Initialize with OpenAI API key from environment"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for GPT-4V analysis")
        
        # Initialize client with retry configuration
        self.client = OpenAI(
            api_key=api_key,
            max_retries=3  # Retry failed requests up to 3 times
        )
        
        # Initialize timeout BEFORE using it in model configs
        self.gpt_timeout = float(os.getenv("GPT_TIMEOUT", "60"))  # 60 seconds max, single attempt
        logger.info(f"GPT timeout: {self.gpt_timeout}s (single attempt, no retries)")
        
        # Model configurations with proper parameter names
        # Different models require different parameter names for token limits
        self.model_configs = {
            "gpt-4o": {
                "supports_vision": True,
                "max_tokens_param": "max_completion_tokens",  # New parameter name
                "max_tokens_value": 8192,
                "timeout": self.gpt_timeout,  # Use single timeout
                # GPT-4o only supports default temperature (1.0)
            },
            "gpt-4o-2024-11-20": {
                "supports_vision": True,
                "max_tokens_param": "max_completion_tokens",  # New parameter name
                "max_tokens_value": 8192,
                "timeout": self.gpt_timeout,  # Use single timeout
                # GPT-4o only supports default temperature (1.0)
            },
            "gpt-4-turbo-2024-04-09": {
                "supports_vision": True,
                "max_tokens_param": "max_tokens",  # Old parameter name
                "max_tokens_value": 4096,
                "timeout": self.gpt_timeout,  # Use single timeout
                "temperature": 0.1
            },
            "gpt-4-turbo": {
                "supports_vision": True,
                "max_tokens_param": "max_tokens",  # Old parameter name
                "max_tokens_value": 4096,
                "timeout": self.gpt_timeout,  # Use single timeout
                "temperature": 0.1
            },
            "gpt-4-vision-preview": {
                "supports_vision": True,
                "max_tokens_param": "max_tokens",  # Old parameter name
                "max_tokens_value": 4096,
                "timeout": self.gpt_timeout,  # Use single timeout
                "temperature": 0.1
            }
        }
        
        # Models to try in order - gpt-4o-2024-11-20 is the only one that works properly for vision
        self.models_to_try = [
            "gpt-4o-2024-11-20",      # Primary model - only one that properly handles vision
            "gpt-4o",                 # Fallback if specific version not available
        ]
        
    def analyze_blueprint(
        self,
        pdf_path: str,
        zip_code: str = "99006",
        page_num: Optional[int] = None,
        pipeline_context=None,
        override_page: Optional[int] = None,  # New parameter for explicit page selection
        floor_label: Optional[str] = None,  # Floor label from page analysis
        previous_floors: Optional[List[Dict]] = None,  # Previous floor analyses for context
        building_typology: Optional[str] = None,  # Building type hint
        use_discovery_mode: bool = False  # Let GPT-4V discover floor type
    ) -> GPTBlueprintAnalysis:
        """
        Analyze blueprint using GPT-4 Vision for maximum accuracy
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Building location zip code
            page_num: Page number (None = auto-detect floor plan)
            pipeline_context: Pipeline context for locked page selection
            override_page: Explicit page override for multi-floor processing
            
        Returns:
            Complete blueprint analysis with all rooms and dimensions
        """
        start_time = time.time()
        logger.info(f"Starting GPT-4o Vision analysis of {pdf_path}")
        
        # Store zip code for use in retry logic
        self.current_zip_code = zip_code
        
        # Priority: override_page > page_num > pipeline_context > auto-detect
        if override_page is not None:
            # Explicit override for multi-floor processing
            page_num = override_page
            logger.info(f"Using override page {page_num + 1} for multi-floor processing")
        elif page_num is not None:
            # Explicit page number provided
            logger.info(f"Using provided page {page_num + 1}")
        elif pipeline_context:
            try:
                page_num = pipeline_context.get_page()
                logger.info(f"Using locked page {page_num + 1} from pipeline context")
            except ValueError:
                # Context doesn't have page set yet, fall back to auto-detect
                page_num = page_classifier.find_best_floor_plan_page(pdf_path) or 0
                logger.info(f"No context page, auto-detected page {page_num + 1}")
        else:
            # Auto-detect best floor plan page
            page_num = page_classifier.find_best_floor_plan_page(pdf_path) or 0
            logger.info(f"Using auto-detected page {page_num + 1}")
        
        # Render page to high-quality image
        image_base64 = self._render_page_to_base64(pdf_path, page_num)
        
        # SINGLE ATTEMPT - NO RETRIES, NO MULTIPLE VERSIONS
        # If GPT fails, we use geometry-based extraction as the source of truth
        response = None
        raw_response = None
        
        # Choose the appropriate prompt based on context
        if use_discovery_mode:
            from services.gpt4v_floor_discovery_prompts import create_floor_discovery_prompt
            prompt = create_floor_discovery_prompt(
                zip_code=zip_code,
                page_number=page_num or 0,
                page_text_hint=floor_label,  # Pass label as hint only
                previous_floors=previous_floors,
                building_context={'building_typology': building_typology} if building_typology else None
            )
            logger.info("Using floor discovery mode prompt")
        # Use multi-floor context prompt if we have context
        elif previous_floors or floor_label or building_typology:
            prompt = create_multi_floor_prompt(
                zip_code=zip_code,
                page_number=page_num or 0,
                floor_label=floor_label,
                previous_floors=previous_floors,
                building_typology=building_typology
            )
            logger.info("Using multi-floor context prompt")
        else:
            # Use the simplest, most reliable prompt
            prompt = blueprint_prompt_manager.get_prompt("v1_structured", zip_code, floor_hint=page_num + 1)
            logger.info("Using standard prompt")
        
        # SINGLE GPT-4o attempt with reasonable timeout
        try:
            logger.info("Making single GPT-4o Vision call (no retries)...")
            raw_response = self._analyze_with_gpt4v(image_base64, prompt)
            
            # Quick validation - don't be too strict
            min_rooms = 3 if page_num and page_num > 0 else 5
            is_valid, error_msg = blueprint_prompt_manager.validate_response(raw_response, min_rooms=min_rooms)
            
            if is_valid:
                logger.info("✅ GPT-4o Vision succeeded on first attempt")
                response = raw_response
                response['prompt_version_used'] = "single_attempt"
            else:
                logger.warning(f"GPT-4o Vision response invalid: {error_msg}")
                logger.info("Will use geometry-based fallback instead of retrying")
                # Save debug info for analysis
                if hasattr(self, 'current_project_id') and self.current_project_id:
                    try:
                        from services.s3_storage import storage_service
                        debug_data = {
                            'validation_error': error_msg,
                            'response': raw_response,
                            'timestamp': time.time()
                        }
                        storage_service.save_debug_json(
                            self.current_project_id, 
                            f'gpt_validation_failure.json', 
                            debug_data
                        )
                    except Exception as e:
                        logger.debug(f"Could not save debug data: {e}")
                        
        except Exception as e:
            logger.error(f"GPT-4o Vision call failed: {e}")
            logger.info("Will use geometry-based fallback instead of retrying")
        
        if not response:
            logger.info("Using geometry-based fallback (GPT-4o unavailable or failed)")
            # Use the raw response if available, otherwise empty dict
            response = raw_response if raw_response else {}
        
        # Parse the response
        analysis = self._parse_gpt_response(response)
        
        # If in discovery mode, store the floor determination
        if use_discovery_mode and 'floor_determination' in response:
            floor_det = response['floor_determination']
            detected_floor_type = floor_det.get('detected_floor_type', 'unknown')
            logger.info(f"GPT-4V determined floor type: {detected_floor_type} (confidence: {floor_det.get('confidence', 0):.2f})")
            if floor_det.get('contradicts_label'):
                logger.warning(f"Floor type contradicts PDF label! PDF says '{floor_label}' but content shows '{detected_floor_type}'")
            
            # Store floor determination in analysis for later use
            if hasattr(analysis, '__dict__'):
                analysis.detected_floor_type = detected_floor_type
                analysis.floor_confidence = floor_det.get('confidence', 0)
                analysis.floor_reasoning = floor_det.get('reasoning', '')
        
        # Validate and improve the analysis
        if not self._validate_analysis(analysis):
            logger.warning("Analysis validation failed, using fallback values")
            analysis = self._add_fallback_values(analysis)
        
        processing_time = time.time() - start_time
        logger.info(f"GPT-4o Vision analysis complete in {processing_time:.2f}s")
        logger.info(f"Found {len(analysis.rooms)} rooms, total area: {analysis.total_area_sqft} sq ft")
        
        # Clean up temporary attributes
        if hasattr(self, 'current_zip_code'):
            delattr(self, 'current_zip_code')
        
        return analysis
    
    def _render_page_to_base64(self, pdf_path: str, page_num: int, dpi: int = 200) -> str:
        """Render PDF page to base64 encoded image for GPT-4o Vision"""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at high DPI for clarity
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Validate base64 was generated
        if not img_base64:
            doc.close()
            raise ValueError(f"Failed to generate base64 image from page {page_num}")
        
        # Log base64 info for debugging
        logger.debug(f"Generated base64 image: {len(img_base64)} chars, starts with: {img_base64[:100]}")
        
        doc.close()
        return img_base64
    
    def _create_simplified_prompt(self, zip_code: str) -> str:
        """Create a simplified prompt for GPT-4o that avoids confusion"""
        return f"""Analyze this blueprint image and identify all rooms with their dimensions.

Location: ZIP code {zip_code}

Please identify:
1. Each room's name and type
2. Room dimensions in feet
3. Which walls are exterior (touching outside)
4. What floor this is (first, second, basement, etc.)
5. Calculate heating and cooling loads

Return a JSON object with this structure:
{{
  "zip_code": "{zip_code}",
  "floor_analysis": {{
    "current_floor_number": 1,
    "current_floor_name": "First Floor",
    "total_floors_in_building": 2
  }},
  "areas": {{
    "current_floor_sqft": 1500,
    "estimated_total_building_sqft": 3000
  }},
  "rooms": [
    {{
      "name": "Living Room",
      "room_type": "living_room",
      "width_ft": 20,
      "length_ft": 15,
      "area_sqft": 300,
      "surfaces": {{
        "exterior_walls": 2
      }},
      "heating_btu_hr": 5000,
      "cooling_btu_hr": 6000
    }}
  ],
  "hvac_loads": {{
    "floor_heating_btu_hr": 25000,
    "floor_cooling_btu_hr": 30000
  }}
}}"""

    def _create_analysis_prompt(self, zip_code: str, use_simplified: bool = False) -> str:
        """Create enhanced prompt for GPT-4o blueprint analysis with multimodal vision AND HVAC calculation"""
        return f"""You are an expert HVAC load calculation specialist using GPT-4o's advanced multimodal vision capabilities.
        
Analyze this residential blueprint AND calculate HVAC loads using ACCA Manual J methodology.

PROJECT LOCATION: ZIP CODE {zip_code}
This is CRITICAL for determining climate zone, design temperatures, and accurate load calculations.

🏠 CRITICAL MULTI-STORY BUILDING AWARENESS:
Most residential buildings have multiple floors. You MUST:
1. Identify which floor(s) are shown in this image
2. Look for stairs/elevators indicating other floors exist
3. Distinguish between EXTERIOR surfaces (touching outside) and INTERIOR surfaces (between floors)
4. Note vertical room relationships for multi-story buildings

ANALYSIS REQUIREMENTS:

1. FLOOR IDENTIFICATION (Do This FIRST):
   - What floor level is shown? Look for: "First Floor", "Second Floor", "Basement", etc.
   - Are there stairs going UP? (indicates floors above)
   - Are there stairs going DOWN? (indicates floors below)
   - Is this a complete building or just one floor?
   - Estimate total number of floors based on architectural cues

2. Room Detection with Surface Classification:
   - Identify EVERY room on THIS FLOOR
   - For each room, determine:
     * Which walls are EXTERIOR (touching outside)
     * Which walls are INTERIOR (touching other rooms)
     * Is the ceiling to another floor OR to attic/roof?
     * Is the floor above ground OR above another floor?
   - Read ALL dimension annotations
   - Note which rooms have stairs (vertical connections)

3. Scale Extraction:
   - Find and read the scale notation
   - Apply scale to all measurements consistently
   - Verify dimensions against scale

4. Building Envelope Analysis:
   - Map the EXTERIOR envelope (walls/roof/floor touching outside)
   - Identify INTERIOR surfaces (between conditioned spaces)
   - Note building orientation (N/S/E/W if marked)
   - Count exterior wall area vs interior partition area
   - Identify foundation type and ground contact

5. Vertical Space Relationships:
   - Which rooms are likely above/below each other?
   - Are there open spaces (cathedral ceilings, open stairs)?
   - Note any floor/ceiling assemblies between conditioned spaces
   - Identify unconditioned spaces (attic, crawlspace, garage)

6. HVAC Load Calculations - MULTI-FLOOR AWARE:
   - Calculate loads for EXTERIOR surfaces only
   - Do NOT add load for interior floors/ceilings between conditioned spaces
   - Account for stack effect if multiple floors detected
   - Note if this is partial building (loads incomplete)
   - Apply proper infiltration distribution by floor level:
     * More infiltration LOW in winter (cold air sinks)
     * More infiltration HIGH in summer (hot air rises)

Use GPT-4o's vision capabilities to:
- Detect floor level indicators and stairwells
- Distinguish exterior envelope from interior partitions
- Map vertical adjacencies between floors
- Identify shared floor/ceiling assemblies
- Calculate accurate square footage FOR THIS FLOOR
- Estimate total building square footage if multiple floors

Respond with a JSON object in this exact format:
{{
  "zip_code": "{zip_code}",
  "climate_zone": "<climate zone for {zip_code}>",
  "floor_analysis": {{
    "current_floor_number": <0=basement, 1=first, 2=second, etc>,
    "current_floor_name": "<e.g., 'First Floor', 'Second Floor'>",
    "total_floors_in_building": <estimated total>,
    "floors_above": <number of floors above this one>,
    "floors_below": <number of floors below this one>,
    "is_complete_building": <true if all floors shown, false otherwise>
  }},
  "areas": {{
    "current_floor_sqft": <area of THIS floor>,
    "estimated_total_building_sqft": <estimated total if known>,
    "exterior_wall_area_sqft": <only walls touching outside>,
    "interior_partition_area_sqft": <walls between rooms>
  }},
  "building_type": "<residential/commercial/other>",
  "scale": "<scale notation from blueprint>",
  "rooms": [
    {{
      "name": "<room name from blueprint>",
      "room_type": "<bedroom/bathroom/kitchen/etc>",
      "floor_level": <which floor this room is on>,
      "width_ft": <number>,
      "length_ft": <number>,
      "area_sqft": <number>,
      "surfaces": {{
        "exterior_walls": <count of walls touching outside>,
        "interior_walls": <count of walls to other rooms>,
        "has_exterior_ceiling": <true if ceiling to outside/attic>,
        "has_interior_ceiling": <true if ceiling to floor above>,
        "has_exterior_floor": <true if floor to outside/crawl>,
        "has_interior_floor": <true if floor to room below>
      }},
      "vertical_connections": {{
        "has_stairs_up": <true/false>,
        "has_stairs_down": <true/false>,
        "likely_room_above": "<room name if determinable>",
        "likely_room_below": "<room name if determinable>"
      }},
      "location": "<description>",
      "features": ["<feature1>", "<feature2>"],
      "confidence": <0.0-1.0>,
      "heating_btu_hr": <for EXTERIOR surfaces only>,
      "cooling_btu_hr": <for EXTERIOR surfaces only>
    }}
  ],
  "special_features": ["<garage>", "<basement>", "<deck>", etc],
  "building_envelope": {{
    "total_exterior_wall_area": <sq ft of walls touching outside>,
    "total_interior_wall_area": <sq ft of walls between rooms>,
    "perimeter_length_ft": <building perimeter>,
    "envelope_tightness": "<tight/average/leaky based on age/construction>",
    "stairwells": [
      {{"location": "<e.g., central>", "connects_floors": [1, 2]}}
    ],
    "open_floor_connections": ["<e.g., open stairway>", "<cathedral ceiling>"]
  }},
  "confidence": <overall confidence 0.0-1.0>,
  "hvac_loads": {{
    "floor_heating_btu_hr": <heating for THIS FLOOR's EXTERIOR surfaces>,
    "floor_cooling_btu_hr": <cooling for THIS FLOOR's EXTERIOR surfaces>,
    "notes_on_calculation": "<e.g., 'Calculated for first floor only - upper floor not shown'>",
    "infiltration_adjustment": "<e.g., 'Lower floor - higher winter infiltration applied'>",
    "estimated_total_building_heating_btu_hr": <if multiple floors detected>,
    "estimated_total_building_cooling_btu_hr": <if multiple floors detected>,
    "heating_system_tons": <number>,
    "cooling_system_tons": <number>,
    "design_temps": {{
      "winter_design_temp_f": <number for {zip_code}>,
      "summer_design_temp_f": <number for {zip_code}>
    }},
    "calculation_method": "ACCA Manual J via GPT-4o Vision for ZIP {zip_code}"
  }}
}}

REMEMBER: Use ZIP code {zip_code} for all climate-specific calculations!"""
    
    def _analyze_with_gpt4v(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """Send image to GPT-4o/GPT-4V and get analysis with model fallback"""
        last_error = None
        
        # Try each model in order until one works
        for model in self.models_to_try:
            try:
                logger.info(f"Attempting blueprint analysis with {model}...")
                
                # Get model-specific configuration
                config = self.model_configs.get(model, {
                    "supports_vision": True,
                    "max_tokens_param": "max_tokens",
                    "max_tokens_value": 4096,
                    "timeout": 90,
                    "temperature": 0.1
                })
                
                if not config["supports_vision"]:
                    logger.warning(f"{model} does not support vision, skipping")
                    continue
                
                logger.info(f"Using {config['timeout']}s timeout for {model}")
                logger.info(f"Using parameter '{config['max_tokens_param']}' with value {config['max_tokens_value']}")
                
                # Build request parameters with model-specific token parameter
                request_params = {
                    "model": model,
                    "timeout": config["timeout"],
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ]
                }
                
                # Add temperature only if specified in config (GPT-4o doesn't support it)
                if "temperature" in config:
                    request_params["temperature"] = config["temperature"]
                
                # Add the correct token parameter based on model
                request_params[config["max_tokens_param"]] = config["max_tokens_value"]
                
                # Make the API call with model-specific parameters
                response = self.client.chat.completions.create(**request_params)
                
                # Successfully got a response with this model
                logger.info(f"✅ {model} responded successfully")
                
                # Extract JSON from response
                content = response.choices[0].message.content
                
                # Save raw GPT-4V response for debugging (if project_id is available)
                if hasattr(self, 'current_project_id') and self.current_project_id:
                    try:
                        from services.s3_storage import storage_service
                        raw_response = {
                            'model': model,
                            'timestamp': time.time(),
                            'prompt_length': len(prompt),
                            'response': content,
                            'token_params': {config['max_tokens_param']: config['max_tokens_value']},
                            'temperature': config['temperature']
                        }
                        storage_service.save_json(self.current_project_id, 'gpt4v_raw.json', raw_response)
                        logger.info(f"[S3] Saved GPT-4V raw response to jobs/{self.current_project_id}/gpt4v_raw.json")
                    except Exception as e:
                        logger.debug(f"Could not save GPT-4V raw response: {e}")
                
                # Check if model claims it can't see images
                if any(phrase in content.lower() for phrase in [
                    "unable to analyze images",
                    "can't analyze images",
                    "cannot analyze images",
                    "unable to view images",
                    "can't see images",
                    "i cannot see",
                    "i can't see",
                    "no image provided",
                    "text-based ai"
                ]):
                    logger.warning(f"⚠️ {model} seems confused about vision capabilities")
                    logger.info("Retrying with simplified prompt...")
                    
                    # Retry with simplified prompt
                    simplified_prompt = self._create_simplified_prompt(
                        self.current_zip_code if hasattr(self, 'current_zip_code') else "99006"
                    )
                    
                    try:
                        retry_params = request_params.copy()
                        retry_params["messages"][0]["content"][0]["text"] = simplified_prompt
                        retry_response = self.client.chat.completions.create(**retry_params)
                        retry_content = retry_response.choices[0].message.content
                        
                        # Try to parse the simplified response
                        import re
                        json_match = re.search(r'\{.*\}', retry_content, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group())
                            result['model_used'] = f"{model} (simplified)"
                            logger.info(f"✅ {model} succeeded with simplified prompt")
                            return result
                    except Exception as retry_error:
                        logger.warning(f"Simplified prompt also failed: {retry_error}")
                    
                    last_error = f"{model} vision confusion"
                    continue
                
                # Try to parse JSON from the response
                try:
                    # Find JSON in the response (might be wrapped in markdown)
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        result = json.loads(json_str)
                        # Add which model was used
                        result['model_used'] = model
                        return result
                    else:
                        # Try parsing the whole content
                        result = json.loads(content)
                        result['model_used'] = model
                        return result
                except json.JSONDecodeError:
                    logger.warning(f"{model} returned non-JSON response: {content[:200]}")
                    # Continue to next model
                    last_error = f"JSON parsing failed for {model}"
                    continue
                    
            except Exception as e:
                logger.warning(f"{model} failed: {e}")
                last_error = str(e)
                # Continue to next model
                continue
        
        # All models failed
        logger.error(f"All models failed. Last error: {last_error}")
        return {
            "error": "All models failed",
            "last_error": last_error,
            "rooms": [],
            "total_area_sqft": 0
        }
    
    def _parse_gpt_response(self, response: Dict[str, Any]) -> GPTBlueprintAnalysis:
        """Parse GPT-4V response into structured analysis with multi-floor awareness"""
        
        # Handle floor determination if present (discovery mode)
        floor_determination = None
        if 'floor_determination' in response:
            floor_determination = response['floor_determination']
        
        # Parse floor analysis
        floor_data = response.get("floor_analysis", {})
        floor_analysis = FloorAnalysis(
            current_floor_number=floor_data.get("current_floor_number", 1),
            current_floor_name=floor_data.get("current_floor_name", "Unknown Floor"),
            total_floors_in_building=floor_data.get("total_floors_in_building", 1),
            floors_above=floor_data.get("floors_above", 0),
            floors_below=floor_data.get("floors_below", 0),
            is_complete_building=floor_data.get("is_complete_building", True)
        )
        
        # Parse building envelope
        envelope_data = response.get("building_envelope", {})
        building_envelope = BuildingEnvelope(
            total_exterior_wall_area=envelope_data.get("total_exterior_wall_area", 0),
            total_interior_wall_area=envelope_data.get("total_interior_wall_area", 0),
            perimeter_length_ft=envelope_data.get("perimeter_length_ft", 0),
            envelope_tightness=envelope_data.get("envelope_tightness", "average"),
            stairwells=envelope_data.get("stairwells", []),
            open_floor_connections=envelope_data.get("open_floor_connections", [])
        )
        
        # Parse rooms with surface classification
        rooms = []
        for room_data in response.get("rooms", []):
            try:
                # Parse surfaces
                surfaces_data = room_data.get("surfaces", {})
                surfaces = RoomSurfaces(
                    exterior_walls=surfaces_data.get("exterior_walls", 0),
                    interior_walls=surfaces_data.get("interior_walls", 0),
                    has_exterior_ceiling=surfaces_data.get("has_exterior_ceiling", False),
                    has_interior_ceiling=surfaces_data.get("has_interior_ceiling", False),
                    has_exterior_floor=surfaces_data.get("has_exterior_floor", False),
                    has_interior_floor=surfaces_data.get("has_interior_floor", False)
                )
                
                # Parse vertical connections
                vert_data = room_data.get("vertical_connections", {})
                vertical_connections = VerticalConnections(
                    has_stairs_up=vert_data.get("has_stairs_up", False),
                    has_stairs_down=vert_data.get("has_stairs_down", False),
                    likely_room_above=vert_data.get("likely_room_above"),
                    likely_room_below=vert_data.get("likely_room_below")
                )
                
                # Handle dimensions
                width = room_data.get("width_ft", 10) or 10
                length = room_data.get("length_ft", 10) or 10
                
                # Calculate area fallback: if dimensions exist but area is 0 or missing, calculate it
                provided_area = room_data.get("area_sqft", 0)
                if provided_area and provided_area > 0:
                    area = float(provided_area)
                elif width and length and width > 0 and length > 0:
                    # Fallback: calculate area from dimensions
                    area = float(width) * float(length)
                    logger.info(f"Calculated area for {room_data.get('name', 'Unknown')}: {width}×{length}={area} sqft")
                else:
                    # Last resort: use reasonable default
                    area = 100.0
                    logger.warning(f"Using default area for {room_data.get('name', 'Unknown')} (no dimensions provided)")
                
                room = GPTRoom(
                    name=room_data.get("name", "Unknown"),
                    room_type=room_data.get("room_type", "unknown"),
                    floor_level=room_data.get("floor_level", floor_analysis.current_floor_number),
                    dimensions_ft=(float(width), float(length)),
                    area_sqft=area,
                    surfaces=surfaces,
                    vertical_connections=vertical_connections,
                    location=room_data.get("location", "") or "",
                    features=room_data.get("features", []) or [],
                    confidence=float(room_data.get("confidence", 0.5) or 0.5),
                    heating_btu_hr=float(room_data.get("heating_btu_hr", 0)) if "heating_btu_hr" in room_data else None,
                    cooling_btu_hr=float(room_data.get("cooling_btu_hr", 0)) if "cooling_btu_hr" in room_data else None
                )
                rooms.append(room)
            except Exception as e:
                logger.warning(f"Error parsing room: {e}")
        
        # Parse areas
        areas = response.get("areas", {})
        current_floor_area = areas.get("current_floor_sqft", sum(r.area_sqft for r in rooms))
        estimated_total_area = areas.get("estimated_total_building_sqft", current_floor_area)
        
        # Extract HVAC loads with multi-floor awareness
        hvac_loads = response.get("hvac_loads", {})
        
        analysis = GPTBlueprintAnalysis(
            current_floor_area_sqft=float(current_floor_area),
            estimated_total_area_sqft=float(estimated_total_area),
            floor_analysis=floor_analysis,
            building_envelope=building_envelope,
            rooms=rooms,
            building_type=response.get("building_type", "residential"),
            special_features=response.get("special_features", []),
            scale=response.get("scale", "1/4\"=1'-0\""),
            confidence=float(response.get("confidence", 0.7)) if response.get("confidence") else 0.7,
            raw_response=response,
            zip_code=response.get("zip_code"),
            climate_zone=response.get("climate_zone"),
            floor_heating_btu_hr=hvac_loads.get("floor_heating_btu_hr"),
            floor_cooling_btu_hr=hvac_loads.get("floor_cooling_btu_hr"),
            estimated_total_heating_btu_hr=hvac_loads.get("estimated_total_building_heating_btu_hr"),
            estimated_total_cooling_btu_hr=hvac_loads.get("estimated_total_building_cooling_btu_hr"),
            heating_system_tons=hvac_loads.get("heating_system_tons"),
            cooling_system_tons=hvac_loads.get("cooling_system_tons")
        )
        
        # Add backward compatibility fields for validation
        if 'total_area_sqft' not in response and 'areas' in response:
            response['total_area_sqft'] = response['areas'].get('current_floor_sqft', 0)
            logger.debug(f"Added backward compatibility: total_area_sqft = {response['total_area_sqft']}")
        
        return analysis
    
    def _validate_analysis(self, analysis: GPTBlueprintAnalysis) -> bool:
        """Validate that the analysis has all required fields with reasonable values"""
        try:
            # Check for required fields
            if not analysis.rooms or len(analysis.rooms) == 0:
                logger.warning("No rooms found in analysis")
                return False
            
            # Check area calculations
            if analysis.current_floor_area_sqft <= 0:
                logger.warning(f"Invalid floor area: {analysis.current_floor_area_sqft}")
                return False
            
            # Check that rooms have valid dimensions
            for room in analysis.rooms:
                if room.area_sqft <= 0:
                    logger.warning(f"Room {room.name} has invalid area: {room.area_sqft}")
                    return False
            
            # Check floor analysis
            if not analysis.floor_analysis or analysis.floor_analysis.current_floor_number < 0:
                logger.warning("Invalid floor analysis")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating analysis: {e}")
            return False
    
    def _add_fallback_values(self, analysis: GPTBlueprintAnalysis) -> GPTBlueprintAnalysis:
        """Add reasonable fallback values for missing or invalid data"""
        try:
            # Ensure rooms have minimum valid values
            for room in analysis.rooms:
                if room.area_sqft <= 0:
                    # Estimate from dimensions if available
                    if room.dimensions_ft[0] > 0 and room.dimensions_ft[1] > 0:
                        room.area_sqft = room.dimensions_ft[0] * room.dimensions_ft[1]
                    else:
                        room.area_sqft = 100  # Default fallback
                
                # Ensure surfaces are set
                if not hasattr(room, 'surfaces') or room.surfaces is None:
                    room.surfaces = RoomSurfaces(exterior_walls=1)  # Conservative default
            
            # Ensure floor analysis is valid
            if not analysis.floor_analysis:
                analysis.floor_analysis = FloorAnalysis(
                    current_floor_number=1,
                    current_floor_name="First Floor",
                    total_floors_in_building=1,
                    floors_above=0,
                    floors_below=0,
                    is_complete_building=True
                )
            
            # Ensure building envelope exists
            if not analysis.building_envelope:
                analysis.building_envelope = BuildingEnvelope(
                    total_exterior_wall_area=analysis.current_floor_area_sqft * 0.4,
                    total_interior_wall_area=analysis.current_floor_area_sqft * 0.3,
                    perimeter_length_ft=math.sqrt(analysis.current_floor_area_sqft) * 4,
                    envelope_tightness="average",
                    stairwells=[],
                    open_floor_connections=[]
                )
            
            # Calculate areas if missing
            if analysis.current_floor_area_sqft <= 0:
                analysis.current_floor_area_sqft = sum(r.area_sqft for r in analysis.rooms)
            
            if analysis.estimated_total_area_sqft <= 0:
                analysis.estimated_total_area_sqft = analysis.current_floor_area_sqft * \
                    analysis.floor_analysis.total_floors_in_building
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error adding fallback values: {e}")
            return analysis
    
    def format_for_hvac(self, analysis: GPTBlueprintAnalysis) -> Dict[str, Any]:
        """Format GPT-4o Vision analysis for HVAC load calculations with multi-floor awareness"""
        return {
            "success": True,
            "current_floor_area": analysis.current_floor_area_sqft,
            "estimated_total_area": analysis.estimated_total_area_sqft,
            "floor_info": {
                "current_floor": analysis.floor_analysis.current_floor_number,
                "current_floor_name": analysis.floor_analysis.current_floor_name,
                "total_floors": analysis.floor_analysis.total_floors_in_building,
                "is_complete": analysis.floor_analysis.is_complete_building
            },
            "rooms": [
                {
                    "name": room.name,
                    "area": room.area_sqft,
                    "room_type": room.room_type,
                    "floor_level": room.floor_level,
                    "width": room.dimensions_ft[0],
                    "height": room.dimensions_ft[1],
                    "exterior_walls": room.surfaces.exterior_walls,
                    "has_exterior_ceiling": room.surfaces.has_exterior_ceiling,
                    "features": room.features,
                    "confidence": room.confidence,
                    "heating_btu_hr": room.heating_btu_hr,
                    "cooling_btu_hr": room.cooling_btu_hr
                }
                for room in analysis.rooms
            ],
            "building_envelope": {
                "exterior_wall_area": analysis.building_envelope.total_exterior_wall_area,
                "interior_wall_area": analysis.building_envelope.total_interior_wall_area,
                "stairwells": analysis.building_envelope.stairwells,
                "envelope_tightness": analysis.building_envelope.envelope_tightness
            },
            "metadata": {
                "method": "GPT-4o Vision Multi-Floor Analysis",
                "building_type": analysis.building_type,
                "special_features": analysis.special_features,
                "scale": analysis.scale,
                "confidence": analysis.confidence,
                "zip_code": analysis.zip_code,
                "climate_zone": analysis.climate_zone
            },
            "hvac_totals": {
                "floor_heating_btu_hr": analysis.floor_heating_btu_hr,
                "floor_cooling_btu_hr": analysis.floor_cooling_btu_hr,
                "estimated_total_heating_btu_hr": analysis.estimated_total_heating_btu_hr,
                "estimated_total_cooling_btu_hr": analysis.estimated_total_cooling_btu_hr,
                "heating_system_tons": analysis.heating_system_tons,
                "cooling_system_tons": analysis.cooling_system_tons
            }
        }


# Global instance (will be created when API key is available)
_gpt4v_analyzer = None

def get_gpt4v_analyzer():
    """Get or create GPT-4V analyzer instance"""
    global _gpt4v_analyzer
    if _gpt4v_analyzer is None:
        _gpt4v_analyzer = GPT4VBlueprintAnalyzer()
    return _gpt4v_analyzer