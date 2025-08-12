"""
GPT-4V Blueprint Analysis Prompts
Multi-version prompt system with fallback strategies
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BlueprintPromptManager:
    """Manages multiple prompt versions for GPT-4V blueprint analysis"""
    
    def __init__(self):
        self.prompt_versions = {
            "v1_structured": self._create_v1_structured_prompt,
            "v2_guided": self._create_v2_guided_prompt,
            "v3_simplified": self._create_v3_simplified_prompt,
            "v4_minimal": self._create_v4_minimal_prompt
        }
        self.current_version = "v1_structured"
    
    def get_prompt(self, version: str, zip_code: str, floor_hint: int = None) -> str:
        """
        Get a specific prompt version
        
        Args:
            version: Prompt version key
            zip_code: Project ZIP code
            floor_hint: Optional floor number hint
        """
        if version not in self.prompt_versions:
            logger.warning(f"Unknown prompt version {version}, using v1_structured")
            version = "v1_structured"
        
        return self.prompt_versions[version](zip_code, floor_hint)
    
    def _create_v1_structured_prompt(self, zip_code: str, floor_hint: int = None) -> str:
        """Version 1: Highly structured with explicit instructions"""
        floor_str = f"(Expected floor: {floor_hint})" if floor_hint else ""
        
        return f"""You are analyzing a residential blueprint image using advanced computer vision.
        
CRITICAL: You MUST analyze the actual blueprint image provided. Extract real room names, dimensions, and layout.

Location: ZIP {zip_code} {floor_str}

STEP-BY-STEP ANALYSIS:

1. FLOOR IDENTIFICATION:
   - What floor is shown? (First/Second/Basement)
   - Are there stairs indicating other floors?
   - Total floors in building?

2. ROOM EXTRACTION:
   - List EVERY room visible with its label
   - Extract dimensions from the blueprint
   - Identify room types (bedroom, bathroom, kitchen, etc.)
   - Note which walls are exterior

3. DIMENSION CALCULATION:
   - Find the scale notation
   - Convert all dimensions to feet
   - Calculate area for each room

4. HVAC LOAD FACTORS:
   - Exterior wall count per room
   - Window presence and size
   - Ceiling type (to attic or another floor)

REQUIRED JSON OUTPUT:
{{
  "analysis_version": "v1_structured",
  "zip_code": "{zip_code}",
  "confidence": 0.0-1.0,
  "floor_info": {{
    "current_floor": 1,
    "floor_name": "First Floor",
    "total_floors": 2,
    "has_stairs_up": true/false,
    "has_stairs_down": true/false
  }},
  "rooms": [
    {{
      "name": "Room Name from Blueprint",
      "type": "bedroom/bathroom/kitchen/living/dining/hallway/closet",
      "dimensions": {{
        "width_ft": 12.5,
        "length_ft": 10.0,
        "area_sqft": 125
      }},
      "exterior_walls": 0-4,
      "has_windows": true/false,
      "ceiling_to_exterior": true/false,
      "floor_above_ground": true/false
    }}
  ],
  "total_area_sqft": 2000,
  "room_count": 10
}}

IMPORTANT: Analyze the ACTUAL blueprint image. Do not generate placeholder data."""
    
    def _create_v2_guided_prompt(self, zip_code: str, floor_hint: int = None) -> str:
        """Version 2: More conversational with examples"""
        return f"""I need you to analyze this residential blueprint image for HVAC load calculations.

Location: ZIP code {zip_code}

Please look at the blueprint and tell me:

1. WHICH FLOOR IS THIS?
   Look for labels like "First Floor", "Second Floor", "Basement"
   Check if there are stairs going up or down

2. WHAT ROOMS DO YOU SEE?
   Read each room label carefully
   Note the dimensions shown on the blueprint
   Identify the room type (bedroom, bathroom, kitchen, etc.)

