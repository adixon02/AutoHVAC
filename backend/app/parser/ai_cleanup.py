"""
AI-powered blueprint cleanup using OpenAI GPT-4
Converts raw geometry + text into structured BlueprintSchema
"""

import json
import asyncio
from typing import Dict, Any, Optional
import os
from openai import AsyncOpenAI
from .schema import BlueprintSchema, RawGeometry, RawText


class AICleanupError(Exception):
    """Custom exception for AI cleanup failures"""
    pass


async def cleanup(raw_geo: RawGeometry, raw_text: RawText) -> BlueprintSchema:
    """
    Use OpenAI GPT-4 to convert raw geometry and text into structured blueprint
    
    Args:
        raw_geo: Raw geometry data from GeometryParser
        raw_text: Raw text data from TextParser  
        
    Returns:
        BlueprintSchema with structured room data
        
    Raises:
        AICleanupError: If AI processing fails
    """
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    if not client.api_key:
        raise AICleanupError("OPENAI_API_KEY environment variable not set")
    
    # Prepare context for AI
    context = _prepare_context(raw_geo, raw_text, "90210")
    
    # Generate system prompt
    system_prompt = _generate_system_prompt()
    
    try:
        # Call OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            temperature=0.1,  # Low temperature for consistent output
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # Validate and create BlueprintSchema
        blueprint = BlueprintSchema(**result_json)
        
        return blueprint
        
    except json.JSONDecodeError as e:
        raise AICleanupError(f"Failed to parse AI response as JSON: {e}")
    except Exception as e:
        raise AICleanupError(f"OpenAI API call failed: {e}")


def _prepare_context(raw_geo: RawGeometry, raw_text: RawText, zip_code: str) -> str:
    """Prepare context string for OpenAI"""
    
    # Summarize geometry data
    geo_summary = {
        "page_dimensions": {
            "width": raw_geo.page_width,
            "height": raw_geo.page_height
        },
        "scale_factor": raw_geo.scale_factor,
        "wall_lines": [
            {
                "start": [line["x0"], line["y0"]],
                "end": [line["x1"], line["y1"]],
                "length": line["length"],
                "orientation": line["orientation"],
                "wall_probability": line.get("wall_probability", 0.5)
            }
            for line in raw_geo.lines 
            if line.get("wall_probability", 0) > 0.6
        ][:20],  # Limit to top 20 wall candidates
        
        "rooms": [
            {
                "bounds": [rect["x0"], rect["y0"], rect["x1"], rect["y1"]],
                "area": rect["area"],
                "center": [rect["center_x"], rect["center_y"]],
                "dimensions": [rect["width"], rect["height"]],
                "room_probability": rect.get("room_probability", 0.5)
            }
            for rect in raw_geo.rectangles
            if rect.get("room_probability", 0) > 0.4
        ][:15]  # Limit to top 15 room candidates
    }
    
    # Summarize text data
    text_summary = {
        "room_labels": [
            {
                "text": label["text"],
                "position": [label["x0"], label["top"]],
                "room_type": label.get("room_type", "unknown"),
                "confidence": label.get("confidence", 0.5)
            }
            for label in raw_text.room_labels
        ],
        
        "dimensions": [
            {
                "text": dim["dimension_text"],
                "position": [dim["x0"], dim["top"]],
                "parsed": dim.get("parsed_dimensions", [0, 0])
            }
            for dim in raw_text.dimensions
        ][:10],  # Limit dimensions
        
        "notes": [
            {
                "text": note["text"],
                "position": [note["x0"], note["top"]],
                "type": note.get("note_type", "unknown")
            }
            for note in raw_text.notes
        ][:5]  # Limit notes
    }
    
    context = f"""
BLUEPRINT ANALYSIS REQUEST

Project Location: {zip_code}

GEOMETRY DATA:
{json.dumps(geo_summary, indent=2)}

TEXT DATA:
{json.dumps(text_summary, indent=2)}

Please analyze this architectural blueprint data and return a structured JSON response following the BlueprintSchema format.
"""
    
    return context


