"""
AI Synthesis Stage - Combines all extracted data for comprehensive Manual J analysis
Uses GPT-4 to analyze the complete building context and identify missing factors
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI
from core.models import Building, Room, Floor

logger = logging.getLogger(__name__)


class ManualJSynthesizer:
    """
    Uses AI to synthesize all extracted data and fill gaps
    Based on HVAC expert checklist for comprehensive load calculations
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key - synthesis disabled")
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = OpenAI(api_key=api_key)
            logger.info("Manual J synthesizer initialized")
    
    def synthesize(
        self, 
        building: Building,
        extraction_results: Dict[str, Any],
        pdf_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize all data for comprehensive Manual J analysis
        
        Args:
            building: Validated building data
            extraction_results: Raw results from all extractors (vision, vector, etc)
            pdf_metadata: Additional PDF metadata (page count, text content, etc)
            
        Returns:
            Enhanced building data with AI-identified factors
        """
        if not self.enabled:
            logger.debug("Synthesis skipped - not enabled")
            return self._passthrough_data(building)
        
        logger.info("Synthesizing building data with AI...")
        
        try:
            # Create comprehensive context
            context = self._build_context(building, extraction_results, pdf_metadata)
            
            # Create mega prompt with all available data
            prompt = self._create_mega_prompt(context)
            
            # Get AI analysis
            response = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temp for factual analysis
                max_completion_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content
            analysis = self._parse_response(content)
            
            # Log the raw analysis for debugging
            if not analysis:
                logger.warning("Failed to parse synthesis response, using defaults")
                analysis = {
                    "missing_factors": ["Unable to perform complete synthesis"],
                    "recommendations": {"safety_factor": 1.1}
                }
            
            # Enhance building data with AI insights
            enhanced_data = self._enhance_building_data(building, analysis)
            
            missing_count = len(analysis.get('missing_factors', []))
            logger.info(f"Synthesis complete - identified {missing_count} missing factors")
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._passthrough_data(building)
    
    def _build_context(
        self, 
        building: Building,
        extraction_results: Dict[str, Any],
        pdf_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive context from all sources"""
        
        context = {
            "building_summary": {
                "total_sqft": building.total_sqft,
                "floor_count": building.floor_count,
                "room_count": building.room_count,
                "zip_code": building.zip_code,
                "climate_zone": building.climate_zone
            },
            "floors": [],
            "extraction_confidence": {},
            "pdf_metadata": pdf_metadata
        }
        
        # Add floor details
        for floor in building.floors:
            floor_data = {
                "name": floor.name,
                "number": floor.number,
                "total_sqft": floor.total_sqft,
                "room_count": floor.room_count,
                "rooms": []
            }
            
            for room in floor.rooms:
                room_data = {
                    "name": room.name,
                    "type": room.room_type.value,
                    "area": room.area_sqft,
                    "dimensions": [room.width_ft, room.length_ft],
                    "exterior_walls": room.exterior_walls,
                    "windows": room.windows,
                    "ceiling_height": room.ceiling_height_ft
                }
                floor_data["rooms"].append(room_data)
            
            context["floors"].append(floor_data)
        
        # Add extraction confidence scores
        if extraction_results.get("vision"):
            context["extraction_confidence"]["vision"] = extraction_results["vision"].get("confidence", 0)
        if extraction_results.get("vector"):
            context["extraction_confidence"]["vector"] = extraction_results["vector"] is not None
        
        return context
    
    def _create_mega_prompt(self, context: Dict[str, Any]) -> str:
        """Create comprehensive prompt with all building data"""
        
        # Summarize building
        summary = f"""
I have extracted data from architectural blueprints for HVAC Manual J load calculations.
Please analyze this building comprehensively and identify any missing critical factors.

BUILDING OVERVIEW:
- Location: ZIP {context['building_summary']['zip_code']} (Climate Zone {context['building_summary']['climate_zone'] or 'Unknown'})
- Total Area: {context['building_summary']['total_sqft']:.0f} sq ft
- Floors: {context['building_summary']['floor_count']}
- Total Rooms: {context['building_summary']['room_count']}

FLOOR-BY-FLOOR BREAKDOWN:
"""
        
        # Add each floor
        for floor in context['floors']:
            summary += f"\n{floor['name']} ({floor['total_sqft']:.0f} sq ft):\n"
            for room in floor['rooms']:
                summary += f"  - {room['name']}: {room['area']:.0f} sq ft, "
                summary += f"{room['exterior_walls']} exterior walls, {room['windows']} windows\n"
        
        # Add extraction confidence
        summary += "\nEXTRACTION CONFIDENCE:\n"
        for source, confidence in context['extraction_confidence'].items():
            if isinstance(confidence, bool):
                summary += f"  - {source}: {'Available' if confidence else 'Not Available'}\n"
            else:
                summary += f"  - {source}: {confidence:.0%}\n"
        
        # Add specific questions based on HVAC expert checklist
        summary += """

CRITICAL MANUAL J FACTORS TO ANALYZE:

1. ORIENTATION & SOLAR GAIN
   - Can you determine building orientation (which walls face N/S/E/W)?
   - Are there overhangs, porches, or shading elements?
   - Window distribution by orientation?

2. ENVELOPE DETAILS
   - Wall construction type (2x4 or 2x6 framing)?
   - Estimated R-values for walls, roof, floor?
   - Window types (single/double pane, low-E)?
   - Foundation type (slab/crawlspace/basement)?

3. INFILTRATION FACTORS
   - Construction age/quality (tight/average/loose)?
   - Presence of fireplaces or combustion appliances?
   - Garage attached or detached?

4. SPECIAL CONDITIONS
   - Vaulted or cathedral ceilings?
   - Large glass walls or skylights?
   - Open floor plans affecting airflow?
   - Bonus rooms over garages?

5. MISSING DATA GAPS
   - What critical Manual J inputs are we missing?
   - What assumptions should we make for missing data?
   - Any unusual features affecting load calculations?

Please provide a JSON response with your analysis:
{
  "orientation": {
    "north_facing_walls": ["list of rooms"],
    "south_facing_walls": ["list of rooms"],
    "confidence": 0.0-1.0
  },
  "envelope": {
    "wall_type": "2x4" or "2x6",
    "estimated_wall_r": 13 or 19,
    "estimated_roof_r": 30 or 38,
    "window_type": "double_low_e",
    "foundation_type": "slab/crawl/basement"
  },
  "infiltration": {
    "construction_quality": "tight/average/loose",
    "has_fireplace": true/false,
    "attached_garage": true/false
  },
  "special_features": [
    "vaulted_ceiling_in_great_room",
    "bonus_room_over_garage"
  ],
  "missing_factors": [
    "Cannot determine building orientation",
    "Window SHGC values unknown"
  ],
  "recommendations": {
    "assumptions": ["Use average infiltration rate", "Assume R-13 walls"],
    "safety_factor": 1.15
  }
}
"""
        
        return summary
    
    def _get_system_prompt(self) -> str:
        """System prompt for HVAC analysis"""
        return """You are an expert HVAC engineer performing ACCA Manual J load calculations.
You analyze building data to identify all factors affecting heating and cooling loads.
You follow industry best practices and flag any missing critical data.
Your goal is 100% accurate load calculations following ACCA standards.
Be conservative when data is missing - it's better to slightly oversize than undersize.
Always consider local climate conditions and building-specific factors."""
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse AI response"""
        try:
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"Failed to parse synthesis response: {e}")
            return {}
    
    def _enhance_building_data(self, building: Building, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance building data with AI insights"""
        
        # Handle empty or malformed analysis
        if not analysis:
            return self._passthrough_data(building)
        
        enhanced = {
            "building": building.to_json(),
            "synthesis": {
                "orientation": analysis.get("orientation", {}),
                "envelope": analysis.get("envelope", {}),
                "infiltration": analysis.get("infiltration", {}),
                "special_features": analysis.get("special_features", []),
                "missing_factors": analysis.get("missing_factors", []),
                "recommendations": analysis.get("recommendations", {})
            }
        }
        
        # Apply any recommended adjustments
        recommendations = analysis.get("recommendations", {})
        if isinstance(recommendations, dict) and "safety_factor" in recommendations:
            enhanced["synthesis"]["safety_factor"] = recommendations["safety_factor"]
        
        # Flag if critical data is missing
        missing_factors = analysis.get("missing_factors", [])
        if missing_factors and len(missing_factors) > 3:
            enhanced["synthesis"]["confidence"] = "medium"
        elif missing_factors:
            enhanced["synthesis"]["confidence"] = "high"
        else:
            enhanced["synthesis"]["confidence"] = "very high"
        
        return enhanced
    
    def _passthrough_data(self, building: Building) -> Dict[str, Any]:
        """Return data unchanged when synthesis is disabled"""
        return {
            "building": building.to_json(),
            "synthesis": {
                "enabled": False,
                "confidence": "low"
            }
        }


# Module-level instance
_synthesizer = None

def get_synthesizer():
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = ManualJSynthesizer()
    return _synthesizer


def synthesize_building_data(
    building: Building,
    extraction_results: Dict[str, Any] = None,
    pdf_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Convenience function for synthesis"""
    synthesizer = get_synthesizer()
    return synthesizer.synthesize(
        building,
        extraction_results or {},
        pdf_metadata or {}
    )