"""
GPT-5 Vision Blueprint Analyzer - Advanced Blueprint Analysis
Uses OpenAI's GPT-5 Vision API to accurately interpret blueprints
Provides comprehensive room detection and HVAC load calculations
"""

import os
import logging
import json
import base64
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image
import io

from services.page_classifier import page_classifier
from services.scale_extractor import scale_extractor

logger = logging.getLogger(__name__)


@dataclass
class GPTRoom:
    """Room detected by GPT-5 with HVAC loads"""
    name: str
    room_type: str  # bedroom, bathroom, kitchen, etc.
    dimensions_ft: Tuple[float, float]  # width x height in feet
    area_sqft: float
    location: str  # description of where in the blueprint
    features: List[str]  # windows, doors, closets, etc.
    confidence: float
    heating_btu_hr: Optional[float] = None  # Heating load in BTU/hr
    cooling_btu_hr: Optional[float] = None  # Cooling load in BTU/hr


@dataclass
class GPTBlueprintAnalysis:
    """Complete blueprint analysis from GPT-5 with HVAC loads"""
    total_area_sqft: float
    num_floors: int
    rooms: List[GPTRoom]
    building_type: str  # residential, commercial, etc.
    special_features: List[str]  # garage, basement, deck, etc.
    scale: str
    confidence: float
    raw_response: Dict[str, Any]
    zip_code: Optional[str] = None
    climate_zone: Optional[str] = None
    total_heating_btu_hr: Optional[float] = None
    total_cooling_btu_hr: Optional[float] = None
    heating_system_tons: Optional[float] = None
    cooling_system_tons: Optional[float] = None


class GPT4VBlueprintAnalyzer:
    """
    GPT-5 Vision Blueprint Analyzer
    Uses GPT-5 Vision API to interpret blueprints with high accuracy
    """
    
    def __init__(self):
        """Initialize with OpenAI API key from environment"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for GPT-4V analysis")
        
        self.client = OpenAI(api_key=api_key)
        # GPT-5 models - announced today with native vision support!
        self.models_to_try = [
            "gpt-5",            # Flagship GPT-5 with 400k context and vision
            "gpt-5-mini",       # Cheaper/faster GPT-5 with vision
            "gpt-4-turbo",      # Fallback to GPT-4 if needed
        ]
        self.model = self.models_to_try[0]  # Start with GPT-5
        self.max_tokens = 8192  # GPT-5 supports more tokens
        
        # GPT-5 specific parameters
        self.reasoning_effort = "high"  # For complex blueprint analysis
        self.verbosity = "low"  # We want concise JSON output
        
    def analyze_blueprint(
        self,
        pdf_path: str,
        zip_code: str = "99006",
        page_num: Optional[int] = None,
        pipeline_context=None
    ) -> GPTBlueprintAnalysis:
        """
        Analyze blueprint using GPT-4 Vision for maximum accuracy
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Building location zip code
            page_num: Page number (None = auto-detect floor plan)
            
        Returns:
            Complete blueprint analysis with all rooms and dimensions
        """
        start_time = time.time()
        logger.info(f"Starting GPT-5 Vision analysis of {pdf_path}")
        
        # Use page from pipeline context if available, otherwise from parameter or auto-detect
        if pipeline_context:
            try:
                page_num = pipeline_context.get_page()
                logger.info(f"Using locked page {page_num + 1} from pipeline context")
            except ValueError:
                # Context doesn't have page set yet, fall back to other methods
                if page_num is None:
                    page_num = page_classifier.find_best_floor_plan_page(pdf_path) or 0
                    logger.info(f"No context page, auto-detected page {page_num + 1}")
        elif page_num is None:
            page_num = page_classifier.find_best_floor_plan_page(pdf_path) or 0
            logger.info(f"Using auto-detected page {page_num + 1}")
        else:
            logger.info(f"Using provided page {page_num + 1}")
        
        # Render page to high-quality image
        image_base64 = self._render_page_to_base64(pdf_path, page_num)
        
        # Prepare the analysis prompt - BE SPECIFIC!
        prompt = self._create_analysis_prompt(zip_code)
        
        # Send to GPT-5 for analysis
        logger.info("Sending blueprint to GPT-5 Vision for analysis...")
        response = self._analyze_with_gpt4v(image_base64, prompt)
        
        # Parse the response
        analysis = self._parse_gpt_response(response)
        
        processing_time = time.time() - start_time
        logger.info(f"GPT-5 Vision analysis complete in {processing_time:.2f}s")
        logger.info(f"Found {len(analysis.rooms)} rooms, total area: {analysis.total_area_sqft} sq ft")
        
        return analysis
    
    def _render_page_to_base64(self, pdf_path: str, page_num: int, dpi: int = 200) -> str:
        """Render PDF page to base64 encoded image for GPT-5 Vision"""
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
        
        doc.close()
        return img_base64
    
    def _create_analysis_prompt(self, zip_code: str) -> str:
        """Create enhanced prompt for GPT-5 blueprint analysis with superior vision AND HVAC calculation"""
        return f"""You are an expert HVAC load calculation specialist using GPT-5's advanced vision capabilities.
        