def _generate_system_prompt() -> str:
    """Generate the system prompt for OpenAI"""
    
    schema_model = """
    class Room(BaseModel):
      name: str
      dimensions_ft: Tuple[float,float]
      floor: int
      windows: int
      orientation: str
      area: float

    class BlueprintSchema(BaseModel):
      project_id: UUID
      zip_code: str
      sqft_total: float
      stories: int
      rooms: List[Room]
    """
    
    return f"""You are an expert at converting raw blueprint data into structured room definitions.
Here is the Pydantic schema: {schema_model}

Your task is to analyze raw geometry and text data extracted from architectural PDFs and convert them into structured room data for HVAC load calculations.

TASK:
Convert the provided raw geometry lines, rectangles, and text labels into a structured JSON response that identifies individual rooms with their properties.

OUTPUT FORMAT:
Return a JSON object matching this exact schema:

{{
  "project_id": "string (generate a UUID)",
  "zip_code": "string (use the provided zip code)",
  "sqft_total": "number (total square footage of all rooms)",
  "stories": "number (number of floors, typically 1-3)",
  "rooms": [
    {{
      "name": "string (e.g., 'Living Room', 'Master Bedroom')",
      "dimensions_ft": "[width_in_feet, length_in_feet]",
      "floor": "number (floor number, 1-based)",
      "windows": "number (estimated number of windows, 0-10)",
      "orientation": "string (N, S, E, W, NE, NW, SE, SW, or empty)",
      "area": "number (room area in square feet)"
    }}
  ]
}}

ANALYSIS GUIDELINES:

1. ROOM IDENTIFICATION:
   - Match text labels with geometric rectangles based on proximity
   - Common room types: Living Room, Kitchen, Master Bedroom, Bedroom, Bathroom, Dining Room, Office, Utility Room
   - If a rectangle has no nearby label, infer room type from size and position
   - Typical room sizes: Bedrooms (100-300 sqft), Living rooms (200-500 sqft), Kitchens (100-250 sqft), Bathrooms (30-100 sqft)

2. DIMENSIONS & AREA:
   - Convert page coordinates to real-world feet using scale_factor if available
   - If no scale provided, estimate based on typical residential dimensions
   - Calculate area as width × length
   - Round dimensions to nearest 0.5 feet

3. WINDOWS:
   - Estimate based on room type and exterior wall exposure
   - Living rooms: 2-4 windows, Bedrooms: 1-2 windows, Bathrooms: 0-1 windows
   - Consider room position relative to building perimeter

4. ORIENTATION:
   - Estimate primary orientation based on room position in floor plan
   - Rooms on building edges have clear orientations (N/S/E/W)
   - Interior rooms have no primary orientation (use empty string)

5. FLOOR DETECTION:
   - Most residential blueprints show single floor (stories = 1)
   - Look for stairs, elevators, or multiple floor indicators
   - If uncertain, assume 1 story

6. VALIDATION:
   - Ensure all rooms have positive area > 20 sqft
   - Total sqft should be reasonable for residential (500-5000 sqft typical)
   - Room count should be reasonable (3-20 rooms typical)

RESPONSE REQUIREMENTS:
- Return ONLY valid JSON, no additional text or explanation
- All numeric values must be positive numbers
- All room names must be descriptive and properly capitalized
- If analysis is impossible, return a minimal valid structure with at least one "Unknown Room"

Focus on accuracy and practical HVAC design needs. The output will be used for Manual J load calculations and equipment sizing."""


async def test_ai_cleanup():
    """Test function for AI cleanup"""
    from .schema import RawGeometry, RawText
    
    # Create mock data
    mock_geo = RawGeometry(
        page_width=792.0,
        page_height=612.0,
        scale_factor=48.0,
        lines=[
            {"x0": 100, "y0": 100, "x1": 300, "y1": 100, "length": 200, "orientation": "horizontal", "wall_probability": 0.8},
            {"x0": 300, "y0": 100, "x1": 300, "y1": 250, "length": 150, "orientation": "vertical", "wall_probability": 0.8}
        ],
        rectangles=[
            {"x0": 100, "y0": 100, "x1": 300, "y1": 250, "area": 3000, "center_x": 200, "center_y": 175, "width": 200, "height": 150, "room_probability": 0.9}
        ],
        polylines=[]
    )
    
    mock_text = RawText(
        words=[{"text": "Living Room", "x0": 180, "top": 175}],
        room_labels=[{"text": "Living Room", "x0": 180, "top": 175, "room_type": "living", "confidence": 0.9}],
        dimensions=[],
        notes=[]
    )
    
    try:
        result = await cleanup_with_ai(mock_geo, mock_text)
        print("AI Cleanup Test Result:")
        print(json.dumps(result.dict(), indent=2))
        return True
    except Exception as e:
        print(f"AI Cleanup Test Failed: {e}")
        return False


# Backward compatibility alias
async def cleanup_with_ai(raw_geo: RawGeometry, raw_text: RawText, zip_code: str = "90210") -> BlueprintSchema:
    """Backward compatibility wrapper"""
    return await cleanup(raw_geo, raw_text)


if __name__ == "__main__":
    # Run test
    asyncio.run(test_ai_cleanup())