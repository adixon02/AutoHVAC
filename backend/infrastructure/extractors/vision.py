"""
Simplified GPT-4V Vision Extractor for AutoHVAC v2
No retries, no fallbacks - just clean vision analysis
"""

import os
import logging
import json
import base64
import time
from typing import Dict, Any, Optional
from openai import OpenAI
from PIL import Image
import io
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class VisionExtractor:
    """
    Clean GPT-4V extractor - one model, one attempt, clear results
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found - vision extraction disabled")
            self.client = None
            self.enabled = False
        else:
            self.client = OpenAI(api_key=api_key)
            self.enabled = True
            logger.info(f"Vision extractor initialized with OpenAI API")
        
        self.model = "gpt-4o-2024-11-20"  # The only model that works properly
        self.timeout = 60  # Increased timeout for large images
    
    def extract_with_prompt(self, pdf_path: str, page_num: int, custom_prompt: str) -> Dict[str, Any]:
        """
        Extract using a custom prompt for specific page types
        """
        if not self.enabled:
            return {}
        
        try:
            # Render page to image
            image_base64 = self._render_page(pdf_path, page_num)
            
            # Use custom prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": custom_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_completion_tokens=1000,
                temperature=0.1,
                timeout=30
            )
            
            # Parse response as JSON
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
        except Exception as e:
            logger.warning(f"Custom vision extraction failed: {e}")
            return {}
    
    def extract(self, pdf_path: str, page_num: int, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract rooms from a single page using GPT-4V
        
        Returns:
            {
                "source": "vision",
                "rooms": [...],
                "confidence": 0.8,
                "metadata": {...}
            }
        """
        if not self.enabled:
            logger.debug("Vision extraction skipped - not enabled")
            return {
                "source": "vision",
                "rooms": [],
                "confidence": 0.0,
                "metadata": {"error": "Vision extraction not enabled"}
            }
        
        logger.info(f"Vision extraction for page {page_num + 1}")
        start_time = time.time()
        
        try:
            # Render page to image
            image_base64 = self._render_page(pdf_path, page_num)
            
            # Create prompt with context if available
            prompt = self._create_prompt()
            if context:
                # Add contextual information for better extraction
                context_info = []
                if 'zip_code' in context:
                    context_info.append(f"Location: ZIP {context['zip_code']}")
                if 'climate_zone' in context:
                    context_info.append(f"Climate Zone: {context['climate_zone']}")
                if 'floor_name' in context:
                    context_info.append(f"This is the {context['floor_name']}")
                if 'total_sqft' in context:
                    context_info.append(f"Expected total area: ~{context['total_sqft']} sq ft")
                
                if context_info:
                    prompt += "\n\nContext:\n" + "\n".join(context_info)
            
            # Single GPT-4V call - no retries
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
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
                }],
                max_completion_tokens=2000,
                temperature=0.1,
                timeout=30  # Reduced from 60 to prevent hanging
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = self._parse_response(content)
            
            # Add metadata
            result["source"] = "vision"
            result["metadata"]["processing_time"] = time.time() - start_time
            result["metadata"]["model"] = self.model
            
            logger.info(f"Vision extracted {len(result['rooms'])} rooms")
            return result
            
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            # Return empty result on failure - no fallbacks
            return {
                "source": "vision",
                "rooms": [],
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    def _render_page(self, pdf_path: str, page_num: int) -> str:
        """Render PDF page to base64 image"""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at 150 DPI (reduced from 200) for faster processing
        # This is still good enough for room detection
        mat = fitz.Matrix(150 / 72.0, 150 / 72.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Compress more aggressively using JPEG for smaller size
        # GPT-4V handles JPEG well and it's much smaller than PNG
        buffer = io.BytesIO()
        img = img.convert('RGB')  # Convert to RGB for JPEG
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        
        # Convert to base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        doc.close()
        
        return img_base64
    
    def _create_prompt(self) -> str:
        """Create comprehensive prompt for Manual J load calculations with CONTEXT"""
        return """You are an expert HVAC designer and Manual J load calculation specialist analyzing a residential blueprint.

Extract TWO types of information:

1. **STRUCTURED DATA** - Measurable parameters for each room and the building:
   - Rooms with names, types, dimensions, areas
   - CRITICAL: Count ACTUAL windows in each room (not guess)
   - CRITICAL: Count exterior walls for each room (0, 1, 2, or 3)
   - Window sizes if visible (e.g., "3050" = 3'0" x 5'0")
   - Door locations and types
   - Any visible R-values, U-factors, or insulation specs
   - Ceiling heights if marked

2. **CONTEXTUAL OBSERVATIONS** - Visual insights that affect HVAC loads:
   - Architectural style and likely construction era/quality
   - Vaulted ceilings, cathedral ceilings, or unusual ceiling shapes
   - Large window walls, sliding glass doors, or significant glazing
   - Covered porches, overhangs, or shading elements
   - Garage location and adjacency to conditioned space
   - Skylights, clerestory windows, or dormers
   - Building orientation if north arrow is present
   - Construction notes suggesting tight/average/loose infiltration
   - Open floor plans or large great rooms
   - Bonus rooms or spaces over garages
   - Any unusual thermal challenges

Return JSON format:
{
  "structured_data": {
    "rooms": [
      {
        "name": "Master Bedroom",
        "type": "bedroom",
        "dimensions": [14, 16],
        "area": 224,
        "exterior_walls": 2,
        "windows": 2,
        "ceiling_type": "flat",
        "confidence": 0.9
      }
    ],
    "total_area": 1912,
    "stories": 2,
    "has_basement": false,
    "has_bonus_room": true,
    "window_to_wall_ratio_estimate": 0.15
  },
  "contextual_notes": [
    "Modern craftsman style with complex roofline suggesting higher heat loss",
    "Large vaulted great room at rear with extensive south-facing glazing",
    "Covered rear porch provides approximately 8ft of shading for lower windows",
    "Attached 2-car garage shares wall with laundry/mudroom - potential thermal bridge",
    "Master suite isolated on opposite side may need separate zone",
    "No visible skylights but multiple dormers on upper floor",
    "Tight construction likely based on 2020+ build date and WA energy code",
    "Approximately 25% of main floor has vaulted ceilings affecting volume"
  ],
  "confidence": 0.85
}

Be thorough in observations - these contextual notes will guide load calculation assumptions."""
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse GPT-4V response with contextual data"""
        try:
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            # Handle new format with structured_data and contextual_notes
            if "structured_data" in data:
                # New enhanced format
                result = {
                    "rooms": data["structured_data"].get("rooms", []),
                    "total_area": data["structured_data"].get("total_area", 0),
                    "contextual_notes": data.get("contextual_notes", []),
                    "building_insights": data["structured_data"],  # Keep all structured data
                    "confidence": data.get("confidence", 0.85)
                }
            else:
                # Legacy format - still support it
                result = {
                    "rooms": data.get("rooms", []),
                    "total_area": data.get("total_area", 0),
                    "contextual_notes": [],  # No context in legacy format
                    "building_insights": {},
                    "confidence": data.get("confidence", 0.7)
                }
            
            # Calculate total area if needed
            if result["total_area"] == 0 and result["rooms"]:
                result["total_area"] = sum(r.get("area", 0) for r in result["rooms"])
            
            # Add metadata
            result["metadata"] = {
                "has_context": len(result.get("contextual_notes", [])) > 0
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse vision response: {e}")
            return {
                "rooms": [],
                "total_area": 0,
                "confidence": 0.0,
                "metadata": {"parse_error": str(e)}
            }


# Module-level instance
_vision_extractor = None

def get_vision_extractor():
    global _vision_extractor
    if _vision_extractor is None:
        try:
            _vision_extractor = VisionExtractor()
        except Exception as e:
            logger.error(f"Failed to create vision extractor: {e}")
            return None
    return _vision_extractor