Analyze this residential blueprint AND calculate HVAC loads using ACCA Manual J methodology.

PROJECT LOCATION: ZIP CODE {zip_code}
This is CRITICAL for determining climate zone, design temperatures, and accurate load calculations.

ANALYSIS REQUIREMENTS:
1. Room Detection (use GPT-5's enhanced vision):
   - Identify EVERY room, closet, hallway, and space
   - Read ALL dimension annotations (e.g., 12'-6" x 10'-0")
   - Detect room labels and types from text
   - Calculate exact area in square feet
   - Note window and door locations/sizes

2. Scale Extraction:
   - Find and read the scale notation (typically 1/4"=1'-0" or 1/8"=1'-0")
   - Apply scale to all measurements consistently
   - Verify dimensions against scale

3. Building Envelope:
   - Identify exterior walls vs interior walls
   - Note building orientation (N/S/E/W if marked)
   - Detect insulation notations if present
   - Identify foundation type (slab/crawl/basement)

4. HVAC-Specific Data:
   - Window sizes and locations for heat gain
   - Door types (exterior/interior)
   - Ceiling heights if noted
   - Any existing HVAC equipment shown

5. HVAC Load Calculations (Using ZIP {zip_code} climate data):
   - Calculate heating BTU/hr for each room
   - Calculate cooling BTU/hr for each room
   - Consider climate zone for ZIP {zip_code}
   - Apply proper design temperatures for location
   - Include infiltration, ventilation, and duct losses
   - Size equipment properly with safety factors

Use GPT-5's superior reasoning to:
- Cross-verify dimensions for accuracy
- Detect partial/obscured text with context
- Identify non-standard room shapes
- Calculate accurate total square footage

Respond with a JSON object in this exact format:
{{
  "zip_code": "{zip_code}",
  "climate_zone": "<climate zone for {zip_code}>",
  "total_area_sqft": <number>,
  "num_floors": <number>,
  "building_type": "<residential/commercial/other>",
  "scale": "<scale notation from blueprint>",
  "rooms": [
    {{
      "name": "<room name from blueprint>",
      "room_type": "<bedroom/bathroom/kitchen/etc>",
      "width_ft": <number>,
      "length_ft": <number>,
      "area_sqft": <number>,
      "location": "<description>",
      "features": ["<feature1>", "<feature2>"],
      "confidence": <0.0-1.0>,
      "heating_btu_hr": <number>,
      "cooling_btu_hr": <number>
    }}
  ],
  "special_features": ["<garage>", "<basement>", "<deck>", etc],
  "confidence": <overall confidence 0.0-1.0>,
  "hvac_loads": {{
    "total_heating_btu_hr": <number>,
    "total_cooling_btu_hr": <number>,
    "heating_system_tons": <number>,
    "cooling_system_tons": <number>,
    "design_temps": {{
      "winter_design_temp_f": <number for {zip_code}>,
      "summer_design_temp_f": <number for {zip_code}>
    }},
    "calculation_method": "ACCA Manual J via GPT-5 Vision for ZIP {zip_code}"
  }}
}}

REMEMBER: Use ZIP code {zip_code} for all climate-specific calculations!"""
    
    def _analyze_with_gpt4v(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """Send image to GPT-5V/GPT-4V and get analysis with model fallback"""
        last_error = None
        
        # Try each model in order until one works
        for model in self.models_to_try:
            try:
                logger.info(f"Attempting blueprint analysis with {model}...")
                
                # Build request based on model type
                if model.startswith("gpt-5"):
                    # GPT-5 uses new parameters and direct image input
                    # GPT-5 ONLY supports default temperature (1.0)
                    response = self.client.chat.completions.create(
                        model=model,
                        timeout=30.0,  # 30-second timeout for GPT-5
                        messages=[
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
                        ],
                        max_completion_tokens=self.max_tokens,  # GPT-5 uses max_completion_tokens
                        # temperature=1.0,  # GPT-5 only supports default (1.0), omit for default
                        # GPT-5 specific parameters
                        extra_body={
                            "reasoning_effort": self.reasoning_effort,
                            "verbosity": self.verbosity
                        }
                    )
                else:
                    # GPT-4 fallback with standard parameters
                    response = self.client.chat.completions.create(
                        model=model,
                        timeout=30.0,  # 30-second timeout for GPT-4
                        messages=[
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
                        ],
                        max_tokens=min(self.max_tokens, 4096),  # GPT-4 limit
                        temperature=0.1
                    )
                
                # Successfully got a response with this model
                logger.info(f"✅ {model} responded successfully")
                
                # Extract JSON from response
                content = response.choices[0].message.content
                
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
        """Parse GPT-4V response into structured analysis"""
        
        # Parse rooms
        rooms = []
        for room_data in response.get("rooms", []):
            try:
                # Handle dimensions - might be None
                width = room_data.get("width_ft", 10) or 10
                length = room_data.get("length_ft", 10) or 10
                
                room = GPTRoom(
                    name=room_data.get("name", "Unknown"),
                    room_type=room_data.get("room_type", "unknown"),
                    dimensions_ft=(float(width), float(length)),
                    area_sqft=float(room_data.get("area_sqft", 100) or 100),
                    location=room_data.get("location", "") or "",
                    features=room_data.get("features", []) or [],
                    confidence=float(room_data.get("confidence", 0.5) or 0.5),
                    heating_btu_hr=float(room_data.get("heating_btu_hr", 0)) if "heating_btu_hr" in room_data else None,
                    cooling_btu_hr=float(room_data.get("cooling_btu_hr", 0)) if "cooling_btu_hr" in room_data else None
                )
                rooms.append(room)
            except Exception as e:
                logger.warning(f"Error parsing room: {e}")
        
        # Create analysis object with safe defaults
        total_area_value = response.get("total_area_sqft", 0)
        if isinstance(total_area_value, str):
            # Handle "Unknown" or other string values
            try:
                total_area_value = float(total_area_value)
            except (ValueError, TypeError):
                total_area_value = sum(r.area_sqft for r in rooms) if rooms else 0
        
        # Extract HVAC loads if provided by GPT-5
        hvac_loads = response.get("hvac_loads", {})
        
        analysis = GPTBlueprintAnalysis(
            total_area_sqft=float(total_area_value) if total_area_value else sum(r.area_sqft for r in rooms),
            num_floors=response.get("num_floors", 1),
            rooms=rooms,
            building_type=response.get("building_type", "residential"),
            special_features=response.get("special_features", []),
            scale=response.get("scale", "1/4\"=1'-0\""),
            confidence=float(response.get("confidence", 0.7)) if response.get("confidence") else 0.7,
            raw_response=response,
            zip_code=response.get("zip_code"),
            climate_zone=response.get("climate_zone"),
            total_heating_btu_hr=hvac_loads.get("total_heating_btu_hr"),
            total_cooling_btu_hr=hvac_loads.get("total_cooling_btu_hr"),
            heating_system_tons=hvac_loads.get("heating_system_tons"),
            cooling_system_tons=hvac_loads.get("cooling_system_tons")
        )
        
        return analysis
    
    def format_for_hvac(self, analysis: GPTBlueprintAnalysis) -> Dict[str, Any]:
        """Format GPT-5 Vision analysis for HVAC load calculations"""
        return {
            "success": True,
            "total_area": analysis.total_area_sqft,
            "rooms": [
                {
                    "name": room.name,
                    "area": room.area_sqft,
                    "room_type": room.room_type,
                    "width": room.dimensions_ft[0],
                    "height": room.dimensions_ft[1],
                    "features": room.features,
                    "confidence": room.confidence,
                    "heating_btu_hr": room.heating_btu_hr,
                    "cooling_btu_hr": room.cooling_btu_hr
                }
                for room in analysis.rooms
            ],
            "metadata": {
                "method": "GPT-5 Vision Analysis with HVAC Calculation",
                "building_type": analysis.building_type,
                "num_floors": analysis.num_floors,
                "special_features": analysis.special_features,
                "scale": analysis.scale,
                "confidence": analysis.confidence,
                "zip_code": analysis.zip_code,
                "climate_zone": analysis.climate_zone
            },
            "hvac_totals": {
                "total_heating_btu_hr": analysis.total_heating_btu_hr,
                "total_cooling_btu_hr": analysis.total_cooling_btu_hr,
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