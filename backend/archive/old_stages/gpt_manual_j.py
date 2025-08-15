"""
GPT-4 Manual J Calculator
Uses GPT-4's knowledge of ACCA Manual J to calculate accurate loads
Instead of implementing formulas, we extract data and let GPT-4 do the calculation
"""

import logging
import json
from typing import Dict, Any, Optional
from openai import OpenAI
import os

logger = logging.getLogger(__name__)


class GPTManualJCalculator:
    """
    Uses GPT-4 to perform actual Manual J calculations
    This is more accurate than our simplified formulas
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning("GPT Manual J calculator disabled - no API key")
    
    def calculate_loads(self, building_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send structured building data to GPT-4 for Manual J calculation
        
        Args:
            building_data: All extracted building information
            
        Returns:
            {
                "heating_btu_hr": 74000,
                "cooling_btu_hr": 25000,
                "heating_tons": 6.2,
                "cooling_tons": 2.1,
                "breakdown": {...},
                "confidence": 0.85
            }
        """
        if not self.enabled:
            logger.error("GPT Manual J calculator not enabled")
            return None
        
        # Build the comprehensive prompt
        prompt = self._build_manual_j_prompt(building_data)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HVAC engineer expert in ACCA Manual J calculations. Provide accurate heating and cooling load calculations based on the building data provided. Use proper Manual J methodology including all correction factors."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent calculations
                max_completion_tokens=2000
            )
            
            # Parse the response
            return self._parse_gpt_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"GPT Manual J calculation failed: {e}")
            return None
    
    def _build_manual_j_prompt(self, data: Dict[str, Any]) -> str:
        """
        Build comprehensive Manual J prompt from extracted data
        NOW INCLUDES CONTEXTUAL UNDERSTANDING!
        """
        # Extract all the relevant data
        building = data.get('building', {})
        
        # Handle Building object or dict
        if hasattr(building, 'to_json'):
            building = building.to_json()
        
        climate = data.get('climate', {})
        envelope = data.get('envelope', {})
        windows = data.get('windows', {})
        extraction = data.get('extraction_results', {})
        
        # Get contextual notes from vision extraction
        contextual_notes = []
        for floor_key in extraction:
            if floor_key.startswith('floor_'):
                floor_data = extraction.get(floor_key, {})
                if 'vision' in floor_data and isinstance(floor_data['vision'], dict):
                    notes = floor_data['vision'].get('contextual_notes', [])
                    contextual_notes.extend(notes)
                    # Also check for building insights
                    insights = floor_data['vision'].get('building_insights', {})
                    if insights.get('has_vaulted_ceilings'):
                        contextual_notes.append("Building has vaulted ceilings affecting load calculations")
                    if insights.get('has_bonus_room'):
                        contextual_notes.append("Bonus room over garage requires special consideration")
        
        # Get climate data
        zip_code = building.get('zip_code', '99006')
        climate_zone = climate.get('climate_zone', '5B')
        winter_temp = climate.get('winter_99', 6)
        summer_temp = climate.get('summer_1', 91)
        
        # Get zone configuration for climate-appropriate defaults
        from core.climate_zones import get_zone_config
        zone_config = get_zone_config(climate_zone)
        
        # Get building data
        stories = building.get('floor_count', 2)
        total_sqft = building.get('total_sqft', 2000)
        
        # Get envelope data if available
        if envelope:
            # Handle both dict and object formats
            if hasattr(envelope, 'total_perimeter_ft'):
                perimeter = envelope.total_perimeter_ft
                wall_area = envelope.total_wall_area_sqft
                shape_factor = envelope.shape_factor
            else:
                perimeter = envelope.get('total_perimeter_ft', 0)
                wall_area = envelope.get('total_wall_area_sqft', 0)
                shape_factor = envelope.get('shape_factor', 4.0)
        else:
            # Estimate from floor area
            perimeter = 4.2 * (total_sqft / stories) ** 0.5
            wall_area = perimeter * 9 * stories
            shape_factor = 4.0
        
        # Get room breakdown
        rooms = []
        floors = building.get('floors', [])
        for floor in floors:
            # Handle both dict and object formats
            if hasattr(floor, 'rooms'):
                floor_rooms = floor.rooms
            else:
                floor_rooms = floor.get('rooms', [])
            
            for room in floor_rooms:
                try:
                    if hasattr(room, 'name'):
                        # It's a Room object
                        rooms.append(f"- {room.name}: {room.area_sqft:.0f} sqft, {room.exterior_walls} exterior walls")
                    else:
                        # It's a dict
                        rooms.append(f"- {room.get('name', 'Unknown')}: {room.get('area_sqft', 100):.0f} sqft, {room.get('exterior_walls', 0)} exterior walls")
                except Exception as e:
                    logger.debug(f"Could not process room: {e}")
        
        # Build contextual notes section
        context_section = ""
        if contextual_notes:
            context_section = f"""
**CONTEXTUAL OBSERVATIONS FROM BLUEPRINT:**
{chr(10).join('- ' + note for note in contextual_notes)}

Use these observations to make intelligent assumptions for any missing data.
"""

        prompt = f"""Calculate ACCA Manual J heating and cooling loads for the following residential building.

{context_section}

1. **Project Location & Climate**
   - Zip Code: {zip_code}
   - Winter Design Temperature: {winter_temp}°F (99% design)
   - Summer Design Temperature: {summer_temp}°F (1% design)
   - Climate Zone: {climate_zone}

2. **Building Description**
   - Number of Stories: {stories}
   - Foundation Type: Slab on grade (typical)
   - Total Conditioned Floor Area: {total_sqft} sq ft
   - Building Perimeter: {perimeter:.1f} ft
   - Shape Factor: {shape_factor:.2f} (perimeter/sqrt(area))
   - Total Exterior Wall Area: {wall_area:.0f} sq ft

3. **Room Breakdown**
{chr(10).join(rooms)}

4. **Envelope Details** (Typical for Climate Zone {climate_zone})
   - Wall Construction: Wood frame with R-{zone_config.get('typical_wall_r', 19)} insulation
   - Roof/Ceiling: R-{zone_config.get('typical_roof_r', 38)}
   - Floor: R-{zone_config.get('typical_floor_r', 19)} (or slab on grade)
   - Windows: U={zone_config.get('typical_window_u', 0.32)}, SHGC={zone_config.get('typical_window_shgc', 0.30)}
   - Air Tightness: {zone_config.get('typical_infiltration_ach', 0.15) * 20:.0f} ACH50 (typical for zone)
   - Construction Quality: Average unless contextual notes suggest otherwise

5. **Windows & Doors**
   - Total Window Area: {total_sqft * 0.15:.0f} sq ft (15% window-to-floor ratio)
   - Window Distribution: Evenly distributed on all orientations
   - Exterior Doors: 3 insulated steel doors, U=0.20

6. **Ductwork**
   - Location: Unconditioned attic
   - Insulation: R-8
   - Leakage: 5% supply, 3% return

7. **Internal Loads**
   - Occupants: {max(3, stories * 2)} people
   - Standard residential lighting and appliances

8. **Ventilation**
   - ASHRAE 62.2 compliant: {total_sqft * 0.03 + 7.5 * max(3, stories * 2):.0f} CFM

**Instructions:**
1. Use proper Manual J 8th Edition methodology
2. Consider the CONTEXTUAL OBSERVATIONS (if any) to adjust assumptions intelligently:
   - If notes mention vaulted ceilings, increase volume calculations
   - If notes mention large glazing areas, adjust solar gains
   - If notes mention shading (porches/overhangs), reduce cooling loads
   - If notes suggest construction quality, adjust infiltration rates
3. Apply appropriate factors for Climate Zone {climate_zone}
4. Include duct losses based on duct location (typically 8-12% heating, 5-8% cooling)
5. DO NOT apply excessive safety factors - ACCA limits: 115% cooling, 140% heating
6. Assume average internal gains for residential use unless context suggests otherwise

**Output Required:**
Provide the total heating load in BTU/hr and cooling load in BTU/hr.
Format as JSON:
{{
    "heating_btu_hr": <number>,
    "cooling_btu_hr": <number>,
    "heating_tons": <number>,
    "cooling_tons": <number>,
    "confidence": <0-1>,
    "notes": ["<any assumptions or concerns>"]
}}"""
        
        return prompt
    
    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """
        Parse GPT-4's Manual J calculation response
        """
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                # Find the JSON object
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                # Try to parse key values from text
                result = {}
                
                # Look for heating load
                if "heating" in response.lower():
                    import re
                    heating_match = re.search(r'heating.*?(\d{2,6})', response.lower())
                    if heating_match:
                        result['heating_btu_hr'] = int(heating_match.group(1))
                
                # Look for cooling load
                if "cooling" in response.lower():
                    cooling_match = re.search(r'cooling.*?(\d{2,6})', response.lower())
                    if cooling_match:
                        result['cooling_btu_hr'] = int(cooling_match.group(1))
                
                if result:
                    result['heating_tons'] = result.get('heating_btu_hr', 0) / 12000
                    result['cooling_tons'] = result.get('cooling_btu_hr', 0) / 12000
                    result['confidence'] = 0.7
                    return result
                
                logger.error("Could not parse GPT response")
                return None
            
            # Parse JSON
            result = json.loads(json_str.strip())
            
            # Ensure all required fields
            if 'heating_tons' not in result and 'heating_btu_hr' in result:
                result['heating_tons'] = result['heating_btu_hr'] / 12000
            if 'cooling_tons' not in result and 'cooling_btu_hr' in result:
                result['cooling_tons'] = result['cooling_btu_hr'] / 12000
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse GPT response: {e}")
            logger.debug(f"Response was: {response}")
            return None


def calculate_with_gpt(building_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main entry point for GPT-based Manual J calculations
    """
    calculator = GPTManualJCalculator()
    if not calculator.enabled:
        logger.warning("GPT Manual J calculator not available, falling back to formula-based")
        return None
    
    result = calculator.calculate_loads(building_data)
    
    if result:
        logger.info(f"GPT Manual J: {result['heating_btu_hr']:,} BTU/hr heating, "
                   f"{result['cooling_btu_hr']:,} BTU/hr cooling")
    
    return result