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


async def cleanup(raw_geo: RawGeometry, raw_text: RawText, zip_code: str = "90210", project_id: Optional[str] = None) -> BlueprintSchema:
    """
    Use OpenAI GPT-4 to convert raw geometry and text into structured blueprint
    
    Args:
        raw_geo: Raw geometry data from GeometryParser
        raw_text: Raw text data from TextParser
        zip_code: Project zip code
        project_id: Optional project ID
        
    Returns:
        BlueprintSchema with structured room data
        
    Raises:
        AICleanupError: If AI processing fails
    """
    from datetime import datetime
    from .schema import ParsingMetadata, ParsingStatus
    from uuid import uuid4, UUID
    import time
    
    start_time = time.time()
    
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    if not client.api_key:
        raise AICleanupError("OPENAI_API_KEY environment variable not set")
    
    # Prepare context for AI
    context = _prepare_context(raw_geo, raw_text, zip_code)
    
    # Generate system prompt
    system_prompt = _generate_system_prompt()
    
    try:
        # Call OpenAI API - Use GPT-4o for text reasoning
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4o mini for cost-effective text reasoning
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            temperature=0.1,  # Low temperature for consistent output
            max_completion_tokens=2000,  # Use new parameter for GPT-4o models
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        # Add the required parsing_metadata field that AI doesn't provide
        processing_time = time.time() - start_time
        
        # Create metadata for the AI parsing
        parsing_metadata = ParsingMetadata(
            parsing_timestamp=datetime.utcnow(),
            processing_time_seconds=processing_time,
            pdf_filename=raw_text.pdf_filename if hasattr(raw_text, 'pdf_filename') else "unknown.pdf",
            pdf_page_count=raw_text.pdf_page_count if hasattr(raw_text, 'pdf_page_count') else 1,
            selected_page=raw_text.selected_page if hasattr(raw_text, 'selected_page') else 1,
            geometry_status=ParsingStatus.SUCCESS if raw_geo else ParsingStatus.FAILED,
            text_status=ParsingStatus.SUCCESS if raw_text else ParsingStatus.FAILED,
            ai_status=ParsingStatus.SUCCESS,
            overall_confidence=0.7,  # AI-based parsing has moderate confidence
            geometry_confidence=0.8 if raw_geo and raw_geo.scale_factor else 0.4,
            text_confidence=0.8 if raw_text and raw_text.room_labels else 0.4,
            errors_encountered=[],
            warnings=["Blueprint parsed using AI analysis"]
        )
        
        # Ensure project_id is set
        if 'project_id' not in result_json or not result_json['project_id']:
            result_json['project_id'] = project_id or str(uuid4())
        
        # Ensure zip_code matches what was provided
        result_json['zip_code'] = zip_code
        
        # Add the metadata to the result
        result_json['parsing_metadata'] = parsing_metadata
        
        # Validate and create BlueprintSchema
        blueprint = BlueprintSchema(**result_json)
        
        return blueprint
        
    except json.JSONDecodeError as e:
        raise AICleanupError(f"Failed to parse AI response as JSON: {e}")
    except TypeError as e:
        if "proxies" in str(e):
            raise AICleanupError(f"OpenAI client configuration error - please update dependencies: {e}")
        raise AICleanupError(f"OpenAI API call failed (type error): {e}")
    except Exception as e:
        # Handle common httpx/connection errors
        error_msg = str(e).lower()
        if "proxies" in error_msg:
            raise AICleanupError(f"HTTP client configuration error - please update OpenAI library: {e}")
        elif "connection" in error_msg or "timeout" in error_msg:
            raise AICleanupError(f"Network connection error during AI processing: {e}")
        elif "unauthorized" in error_msg or "401" in error_msg:
            raise AICleanupError(f"OpenAI API authentication failed - check API key: {e}")
        elif "rate limit" in error_msg or "429" in error_msg:
            raise AICleanupError(f"OpenAI API rate limit exceeded: {e}")
        else:
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
                # Convert area from pixels to square feet using scale_factor
                "area": rect.get("area_sqft", 
                        rect["area"] / (raw_geo.scale_factor ** 2) if raw_geo.scale_factor and raw_geo.scale_factor > 0 
                        else rect["area"]),
                "center": [rect["center_x"], rect["center_y"]],
                # Convert dimensions from pixels to feet using scale_factor
                "dimensions": [
                    rect.get("width_ft", rect["width"] / raw_geo.scale_factor if raw_geo.scale_factor and raw_geo.scale_factor > 0 else rect["width"]),
                    rect.get("height_ft", rect["height"] / raw_geo.scale_factor if raw_geo.scale_factor and raw_geo.scale_factor > 0 else rect["height"])
                ],
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
                "text": label.get("text", ""),
                # Handle both formats: x0/top (text_parser) and x/y (old format)
                "position": [
                    label.get("x0", label.get("x", 0)),  # Try x0 first, fall back to x
                    label.get("top", label.get("y", 0))  # Try top first, fall back to y
                ],
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
      room_type: str
      confidence: float
      center_position: Tuple[float, float]
      label_found: bool
      dimensions_source: str

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
      "area": "number (room area in square feet)",
      "room_type": "string (bedroom, bathroom, kitchen, living, dining, hallway, closet, laundry, office, other)",
      "confidence": "number (0.0-1.0, parsing confidence)",
      "center_position": "[x_coordinate, y_coordinate] (room center on page)",
      "label_found": "boolean (true if text label found, false if inferred)",
      "dimensions_source": "string (measured, inferred, estimated)"
    }}
  ]
}}

