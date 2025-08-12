"""
Enhanced GPT-4V Prompts for Multi-Floor Blueprint Analysis

This module provides context-aware prompts that understand building structure
across multiple pages and properly handle partial floors like bonus rooms.

NO BAND-AID FIXES: These prompts address the ROOT CAUSE of incomplete room detection
by providing floor-specific expectations and context from previous pages.
"""

import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class MultiFloorPromptManager:
    """
    Manages context-aware prompts for multi-floor blueprint analysis
    
    ROOT CAUSE FIX: Previous prompts expected same room count on all floors.
    These prompts understand that upper floors, bonus rooms, and basements
    have different characteristics.
    """
    
    def __init__(self):
        self.building_context = {}
        self.floors_analyzed = []
    
    def get_floor_aware_prompt(
        self,
        zip_code: str,
        page_number: int,
        floor_label: Optional[str] = None,
        previous_floors: Optional[List[Dict]] = None,
        building_typology_hint: Optional[str] = None
    ) -> str:
        """
        Generate a context-aware prompt for a specific floor
        
        Args:
            zip_code: Project ZIP code
            page_number: Current page number (0-indexed)
            floor_label: Detected floor label from page
            previous_floors: Analysis results from previous floors
            building_typology_hint: Expected building type (1.5-story, 2-story, etc.)
            
        Returns:
            Optimized prompt for this specific floor
        """
        # Determine expected floor characteristics
        floor_context = self._determine_floor_context(
            page_number, floor_label, previous_floors, building_typology_hint
        )
        
        # Build context from previous floors
        context_str = ""
        if previous_floors:
            context_str = self._build_previous_floors_context(previous_floors)
        
        return self._create_contextual_prompt(
            zip_code, floor_context, context_str, page_number
        )
    
    def _determine_floor_context(
        self,
        page_number: int,
        floor_label: Optional[str],
        previous_floors: Optional[List[Dict]],
        building_typology_hint: Optional[str]
    ) -> Dict[str, Any]:
        """Determine expected characteristics for this floor"""
        
        context = {
            "floor_type": "unknown",
            "expected_rooms": [],
            "min_rooms": 5,
            "max_rooms": 15,
            "likely_has_kitchen": False,
            "likely_has_bedrooms": True,
            "special_instructions": []
        }
        
        # Parse floor label
        if floor_label:
            label_lower = floor_label.lower()
            
            if "basement" in label_lower or "lower" in label_lower:
                context["floor_type"] = "basement"
                context["min_rooms"] = 2
                context["likely_has_kitchen"] = False
                context["expected_rooms"] = ["recreation", "storage", "utility", "bathroom"]
                context["special_instructions"].append("Look for unfinished areas and mechanical rooms")
                
            elif "bonus" in label_lower:
                context["floor_type"] = "bonus"
                context["min_rooms"] = 1  # Bonus floors often just have 1-3 rooms
                context["max_rooms"] = 4
                context["likely_has_kitchen"] = False
                context["expected_rooms"] = ["bonus room", "bedroom", "storage", "bathroom"]
                context["special_instructions"].append(
                    "CRITICAL: Bonus floors typically have only 1-3 rooms over the garage"
                )
                context["special_instructions"].append(
                    "Look for: One large bonus room, possibly a bedroom and bathroom"
                )
                
            elif any(x in label_lower for x in ["second", "2nd", "upper"]):
                context["floor_type"] = "upper"
                context["min_rooms"] = 3
                context["likely_has_kitchen"] = False
                context["likely_has_bedrooms"] = True
                context["expected_rooms"] = ["master bedroom", "bedroom", "bathroom", "closet", "hallway"]
                
                # Check if this might be a partial upper floor
                if building_typology_hint and "1.5" in building_typology_hint:
                    context["min_rooms"] = 2
                    context["special_instructions"].append(
                        "This may be a partial upper floor (1.5 story home)"
                    )
                    
            elif any(x in label_lower for x in ["first", "1st", "main", "ground"]):
                context["floor_type"] = "main"
                context["min_rooms"] = 5
                context["likely_has_kitchen"] = True
                context["expected_rooms"] = ["kitchen", "living", "dining", "bathroom", "entry"]
                
        # Adjust based on page number if no clear label
        if context["floor_type"] == "unknown":
            if page_number == 0:
                context["floor_type"] = "main"
                context["likely_has_kitchen"] = True
            elif page_number == 1:
                context["floor_type"] = "upper"
                context["likely_has_kitchen"] = False
        
        # Adjust based on previous floors analyzed
        if previous_floors:
            has_main_floor = any(
                f.get("has_kitchen", False) for f in previous_floors
            )
            if has_main_floor:
                # We already have main floor, this must be upper/bonus
                context["likely_has_kitchen"] = False
                if context["floor_type"] == "main":
                    context["floor_type"] = "upper"
        
        return context
    
    def _build_previous_floors_context(self, previous_floors: List[Dict]) -> str:
        """Build context string from previous floor analyses"""
        if not previous_floors:
            return ""
        
        context_parts = ["CONTEXT FROM PREVIOUS FLOORS:"]
        
        for i, floor in enumerate(previous_floors):
            floor_name = floor.get("floor_name", f"Floor {i+1}")
            room_count = len(floor.get("rooms", []))
            total_area = floor.get("total_area", 0)
            
            context_parts.append(
                f"- {floor_name}: {room_count} rooms, {total_area:.0f} sqft"
            )
            
            # Note key rooms found
            if floor.get("has_kitchen"):
                context_parts.append("  (has kitchen - main living floor)")
            if floor.get("has_master"):
                context_parts.append("  (has master bedroom)")
        
        context_parts.append("")
        return "\n".join(context_parts)
    
    def _create_contextual_prompt(
        self,
        zip_code: str,
        floor_context: Dict[str, Any],
        previous_context: str,
        page_number: int
    ) -> str:
        """Create the actual prompt with all context"""
        
        # Build special instructions
        special_instructions = "\n".join(
            f"- {inst}" for inst in floor_context["special_instructions"]
        )
        
        # Build expected rooms list
        expected_rooms = ", ".join(floor_context["expected_rooms"]) if floor_context["expected_rooms"] else "typical residential rooms"
        
        prompt = f"""You are analyzing page {page_number + 1} of a residential blueprint.

{previous_context}

CRITICAL FLOOR-SPECIFIC REQUIREMENTS:
- Floor Type: {floor_context['floor_type'].upper()}
- Expected: {floor_context['min_rooms']}-{floor_context['max_rooms']} rooms
- Likely rooms: {expected_rooms}
- Has kitchen: {'YES' if floor_context['likely_has_kitchen'] else 'NO'}

{special_instructions}

EXTRACTION REQUIREMENTS:
1. COUNT EVERY ROOM - Do not skip any spaces, even if small
2. For {floor_context['floor_type']} floors, expect {floor_context['min_rooms']}-{floor_context['max_rooms']} rooms
3. Include storage areas, closets, and utility spaces
4. If this is a BONUS or UPPER floor, it may have significantly fewer rooms than the main floor

ROOM DETECTION CHECKLIST:
□ All bedrooms identified
□ All bathrooms identified  
□ Kitchen identified (if main floor)
□ Living/family rooms identified
□ Dining areas identified
□ Hallways and circulation
□ Closets and storage
□ Utility/mechanical rooms
□ Bonus room (if applicable)
□ Garage (if visible)

For each room provide:
- Exact name from blueprint
- Room type classification
- Dimensions in feet
- Number of exterior walls
- Windows (count or presence)
- Special features (vaulted ceiling, over garage, etc.)

Location: ZIP {zip_code}

OUTPUT FORMAT:
{{
  "confidence": 0.0-1.0,
  "floor_info": {{
    "floor_number": {page_number + 1},
    "floor_type": "{floor_context['floor_type']}",
    "total_rooms": <count>,
    "has_kitchen": {str(floor_context['likely_has_kitchen']).lower()},
    "is_partial_floor": <true if bonus/partial>,
    "is_over_garage": <true if bonus over garage>
  }},
  "rooms": [
    {{
      "name": "exact name from blueprint",
      "type": "bedroom/bathroom/kitchen/living/bonus/storage/etc",
      "width_ft": 0.0,
      "length_ft": 0.0,
      "area_sqft": 0.0,
      "exterior_walls": 0-4,
      "has_windows": true/false,
      "is_over_garage": true/false,
      "special_notes": "any special features"
    }}
  ],
  "validation": {{
    "all_rooms_found": true/false,
    "room_count_reasonable": true/false,
    "total_area_sqft": 0.0
  }}
}}

REMEMBER: Upper floors and bonus rooms typically have FEWER rooms than main floors!"""
        
        return prompt
    
    def get_validation_prompt(self, rooms_found: List[Dict], floor_type: str) -> str:
        """
        Generate a validation prompt to verify room detection
        
        Used when initial detection seems incomplete
        """
        room_names = [r.get("name", "Unknown") for r in rooms_found]
        
        return f"""Please verify the room detection for this {floor_type} floor.

Rooms currently detected ({len(rooms_found)}):
{', '.join(room_names)}

Please check if any rooms were missed:
1. Are there any bedrooms not listed?
2. Are there any bathrooms not listed?
3. Are there any closets or storage areas not listed?
4. Is there a hallway or circulation space not listed?
5. For bonus floors: Is there a bonus room or flex space?

If you find additional rooms, please list them with their approximate dimensions.

Expected for {floor_type} floor: 
- Main floor: 8-15 rooms including kitchen, living, dining
- Upper floor: 4-10 rooms, mainly bedrooms and bathrooms
- Bonus floor: 1-4 rooms, typically one large bonus room
- Basement: 2-8 rooms, may include unfinished space

OUTPUT:
{{
  "validation_complete": true,
  "additional_rooms_found": [
    {{
      "name": "room name",
      "type": "room type",
      "approximate_area_sqft": 0
    }}
  ],
  "total_rooms_after_validation": 0,
  "confidence_after_validation": 0.0-1.0
}}"""


def create_multi_floor_prompt(
    zip_code: str,
    page_number: int = 0,
    floor_label: Optional[str] = None,
    previous_floors: Optional[List[Dict]] = None,
    building_typology: Optional[str] = None
) -> str:
    """
    Convenience function to create a multi-floor aware prompt
    
    Args:
        zip_code: Project ZIP code
        page_number: Current page (0-indexed)
        floor_label: Detected floor label
        previous_floors: Previous floor analyses
        building_typology: Building type hint (e.g., "1.5-story")
        
    Returns:
        Optimized prompt for the floor
    """
    manager = MultiFloorPromptManager()
    return manager.get_floor_aware_prompt(
        zip_code, page_number, floor_label, 
        previous_floors, building_typology
    )