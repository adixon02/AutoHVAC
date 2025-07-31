"""
Enhanced Building Envelope Data Extraction Service
Extracts R-values, U-factors, construction details from blueprint PDFs using OpenAI
"""

import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import os
from openai import AsyncOpenAI
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence levels for AI extractions"""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # >= 0.6
    LOW = "low"        # < 0.6


@dataclass
class EnvelopeExtraction:
    """Data structure for envelope extraction results"""
    # Wall properties (required)
    wall_construction: str
    wall_r_value: float
    wall_u_factor: float
    wall_confidence: float
    
    # Roof properties (required)
    roof_construction: str
    roof_r_value: float
    roof_u_factor: float
    roof_confidence: float
    
    # Floor properties (required)
    floor_construction: str
    floor_r_value: float
    floor_u_factor: float
    floor_confidence: float
    
    # Window properties (required)
    window_type: str
    window_u_factor: float
    window_shgc: float
    window_confidence: float
    
    # Building details (required)
    ceiling_height: float
    ceiling_height_confidence: float
    
    infiltration_class: str  # "tight", "code", "loose"
    infiltration_confidence: float
    
    # Construction vintage (required)
    estimated_vintage: str
    vintage_confidence: float
    
    # Overall extraction quality (required)
    overall_confidence: float
    needs_confirmation: List[str]  # Fields that need user confirmation
    
    # Optional wall details
    wall_cavity_insulation: Optional[str] = None
    wall_continuous_insulation: Optional[str] = None
    wall_air_barrier: Optional[str] = None
    
    # Optional roof details
    roof_ventilation: Optional[str] = None
    roof_radiant_barrier: bool = False
    
    # Optional floor details
    floor_perimeter_insulation: Optional[str] = None
    floor_vapor_barrier: bool = False
    
    # Optional window details
    window_frame_type: Optional[str] = None
    
    # Door properties (with defaults)
    door_type: Optional[str] = None
    door_u_factor: float = 0.40
    door_count: int = 1
    door_confidence: float = 0.4
    
    # Optional building details
    ceiling_height_variations: Optional[str] = None
    blower_door_result: Optional[str] = None
    
    # Mechanical systems (optional)
    mechanical_ventilation: Optional[str] = None
    duct_location: Optional[str] = None
    
    # Thermal mass (optional with defaults)
    thermal_mass_walls: Optional[str] = None
    exposed_slab: bool = False
    thermal_mass_confidence: float = 0.4
    
    def get_confidence_level(self, field: str) -> ConfidenceLevel:
        """Get confidence level enum for a field"""
        confidence_map = {
            'wall': self.wall_confidence,
            'roof': self.roof_confidence, 
            'floor': self.floor_confidence,
            'window': self.window_confidence,
            'ceiling_height': self.ceiling_height_confidence,
            'infiltration': self.infiltration_confidence,
            'vintage': self.vintage_confidence,
            'overall': self.overall_confidence
        }
        
        confidence = confidence_map.get(field, 0.0)
        
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


class EnvelopeExtractorError(Exception):
    """Custom exception for envelope extraction failures"""
    pass


def scrub_pii(text_content: str) -> str:
    """
    Scrub personally identifiable information from blueprint text
    
    Args:
        text_content: Raw text content from blueprint
        
    Returns:
        Scrubbed text with PII removed/masked
    """
    # Remove common PII patterns
    scrubbed = text_content
    
    # Remove names (patterns like "John Smith", "Jane Doe")
    # Keep architectural terms but remove owner/designer names
    scrubbed = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', '[NAME]', scrubbed)
    
    # Remove phone numbers
    scrubbed = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', scrubbed)
    
    # Remove email addresses
    scrubbed = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', scrubbed)
    
    # Remove addresses (street numbers and names)
    scrubbed = re.sub(r'\b\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Circle|Cir|Boulevard|Blvd)\b', '[ADDRESS]', scrubbed)
    
    # Remove SSN patterns
    scrubbed = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', scrubbed)
    
    # Remove credit card patterns  
    scrubbed = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', scrubbed)
    
    # Keep architectural/construction terms but remove personal project titles
    # Remove phrases like "Smith Residence", "Jones House", etc.
    scrubbed = re.sub(r'\b[A-Z][a-z]+\s+(?:Residence|House|Home|Estate|Property|Building)\b', '[PROJECT]', scrubbed)
    
    return scrubbed


async def extract_envelope_data(blueprint_text: str, notes_text: str = "", 
                              zip_code: str = "90210") -> EnvelopeExtraction:
    """
    Extract building envelope data from blueprint text using OpenAI
    
    Args:
        blueprint_text: Raw text extracted from blueprint PDF
        notes_text: Additional notes/specifications text
        zip_code: Project location for context
        
    Returns:
        EnvelopeExtraction with building envelope properties and confidence scores
        
    Raises:
        EnvelopeExtractorError: If extraction fails
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    if not client.api_key:
        raise EnvelopeExtractorError("OPENAI_API_KEY environment variable not set")
    
    # Scrub PII from input text
    scrubbed_blueprint = scrub_pii(blueprint_text)
    scrubbed_notes = scrub_pii(notes_text)
    
    # Prepare context
    context = _prepare_envelope_context(scrubbed_blueprint, scrubbed_notes, zip_code)
    
    # Generate system prompt
    system_prompt = _generate_envelope_system_prompt()
    
    try:
        # Call OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # Create EnvelopeExtraction object
        extraction = _parse_extraction_result(result_json)
        
        # Identify fields needing confirmation
        extraction.needs_confirmation = _identify_low_confidence_fields(extraction)
        
        return extraction
        
    except json.JSONDecodeError as e:
        raise EnvelopeExtractorError(f"Failed to parse AI response as JSON: {e}")
    except TypeError as e:
        if "proxies" in str(e):
            raise EnvelopeExtractorError(f"OpenAI client configuration error - please update dependencies: {e}")
        raise EnvelopeExtractorError(f"OpenAI API call failed (type error): {e}")
    except Exception as e:
        # Handle common httpx/connection errors
        error_msg = str(e).lower()
        if "proxies" in error_msg:
            raise EnvelopeExtractorError(f"HTTP client configuration error - please update OpenAI library: {e}")
        elif "connection" in error_msg or "timeout" in error_msg:
            raise EnvelopeExtractorError(f"Network connection error during envelope extraction: {e}")
        elif "unauthorized" in error_msg or "401" in error_msg:
            raise EnvelopeExtractorError(f"OpenAI API authentication failed - check API key: {e}")
        elif "rate limit" in error_msg or "429" in error_msg:
            raise EnvelopeExtractorError(f"OpenAI API rate limit exceeded: {e}")
        else:
            raise EnvelopeExtractorError(f"OpenAI API call failed: {e}")