3. ROOM DETAILS FOR HVAC:
   For each room, count:
   - How many exterior walls (walls touching outside)
   - Are there windows?
   - Is the ceiling to another floor or to the attic/roof?

Example of what you might see:
- "Master Bedroom 14'x16'"
- "Kitchen 12'x14'"
- "Bath 8'x10'"

Return your analysis as JSON:
{{
  "analysis_version": "v2_guided",
  "zip_code": "{zip_code}",
  "floor_number": 1,
  "floor_name": "First Floor",
  "rooms": [
    {{
      "name": "Master Bedroom",
      "type": "bedroom",
      "width_ft": 14,
      "length_ft": 16,
      "area_sqft": 224,
      "exterior_walls": 2,
      "has_windows": true
    }},
    // ... more rooms
  ],
  "total_area_sqft": 1800
}}"""
    
    def _create_v3_simplified_prompt(self, zip_code: str, floor_hint: int = None) -> str:
        """Version 3: Very simple and direct"""
        return f"""Analyze this blueprint image.

ZIP: {zip_code}

List all rooms with dimensions:

{{
  "analysis_version": "v3_simplified",
  "zip_code": "{zip_code}",
  "floor": 1,
  "rooms": [
    {{
      "name": "Living Room",
      "width_ft": 20,
      "length_ft": 15,
      "area_sqft": 300,
      "exterior_walls": 2
    }}
  ],
  "total_sqft": 2000
}}"""
    
    def _create_v4_minimal_prompt(self, zip_code: str, floor_hint: int = None) -> str:
        """Version 4: Absolute minimum - just extract what you can see"""
        return f"""Extract rooms from blueprint. ZIP {zip_code}.

Return JSON:
{{
  "analysis_version": "v4_minimal",
  "rooms": [
    {{"name": "room_name", "area_sqft": 100}}
  ]
}}"""
    
    def validate_response(self, response: Dict[str, Any], min_rooms: int = 5) -> tuple[bool, str]:
        """
        Validate a GPT-4V response
        
        Returns:
            (is_valid, error_message)
        """
        # Check for minimum rooms
        if 'rooms' not in response:
            return False, "No rooms found in response"
        
        room_count = len(response.get('rooms', []))
        if room_count < min_rooms:
            return False, f"Only {room_count} rooms found (minimum {min_rooms} expected)"
        
        # Check for reasonable total area
        total_area = response.get('total_area_sqft', 0) or response.get('total_sqft', 0)
        if total_area < 500:
            return False, f"Total area {total_area} sq ft is too small for residential"
        
        if total_area > 10000:
            return False, f"Total area {total_area} sq ft is unusually large"
        
        # Check that rooms have required fields
        for room in response.get('rooms', []):
            if 'name' not in room:
                return False, "Room missing name"
            
            area = room.get('area_sqft', 0)
            if area <= 0:
                # Try to calculate from dimensions
                width = room.get('width_ft', 0) or room.get('dimensions', {}).get('width_ft', 0)
                length = room.get('length_ft', 0) or room.get('dimensions', {}).get('length_ft', 0)
                if width > 0 and length > 0:
                    room['area_sqft'] = width * length
                else:
                    return False, f"Room {room.get('name', 'unknown')} has no valid area"
        
        # Check floor assignment if multi-story
        if 'floor_info' in response or 'floor' in response:
            floor_num = response.get('floor_info', {}).get('current_floor', 0) or response.get('floor', 0)
            if floor_num < 0 or floor_num > 5:
                return False, f"Invalid floor number: {floor_num}"
        
        return True, ""
    
    def get_next_version(self, current_version: str) -> str:
        """Get the next prompt version to try"""
        versions = list(self.prompt_versions.keys())
        try:
            current_idx = versions.index(current_version)
            if current_idx < len(versions) - 1:
                return versions[current_idx + 1]
        except ValueError:
            pass
        return None


# Global instance
blueprint_prompt_manager = BlueprintPromptManager()