ANALYSIS GUIDELINES:

1. ROOM IDENTIFICATION (CRITICAL - FIND ALL ROOMS):
   - Match text labels with geometric rectangles based on proximity
   - Common room types: Living Room, Kitchen, Master Bedroom, Bedroom, Bathroom, Dining Room, Office, Utility Room
   - IMPORTANT: Also look for: Pantry, Laundry, Mudroom, Entry/Foyer, Hallway, Closets, Storage, Half Bath
   - If a rectangle has no nearby label, infer room type from size and position
   - Small unlabeled rooms near kitchen = likely pantry
   - Small unlabeled rooms near bedrooms = likely closets
   - Small rooms with plumbing notation = likely bathrooms
   - Typical room sizes: 
     * Bedrooms: 100-300 sqft
     * Living rooms: 200-500 sqft
     * Kitchens: 100-250 sqft
     * Full Bathrooms: 40-100 sqft
     * Half Baths: 20-40 sqft
     * Closets: 15-50 sqft
     * Pantries: 20-60 sqft
     * Laundry: 30-80 sqft

2. DIMENSIONS & AREA:
   - When scale_factor is provided, room areas and dimensions are already converted to square feet and feet
   - If scale_factor is missing or 0, values may be in page units - estimate based on typical residential dimensions
   - Validate that areas are reasonable (bedrooms 100-300 sqft, not 0.5-2 sqft)
   - Calculate area as width × length if needed
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

6. NEW REQUIRED FIELDS:
   - room_type: Classify based on name/size (bedroom, bathroom, kitchen, living, dining, hallway, closet, laundry, office, other)
   - confidence: Your confidence in room identification (0.9 = clear label+dims, 0.7 = clear label, 0.5 = unlabeled, 0.3 = uncertain)
   - center_position: Calculate from room rectangle bounds as [(x0+x1)/2, (y0+y1)/2]
   - label_found: true if text label exists near room, false if room type was inferred
   - dimensions_source: "measured" if dimensions shown, "inferred" if calculated from geometry, "estimated" if guessed

7. VALIDATION:
   - Ensure all rooms have positive area > 15 sqft (allows for small closets)
   - Total sqft should be reasonable for residential (500-5000 sqft typical)
   - Room count expectations:
     * 1000-1500 sqft: 5-10 rooms minimum
     * 1500-2500 sqft: 8-15 rooms minimum
     * 2500+ sqft: 12-25 rooms minimum
   - If you find fewer rooms than expected, you likely missed some

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
async def cleanup_with_ai(raw_geo: RawGeometry, raw_text: RawText, zip_code: str = "90210", project_id: Optional[str] = None) -> BlueprintSchema:
    """Backward compatibility wrapper"""
    return await cleanup(raw_geo, raw_text, zip_code, project_id)


if __name__ == "__main__":
    # Run test
    asyncio.run(test_ai_cleanup())