def _prepare_envelope_context(blueprint_text: str, notes_text: str, zip_code: str) -> str:
    """Prepare context for envelope data extraction"""
    
    context = f"""
BUILDING ENVELOPE DATA EXTRACTION REQUEST

Project Location: {zip_code}

BLUEPRINT TEXT CONTENT:
{blueprint_text[:3000]}  

NOTES/SPECIFICATIONS:
{notes_text[:1000]}

Please analyze this architectural blueprint and specification text to extract building envelope properties.
Look for specific mentions of:
- Wall construction and insulation (R-values, U-factors)
- Roof/ceiling insulation specifications  
- Floor insulation details
- Window types and performance ratings
- Ceiling heights
- Construction vintage indicators
- Air sealing/infiltration details

Provide confidence scores (0.0-1.0) for each extraction based on how explicitly the information is stated.
"""
    
    return context


def _generate_envelope_system_prompt() -> str:
    """Generate system prompt for envelope data extraction"""
    
    return """You are an expert at extracting building envelope data from architectural blueprints and specifications for HVAC load calculations.

Your task is to analyze blueprint text and extract specific building envelope properties with confidence scores.

EXTRACTION REQUIREMENTS:

1. WALL PROPERTIES:
   - Construction type (e.g., "2x4 frame", "2x6 frame", "masonry", "concrete", "ICF", "SIP")
   - R-value (if specified, otherwise estimate based on construction type)
   - U-factor (calculate as 1/R-value)
   - Cavity insulation type (e.g., "fiberglass batt", "spray foam", "cellulose")
   - Continuous insulation (e.g., "1 inch foam board R-5")
   - Air barrier details (e.g., "house wrap", "sealed sheathing")
   - Confidence score based on how explicitly stated

2. ROOF PROPERTIES:
   - Construction type (e.g., "attic insulation", "cathedral ceiling", "flat roof", "SIP roof")
   - R-value (common values: R-19, R-30, R-38, R-49, R-60)
   - U-factor (calculate as 1/R-value)
   - Ventilation type (e.g., "vented attic", "hot roof", "conditioned attic")
   - Radiant barrier (yes/no)
   - Confidence score

3. FLOOR PROPERTIES:
   - Construction type (e.g., "slab on grade", "crawl space", "basement", "raised floor")
   - R-value (common values: R-11, R-19, R-25, R-30)
   - U-factor (calculate as 1/R-value)
   - Perimeter insulation for slabs (e.g., "R-10 2ft deep")
   - Vapor barrier details
   - Confidence score

4. WINDOW PROPERTIES:
   - Type (e.g., "single pane", "double pane", "low-e", "triple pane", "argon filled")
   - U-factor (typical range: 0.20-0.80)
   - SHGC - Solar Heat Gain Coefficient (typical range: 0.20-0.70)
   - Frame type (e.g., "aluminum", "vinyl", "wood", "fiberglass")
   - Glazing area by orientation if available
   - Confidence score

5. DOOR PROPERTIES:
   - Type (e.g., "solid wood", "steel insulated", "fiberglass", "glass sliding")
   - U-factor (typical range: 0.20-0.70)
   - Count and locations
   - Confidence score

6. BUILDING DETAILS:
   - Ceiling height in feet (typical: 8-12 ft, note variations)
   - Infiltration class ("tight", "code", "loose") based on construction notes
   - Blower door results if available (e.g., "3 ACH50", "1200 CFM50")
   - Mechanical ventilation type (e.g., "HRV", "ERV", "exhaust only")
   - Duct location (e.g., "conditioned space", "attic", "crawl space")
   - Estimated construction vintage ("pre-1980", "1980-2000", "2000-2020", "current-code")

7. THERMAL MASS:
   - Interior mass walls (e.g., "concrete", "brick", "none")
   - Exposed slab (yes/no and area)
   - Mass wall thickness if applicable

CONFIDENCE SCORING:
- 1.0: Explicitly stated with specific values
- 0.8: Clearly implied from construction details
- 0.6: Reasonable inference from context
- 0.4: Educated guess based on typical values
- 0.2: Very uncertain, using fallback defaults

OUTPUT FORMAT - Return valid JSON only:

{
  "wall_construction": "string",
  "wall_r_value": number,
  "wall_u_factor": number,
  "wall_cavity_insulation": "string",
  "wall_continuous_insulation": "string",
  "wall_air_barrier": "string",
  "wall_confidence": number,
  
  "roof_construction": "string", 
  "roof_r_value": number,
  "roof_u_factor": number,
  "roof_ventilation": "string",
  "roof_radiant_barrier": boolean,
  "roof_confidence": number,
  
  "floor_construction": "string",
  "floor_r_value": number,
  "floor_u_factor": number,
  "floor_perimeter_insulation": "string",
  "floor_vapor_barrier": boolean,
  "floor_confidence": number,
  
  "window_type": "string",
  "window_u_factor": number,
  "window_shgc": number,
  "window_frame_type": "string",
  "window_confidence": number,
  
  "door_type": "string",
  "door_u_factor": number,
  "door_count": number,
  "door_confidence": number,
  
  "ceiling_height": number,
  "ceiling_height_variations": "string",
  "ceiling_height_confidence": number,
  
  "infiltration_class": "string",
  "blower_door_result": "string",
  "infiltration_confidence": number,
  
  "mechanical_ventilation": "string",
  "duct_location": "string",
  
  "thermal_mass_walls": "string",
  "exposed_slab": boolean,
  "thermal_mass_confidence": number,
  
  "estimated_vintage": "string",
  "vintage_confidence": number,
  
  "overall_confidence": number
}

ESTIMATION GUIDELINES:

Wall R-values by type:
- 2x4 frame basic: R-11 to R-13
- 2x4 frame high-perf: R-15 to R-20  
- 2x6 frame: R-19 to R-25
- ICF: R-22 to R-30
- SIP: R-15 to R-30
- Masonry: R-5 to R-15
- Current code: R-20+ (climate dependent)

Window U-factors by type:
- Single pane: 0.80-1.00
- Double pane clear: 0.45-0.60
- Double pane Low-E: 0.25-0.40
- Triple pane: 0.15-0.30
- Low-E argon filled: 0.22-0.35

Door U-factors by type:
- Solid wood: 0.40-0.60
- Steel insulated: 0.20-0.40
- Fiberglass: 0.15-0.30
- Glass sliding: 0.30-0.70

Focus on practical HVAC design accuracy. If specific values aren't found, use reasonable estimates based on construction type and vintage with appropriate confidence scores."""


