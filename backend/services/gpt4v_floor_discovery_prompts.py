"""
GPT-4V Floor Discovery Prompts

This module lets GPT-4V determine floor types from blueprint content
rather than forcing labels based on PDF text that may be incorrect.

NO BAND-AID FIXES: This addresses the ROOT CAUSE of GPT-4V rejecting pages
when we tell it the wrong floor type. Let GPT-4V figure it out itself!
"""

import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class FloorDiscoveryPromptManager:
    """
    Creates prompts that let GPT-4V discover the floor type from content
    
    ROOT CAUSE FIX: PDF labels like "SECOND FLOOR" are often wrong.
    GPT-4V can determine the actual floor type from room patterns.
    """
    
    def get_floor_discovery_prompt(
        self,
        zip_code: str,
        page_number: int,
        page_text_hint: Optional[str] = None,  # What the PDF says (may be wrong!)
        previous_floors: Optional[List[Dict]] = None,
        building_context: Optional[Dict] = None
    ) -> str:
        """
        Generate a prompt that lets GPT-4V determine the floor type
        
        Args:
            zip_code: Project ZIP code
            page_number: Current page number (0-indexed)
            page_text_hint: Text label from PDF (treated as hint only)
            previous_floors: Analysis results from previous floors
            building_context: Overall building context if available
            
        Returns:
            Discovery prompt that doesn't force a floor type
        """
        # Build context from previous floors
        context_str = self._build_context_string(previous_floors, building_context)
        
        # Build hint about what we've seen so far
        floors_found = self._summarize_floors_found(previous_floors)
        
        return self._create_discovery_prompt(
            zip_code, page_number, page_text_hint, 
            context_str, floors_found
        )
    
    def _build_context_string(
        self, 
        previous_floors: Optional[List[Dict]],
        building_context: Optional[Dict]
    ) -> str:
        """Build context from what we've analyzed so far"""
        if not previous_floors:
            return "This appears to be the first floor plan page."
        
        parts = ["CONTEXT FROM PREVIOUS PAGES:"]
        
        for i, floor in enumerate(previous_floors):
            floor_type = floor.get("floor_type", "unknown")
            room_count = len(floor.get("rooms", []))
            total_area = floor.get("total_area", 0)
            has_kitchen = floor.get("has_kitchen", False)
            
            summary = f"Page {i+1}: {floor_type.title()} floor - {room_count} rooms, {total_area:.0f} sqft"
            if has_kitchen:
                summary += " (has kitchen - confirmed main floor)"
            
            parts.append(summary)
        
        if building_context:
            if building_context.get("expected_stories"):
                parts.append(f"\nBuilding appears to be {building_context['expected_stories']} stories")
            if building_context.get("has_bonus_expectation"):
                parts.append("Note: May have bonus room over garage")
        
        return "\n".join(parts)
    
    def _summarize_floors_found(self, previous_floors: Optional[List[Dict]]) -> Dict:
        """Summarize what floor types we've found"""
        summary = {
            "has_main": False,
            "has_upper": False,
            "has_bonus": False,
            "has_basement": False,
            "main_floor_area": 0
        }
        
        if not previous_floors:
            return summary
        
        for floor in previous_floors:
            floor_type = floor.get("floor_type", "").lower()
            if "main" in floor_type or floor.get("has_kitchen"):
                summary["has_main"] = True
                summary["main_floor_area"] = floor.get("total_area", 0)
            elif "upper" in floor_type or "second" in floor_type:
                summary["has_upper"] = True
            elif "bonus" in floor_type:
                summary["has_bonus"] = True
            elif "basement" in floor_type:
                summary["has_basement"] = True
        
        return summary
    
    def _create_discovery_prompt(
        self,
        zip_code: str,
        page_number: int,
        page_text_hint: Optional[str],
        context_str: str,
        floors_found: Dict
    ) -> str:
        """Create the discovery prompt"""
        
        # Build expectations based on what we've seen
        expectations = []
        if not floors_found["has_main"]:
            expectations.append("- Main floor (should have kitchen, living, dining)")
        elif not floors_found["has_upper"] and not floors_found["has_bonus"]:
            expectations.append("- Upper floor (bedrooms, bathrooms)")
            expectations.append("- OR Bonus room (1-3 rooms over garage)")
        elif floors_found["has_main"] and floors_found["has_upper"]:
            expectations.append("- Possibly basement or additional floor")
        
        expectations_str = "\n".join(expectations) if expectations else "- Additional floor plan"
        
        # Include page text as a hint only
        hint_str = ""
        if page_text_hint:
            hint_str = f"""
PAGE TEXT (MAY BE INCORRECT): The PDF labels this as "{page_text_hint}"
IMPORTANT: This label may be wrong! Determine the actual floor type from the rooms you see."""
        
        prompt = f"""You are analyzing page {page_number + 1} of a residential blueprint.

{context_str}

YOUR TASK: Determine what floor this blueprint page shows based on the rooms present.

CRITICAL: For EVERY room you identify:
1. MEASURE the dimensions in feet from the blueprint
2. CALCULATE the area (width × length) in square feet
3. DO NOT RETURN 0 for area - if you can see a room, estimate its size

FLOOR TYPE IDENTIFICATION GUIDE:
1. MAIN FLOOR indicators:
   - Has kitchen (critical indicator)
   - Has living/family room
   - Has dining room/area
   - Has entry/foyer
   - Usually 8-15 rooms total

2. UPPER/SECOND FLOOR indicators:
   - Multiple bedrooms (2+)
   - Master bedroom suite
   - Multiple bathrooms
   - NO kitchen
   - Usually 4-10 rooms total

3. BONUS ROOM indicators:
   - Only 1-3 rooms total
   - One large "bonus" or "flex" room
   - May have one bedroom and bathroom
   - Often labeled as over garage
   - Very limited room count

4. BASEMENT indicators:
   - Recreation/rec room
   - Unfinished areas
   - Storage areas
   - Utility/mechanical room
   - May have bedrooms
{hint_str}

WHAT WE EXPECT TO SEE NEXT:
{expectations_str}

CRITICAL INSTRUCTIONS:
1. IDENTIFY the floor type based on the rooms you see, NOT the page label
2. COUNT every room including closets and storage
3. If you see a kitchen, this IS the main floor regardless of labels
4. If you see only 1-3 rooms, this is likely a bonus room floor
5. Look for room names and patterns to determine floor type

Location: ZIP {zip_code}

OUTPUT FORMAT:
{{
  "floor_determination": {{
    "detected_floor_type": "main/upper/bonus/basement",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why you determined this floor type",
    "key_indicators": ["kitchen present", "3 bedrooms", "only 2 rooms", etc],
    "rooms_found_count": <number>,
    "has_kitchen": true/false,
    "has_bedrooms": true/false,
    "has_living_spaces": true/false,
    "contradicts_label": true/false
  }},
  "rooms": [
    {{
      "name": "exact name from blueprint",
      "type": "bedroom/bathroom/kitchen/living/bonus/storage/etc",
      "width_ft": <MEASURE FROM BLUEPRINT>,
      "length_ft": <MEASURE FROM BLUEPRINT>,
      "area_sqft": <CALCULATE: width × length, NEVER 0>,
      "exterior_walls": 0-4,
      "has_windows": true/false,
      "is_over_garage": true/false,
      "special_notes": "any special features"
    }}
  ],
  "validation": {{
    "all_rooms_found": true/false,
    "total_area_sqft": <SUM OF ALL ROOM AREAS>,
    "floor_assignment": {{
      "recommended_floor_number": 1/2/3,
      "recommended_floor_name": "Main Floor/Upper Floor/Bonus Room/etc"
    }}
  }}
}}

REMEMBER: Trust what you SEE in the blueprint, not what the label says!"""
        
        return prompt
    
    def get_validation_prompt(
        self, 
        initial_response: Dict,
        page_text: str,
        expected_floor_type: str
    ) -> str:
        """
        Generate a validation prompt when there's a mismatch
        
        Used when GPT-4V's determination contradicts expectations
        """
        detected_type = initial_response.get("floor_determination", {}).get("detected_floor_type", "unknown")
        room_count = len(initial_response.get("rooms", []))
        has_kitchen = initial_response.get("floor_determination", {}).get("has_kitchen", False)
        
        return f"""Please verify your floor type determination.

You detected this as a {detected_type} floor with {room_count} rooms.
The page text suggests this might be {expected_floor_type}.
Kitchen present: {has_kitchen}

Please confirm:
1. Did you correctly identify all rooms?
2. Is there definitely {"a" if has_kitchen else "no"} kitchen?
3. Based on the room patterns, what floor type is this?

Be especially careful about:
- Kitchen vs other rooms (kitchen has appliances, cabinets)
- Bonus rooms (large open spaces, often over garage)
- Bedrooms vs other room types

OUTPUT:
{{
  "validation_complete": true,
  "final_floor_type": "main/upper/bonus/basement",
  "confidence": 0.0-1.0,
  "explanation": "Why this is the correct floor type"
}}"""


def create_floor_discovery_prompt(
    zip_code: str,
    page_number: int = 0,
    page_text_hint: Optional[str] = None,
    previous_floors: Optional[List[Dict]] = None,
    building_context: Optional[Dict] = None
) -> str:
    """
    Convenience function to create a floor discovery prompt
    
    This lets GPT-4V determine the floor type from content,
    not from potentially incorrect PDF labels.
    """
    manager = FloorDiscoveryPromptManager()
    return manager.get_floor_discovery_prompt(
        zip_code, page_number, page_text_hint,
        previous_floors, building_context
    )