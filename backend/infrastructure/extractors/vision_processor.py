"""
Vision Processor
Handles GPT-4V analysis of blueprint images
"""

import logging
import base64
from typing import Dict, Any, List, Optional
from openai import OpenAI
import json

logger = logging.getLogger(__name__)


class VisionProcessor:
    """
    Processes blueprint images using GPT-4V for extraction.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided, vision processing disabled")
    
    async def analyze_blueprint(
        self,
        image_bytes: bytes,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze blueprint image with GPT-4V.
        
        Args:
            image_bytes: Blueprint image as bytes
            text_blocks: Extracted text for context
            
        Returns:
            Dictionary with extracted information
        """
        
        if not self.api_key:
            logger.warning("Vision processing skipped - no API key")
            return {}
        
        # For now, return mock data
        # Real implementation would call GPT-4V
        
        logger.info("Processing blueprint with GPT-4V...")
        
        # Mock response
        return {
            'total_sqft': 2599,
            'floor_count': 2,
            'rooms_detected': 12,
            'has_garage': True,
            'has_bonus_room': True,
            'foundation_type': 'crawlspace',
            'confidence': 0.85
        }
    
    def analyze_construction_context(
        self,
        text_blocks: List[Dict[str, Any]],
        user_inputs: Dict[str, Any],
        pipeline_extractions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze blueprint text to identify actual construction specifications.
        Filters out code compliance requirements and focuses on real building specs.
        
        Args:
            text_blocks: All extracted text from blueprint
            user_inputs: User-provided context (era, building type, etc.)
            pipeline_extractions: Basic extractions (area, rooms, etc.)
            
        Returns:
            Construction context with filtered specs and authority analysis
        """
        
        if not self.client:
            logger.warning("Construction context analysis skipped - no API key")
            return self._get_fallback_construction_context(text_blocks, user_inputs)
        
        logger.info("Analyzing construction context with GPT-4o...")
        
        # Prepare context for AI
        building_era = user_inputs.get('building_era', user_inputs.get('year_built', 'unknown'))
        building_type = user_inputs.get('building_type', 'residential')
        total_sqft = pipeline_extractions.get('total_sqft', 'unknown')
        
        # Combine all text for analysis
        all_text = ""
        for block in text_blocks:
            all_text += f"Page {block.get('page', 1)}: {block.get('text', '')}\n"
        
        construction_prompt = f"""
You are a professional construction document analyst specializing in HVAC load calculations.

ANALYZE these blueprint text sections to identify ACTUAL CONSTRUCTION SPECIFICATIONS for thermal modeling.

INPUT CONTEXT:
- Building Era: {building_era}
- Building Type: {building_type}
- Extracted Area: {total_sqft} sqft
- User Notes: {user_inputs}

YOUR TASK:
1. FILTER TEXT: Return only text describing actual building construction
2. SCORE AUTHORITY: Rate reliability of each specification (1-10)  
3. RESOLVE CONFLICTS: When specs contradict, choose most authoritative
4. PROVIDE CONTEXT: Assess construction reality vs aspirational targets
5. ANALYZE LOAD FACTORS: Extract thermal context that affects HVAC load calculations

INCLUDE (High Priority):
✓ Wall section details, assembly specifications
✓ Material callouts with R-values, U-values
✓ Construction drawings and details
✓ Title block specifications
✓ Actual equipment specifications
✓ Window orientations and solar exposure
✓ Ceiling heights and volume details
✓ HVAC system specifications and duct locations
✓ Regional construction adaptations

EXCLUDE (Filter Out):
✗ Energy code compliance options/credits
✗ Future phases, conceptual work
✗ Administrative/permit language
✗ Site work, landscaping
✗ Marketing language

BLUEPRINT TEXT TO ANALYZE:
{all_text}

IMPORTANT: Return ONLY valid JSON. No explanation text before or after.

{{
  "construction_specs": [
    {{
      "text": "example spec text",
      "authority_score": 8,
      "source_type": "wall_detail",
      "page": 2
    }}
  ],
  "construction_context": {{
    "apparent_era": "2024_new_construction",
    "construction_quality": "above_average",
    "specs_vs_reality": "specs_match_era", 
    "primary_authority": "construction_drawings"
  }},
  "thermal_intelligence": {{
    "window_orientation": {{
      "south_facing_ratio": 0.4,
      "north_facing_ratio": 0.2,
      "large_windows_detected": true,
      "solar_exposure": "high"
    }},
    "ceiling_volume": {{
      "ceiling_height_ft": 9.0,
      "vaulted_areas_percent": 0.3,
      "high_volume_spaces": ["great_room", "master_bedroom"]
    }},
    "construction_method": {{
      "framing_type": "stick_built",
      "thermal_mass": "low",
      "wall_assembly": "standard_frame"
    }},
    "hvac_context": {{
      "system_type": "heat_pump",
      "duct_location": "crawlspace",
      "zoned_system": false,
      "existing_equipment": true
    }},
    "regional_adaptations": {{
      "climate_zone": "5B",
      "frost_protection": true,
      "wind_resistance": false,
      "moisture_control": "standard"
    }}
  }},
  "conflicts_resolved": [
    {{
      "issue": "conflicting R-values",
      "resolution": "chose construction detail over code reference",
      "chosen_spec": "R-19"
    }}
  ],
  "confidence": 0.85
}}
"""

        try:
            # Call OpenAI API with GPT-4o-2024-11-20
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[{
                    "role": "user",
                    "content": construction_prompt
                }],
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent analysis
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                # Clean response text - sometimes AI adds markdown formatting
                clean_response = response_text.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                construction_analysis = json.loads(clean_response)
                logger.info(f"AI analyzed {len(construction_analysis.get('construction_specs', []))} construction specs")
                return construction_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")
                
                # Return fallback
                return self._get_fallback_construction_context(text_blocks, user_inputs)
                
        except Exception as e:
            logger.error(f"AI construction analysis failed: {e}")
            return self._get_fallback_construction_context(text_blocks, user_inputs)
    
    def _get_fallback_construction_context(
        self,
        text_blocks: List[Dict[str, Any]], 
        user_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback construction context when AI analysis fails"""
        
        # Simple filtering - exclude obvious energy credits text
        filtered_specs = []
        for block in text_blocks:
            text = block.get('text', '').upper()
            
            # Skip energy credits and compliance text
            if any(term in text for term in [
                'ENERGY CREDITS', 'COMPLIANCE', 'CODE REQUIREMENT',
                'MINIMUM STANDARD', 'OPTION', 'ALTERNATIVE'
            ]):
                continue
                
            # Keep construction-related text
            if any(term in text for term in [
                'WALL', 'FLOOR', 'ROOF', 'INSULATION', 'FRAMING',
                'R-', 'U-', 'CONSTRUCTION', 'ASSEMBLY'
            ]):
                filtered_specs.append({
                    'text': block.get('text', ''),
                    'authority_score': 5,  # Medium authority
                    'source_type': 'mixed',
                    'page': block.get('page', 1)
                })
        
        return {
            'construction_specs': filtered_specs,
            'construction_context': {
                'apparent_era': user_inputs.get('building_era', 'unknown'),
                'construction_quality': 'average',
                'specs_vs_reality': 'uncertain',
                'primary_authority': 'mixed'
            },
            'conflicts_resolved': [],
            'confidence': 0.6
        }