def _parse_extraction_result(result_json: Dict[str, Any]) -> EnvelopeExtraction:
    """Parse JSON result into EnvelopeExtraction object"""
    
    try:
        return EnvelopeExtraction(
            # Wall properties
            wall_construction=result_json.get("wall_construction", "Unknown"),
            wall_r_value=float(result_json.get("wall_r_value", 11.0)),
            wall_u_factor=float(result_json.get("wall_u_factor", 0.09)),
            wall_confidence=float(result_json.get("wall_confidence", 0.4)),
            wall_cavity_insulation=result_json.get("wall_cavity_insulation"),
            wall_continuous_insulation=result_json.get("wall_continuous_insulation"),
            wall_air_barrier=result_json.get("wall_air_barrier"),
            
            # Roof properties
            roof_construction=result_json.get("roof_construction", "Unknown"),
            roof_r_value=float(result_json.get("roof_r_value", 30.0)),
            roof_u_factor=float(result_json.get("roof_u_factor", 0.033)),
            roof_confidence=float(result_json.get("roof_confidence", 0.4)),
            roof_ventilation=result_json.get("roof_ventilation"),
            roof_radiant_barrier=bool(result_json.get("roof_radiant_barrier", False)),
            
            # Floor properties
            floor_construction=result_json.get("floor_construction", "Unknown"),
            floor_r_value=float(result_json.get("floor_r_value", 19.0)),
            floor_u_factor=float(result_json.get("floor_u_factor", 0.053)),
            floor_confidence=float(result_json.get("floor_confidence", 0.4)),
            floor_perimeter_insulation=result_json.get("floor_perimeter_insulation"),
            floor_vapor_barrier=bool(result_json.get("floor_vapor_barrier", False)),
            
            # Window properties
            window_type=result_json.get("window_type", "Double pane"),
            window_u_factor=float(result_json.get("window_u_factor", 0.50)),
            window_shgc=float(result_json.get("window_shgc", 0.60)),
            window_confidence=float(result_json.get("window_confidence", 0.4)),
            window_frame_type=result_json.get("window_frame_type"),
            
            # Door properties
            door_type=result_json.get("door_type", "Steel insulated"),
            door_u_factor=float(result_json.get("door_u_factor", 0.40)),
            door_count=int(result_json.get("door_count", 1)),
            door_confidence=float(result_json.get("door_confidence", 0.4)),
            
            # Building details
            ceiling_height=float(result_json.get("ceiling_height", 9.0)),
            ceiling_height_confidence=float(result_json.get("ceiling_height_confidence", 0.4)),
            ceiling_height_variations=result_json.get("ceiling_height_variations"),
            
            # Infiltration
            infiltration_class=result_json.get("infiltration_class", "code"),
            infiltration_confidence=float(result_json.get("infiltration_confidence", 0.4)),
            blower_door_result=result_json.get("blower_door_result"),
            
            # Mechanical systems
            mechanical_ventilation=result_json.get("mechanical_ventilation"),
            duct_location=result_json.get("duct_location"),
            
            # Thermal mass
            thermal_mass_walls=result_json.get("thermal_mass_walls"),
            exposed_slab=bool(result_json.get("exposed_slab", False)),
            thermal_mass_confidence=float(result_json.get("thermal_mass_confidence", 0.4)),
            
            # Vintage
            estimated_vintage=result_json.get("estimated_vintage", "1980-2000"),
            vintage_confidence=float(result_json.get("vintage_confidence", 0.4)),
            
            overall_confidence=float(result_json.get("overall_confidence", 0.4)),
            needs_confirmation=[]
        )
        
    except (ValueError, TypeError) as e:
        raise EnvelopeExtractorError(f"Failed to parse extraction result: {e}")


def _identify_low_confidence_fields(extraction: EnvelopeExtraction) -> List[str]:
    """Identify fields that need user confirmation due to low confidence"""
    
    LOW_CONFIDENCE_THRESHOLD = 0.6
    needs_confirmation = []
    
    confidence_fields = {
        "Wall construction and R-value": extraction.wall_confidence,
        "Roof construction and R-value": extraction.roof_confidence,
        "Floor construction and R-value": extraction.floor_confidence,
        "Window type and performance": extraction.window_confidence,
        "Ceiling height": extraction.ceiling_height_confidence,
        "Infiltration class": extraction.infiltration_confidence,
        "Construction vintage": extraction.vintage_confidence
    }
    
    for field_name, confidence in confidence_fields.items():
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            needs_confirmation.append(field_name)
    
    return needs_confirmation


async def test_envelope_extraction():
    """Test function for envelope extraction"""
    
    sample_text = """
    CONSTRUCTION SPECIFICATIONS
    
    WALLS: 2x6 FRAME CONSTRUCTION WITH R-21 INSULATION
    WINDOWS: LOW-E DOUBLE PANE, U=0.30
    ROOF: R-38 BLOWN-IN ATTIC INSULATION  
    FLOOR: SLAB ON GRADE WITH R-10 PERIMETER INSULATION
    CEILING HEIGHT: 9'-0"
    
    NOTES:
    - House wrap and sealed construction per 2018 IRC
    - Energy Star certified windows
    - Continuous air barrier system
    """
    
    try:
        result = await extract_envelope_data(sample_text, zip_code="90210")
        
        print("Envelope Extraction Test Result:")
        print(f"Wall: {result.wall_construction}, R-{result.wall_r_value} (confidence: {result.wall_confidence:.2f})")
        print(f"Roof: {result.roof_construction}, R-{result.roof_r_value} (confidence: {result.roof_confidence:.2f})")
        print(f"Windows: {result.window_type}, U={result.window_u_factor} (confidence: {result.window_confidence:.2f})")
        print(f"Ceiling Height: {result.ceiling_height} ft (confidence: {result.ceiling_height_confidence:.2f})")
        print(f"Overall Confidence: {result.overall_confidence:.2f}")
        
        if result.needs_confirmation:
            print(f"Needs Confirmation: {', '.join(result.needs_confirmation)}")
        
        return True
        
    except Exception as e:
        print(f"Envelope Extraction Test Failed: {e}")
        return False


if __name__ == "__main__":
    # Run test
    asyncio.run(test_envelope_extraction())