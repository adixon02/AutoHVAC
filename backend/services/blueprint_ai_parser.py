"""
GPT-4 Vision Blueprint Parser for AutoHVAC
Converts PDF blueprints to structured JSON using OpenAI's Vision API
"""

import os
import json
import base64
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4, UUID
from io import BytesIO
from PIL import Image

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    
from openai import AsyncOpenAI
from app.parser.schema import (
    BlueprintSchema, Room, ParsingMetadata, ParsingStatus
)

logger = logging.getLogger(__name__)


class BlueprintAIParsingError(Exception):
    """Custom exception for AI blueprint parsing failures"""
    pass


class BlueprintAIParser:
    """
    AI-powered blueprint parser using GPT-4 Vision
    
    This service converts PDF blueprints to structured JSON by:
    1. Converting PDF pages to images
    2. Sending images to GPT-4V with specialized prompts
    3. Parsing the response into BlueprintSchema format
    4. Handling errors gracefully with fallbacks
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise BlueprintAIParsingError("OPENAI_API_KEY environment variable not set")
        
        # Configuration
        self.max_image_size = 20 * 1024 * 1024  # 20MB max for OpenAI
        self.target_dpi = 300  # High quality for blueprint analysis
        self.max_pages = 10  # Limit pages to analyze
        self.min_resolution = 800  # Minimum resolution to maintain blueprint readability
        
    async def parse_pdf_with_gpt4v(
        self, 
        pdf_path: str, 
        filename: str, 
        zip_code: str, 
        project_id: Optional[str] = None
    ) -> BlueprintSchema:
        """
        Parse PDF blueprint using GPT-4 Vision
        
        Args:
            pdf_path: Path to PDF file
            filename: Original filename
            zip_code: Project location
            project_id: Optional project ID
            
        Returns:
            BlueprintSchema with extracted room data
            
        Raises:
            BlueprintAIParsingError: If parsing fails
        """
        start_time = time.time()
        
        # Initialize metadata
        parsing_metadata = ParsingMetadata(
            parsing_timestamp=datetime.utcnow(),
            processing_time_seconds=0.0,
            pdf_filename=filename,
            pdf_page_count=0,
            selected_page=1,
            geometry_status=ParsingStatus.FAILED,
            text_status=ParsingStatus.FAILED,
            ai_status=ParsingStatus.FAILED,
            overall_confidence=0.0,
            geometry_confidence=0.0,
            text_confidence=0.0
        )
        
        logger.info(f"Starting GPT-4V blueprint parsing for {filename}")
        
        try:
            # Step 1: Convert PDF to images
            logger.info("Converting PDF to images...")
            images = self._convert_pdf_to_images(pdf_path)
            parsing_metadata.pdf_page_count = len(images)
            logger.info(f"Converted PDF to {len(images)} images")
            
            # Step 2: Try different pages until one works
            logger.info("Trying different pages for GPT-4V analysis...")
            blueprint_data = None
            successful_page = None
            
            # Try pages in order: 2, 1, 3, 4 (skip title pages, try floor plans first)
            page_order = [1, 0, 2, 3] if len(images) > 1 else [0]
            
            for page_idx in page_order:
                if page_idx < len(images):
                    try:
                        logger.info(f"Trying page {page_idx + 1} ({len(images[page_idx])} bytes)")
                        blueprint_data = await self._extract_blueprint_data(images[page_idx])
                        successful_page = page_idx
                        parsing_metadata.selected_page = page_idx + 1
                        logger.info(f"✅ Successfully extracted from page {page_idx + 1}")
                        break
                    except BlueprintAIParsingError as e:
                        logger.warning(f"❌ Page {page_idx + 1} failed: {str(e)}")
                        continue
            
            if blueprint_data is None:
                raise BlueprintAIParsingError("Failed to extract data from any page")
            
            parsing_metadata.ai_status = ParsingStatus.SUCCESS
            parsing_metadata.overall_confidence = 0.85
            logger.info(f"Successfully extracted {len(blueprint_data.get('rooms', []))} rooms from page {successful_page + 1}")
            
            # Step 4: Create BlueprintSchema
            blueprint_schema = self._create_blueprint_schema(
                blueprint_data, 
                project_id or str(uuid4()),
                zip_code,
                parsing_metadata
            )
            
            # Update final metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            blueprint_schema.parsing_metadata = parsing_metadata
            
            logger.info(f"GPT-4V parsing completed successfully in {parsing_metadata.processing_time_seconds:.2f}s")
            return blueprint_schema
            
        except Exception as e:
            # Record error in metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            parsing_metadata.errors_encountered.append({
                'stage': 'gpt4v_parsing',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': time.time()
            })
            
            logger.error(f"GPT-4V parsing failed for {filename}: {type(e).__name__}: {str(e)}")
            
            # Return minimal fallback blueprint
            return self._create_fallback_blueprint(zip_code, project_id, parsing_metadata, str(e))
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF pages to high-quality images using PyMuPDF (no poppler needed)"""
        try:
            import fitz  # PyMuPDF
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if total_pages == 0:
                raise BlueprintAIParsingError("PDF has no pages")
            
            logger.info(f"Converting {total_pages} pages to images using PyMuPDF")
            
            # Limit pages to process
            last_page = min(self.max_pages, total_pages)
            
            images = []
            for page_num in range(last_page):
                try:
                    page = doc[page_num]
                    
                    # Create moderate resolution for GPT-4V (1.5x zoom for good balance)
                    mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom for good quality without being too large
                    
                    # Render page as pixmap
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Try PNG first for lossless compression (better for line drawings)
                    png_bytes = pix.tobytes("png")
                    
                    if len(png_bytes) <= self.max_image_size:
                        logger.info(f"Page {page_num + 1}: Using PNG format ({len(png_bytes) / 1024 / 1024:.1f}MB)")
                        img_bytes = png_bytes
                    else:
                        # Fall back to JPEG with progressive compression
                        img_bytes = pix.tobytes("jpeg", jpg_quality=90)
                        logger.info(f"Page {page_num + 1}: Using JPEG format ({len(img_bytes) / 1024 / 1024:.1f}MB)")
                    
                    # Compress if still too large
                    if len(img_bytes) > self.max_image_size:
                        img_bytes = self._compress_image_for_gpt4v(img_bytes, page_num + 1, pix.width, pix.height)
                    
                    images.append(img_bytes)
                    logger.info(f"Page {page_num + 1} ready: {len(img_bytes) / 1024 / 1024:.1f}MB")
                    
                except Exception as e:
                    logger.error(f"Failed to convert page {page_num+1}: {str(e)}")
                    continue
            
            doc.close()
            
            if not images:
                raise BlueprintAIParsingError("Failed to convert any pages to images")
            
            # Log total conversion metrics
            total_size = sum(len(img) for img in images)
            logger.info(f"[METRICS] Converted {len(images)} pages, total size: {total_size / 1024 / 1024:.1f}MB")
            logger.info(f"Successfully converted {len(images)} pages to images")
            
            return images
            
        except Exception as e:
            raise BlueprintAIParsingError(f"Failed to convert PDF to images with PyMuPDF: {str(e)}")
    
    def _compress_image_for_gpt4v(self, img_bytes: bytes, page_num: int, orig_width: int, orig_height: int) -> bytes:
        """Compress image to stay under GPT-4V limit while maintaining readability"""
        logger.info(f"Compressing page {page_num} (original: {len(img_bytes) / 1024 / 1024:.1f}MB)")
        
        # First try JPEG quality reduction
        img = Image.open(BytesIO(img_bytes))
        
        # Try different JPEG qualities
        for quality in [85, 75, 65, 50]:
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            compressed = buffer.getvalue()
            
            if len(compressed) <= self.max_image_size:
                logger.info(f"Compressed page {page_num} to {len(compressed) / 1024 / 1024:.1f}MB with JPEG quality {quality}")
                return compressed
        
        # If still too large, reduce resolution while maintaining aspect ratio
        return self._reduce_resolution(img, page_num)
    
    def _reduce_resolution(self, img: Image.Image, page_num: int) -> bytes:
        """Reduce image resolution while maintaining minimum readability"""
        orig_width, orig_height = img.size
        
        # Calculate scaling factor to stay above minimum resolution
        min_dimension = min(orig_width, orig_height)
        
        # Try different scale factors
        for scale in [0.75, 0.5, 0.4]:
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            
            # Ensure minimum resolution for readability
            if min(new_width, new_height) < self.min_resolution:
                new_width = max(new_width, self.min_resolution)
                new_height = max(new_height, self.min_resolution)
            
            # Resize with high-quality resampling
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Try PNG first for resized image
            buffer = BytesIO()
            resized.save(buffer, format='PNG', optimize=True)
            png_bytes = buffer.getvalue()
            
            if len(png_bytes) <= self.max_image_size:
                logger.info(f"Reduced page {page_num} to {new_width}x{new_height} PNG ({len(png_bytes) / 1024 / 1024:.1f}MB)")
                return png_bytes
            
            # Try JPEG if PNG is too large
            buffer = BytesIO()
            resized.save(buffer, format='JPEG', quality=75, optimize=True)
            jpeg_bytes = buffer.getvalue()
            
            if len(jpeg_bytes) <= self.max_image_size:
                logger.info(f"Reduced page {page_num} to {new_width}x{new_height} JPEG ({len(jpeg_bytes) / 1024 / 1024:.1f}MB)")
                return jpeg_bytes
        
        # Last resort: very low quality JPEG at minimum resolution
        min_size = (self.min_resolution, self.min_resolution)
        last_resort = img.resize(min_size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        last_resort.save(buffer, format='JPEG', quality=40, optimize=True)
        result = buffer.getvalue()
        
        logger.warning(f"Page {page_num} compressed to minimum size: {len(result) / 1024 / 1024:.1f}MB")
        return result
    
    
    async def _extract_blueprint_data(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extract blueprint data using GPT-4V"""
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create the prompt
            prompt = self._create_blueprint_prompt()
            
            # Call GPT-4V (using gpt-4o which has vision capabilities)
            logger.info(f"Making GPT-4V API call with image size: {len(image_base64)} base64 chars")
            logger.info(f"Prompt length: {len(prompt)} chars")
            
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}",
                                        "detail": "low"  # Use low detail for complex blueprints
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.3  # Slightly higher temperature for flexibility
                )
                logger.info("GPT-4V API call completed successfully")
                
            except Exception as api_error:
                logger.error(f"GPT-4V API call failed: {type(api_error).__name__}: {str(api_error)}")
                raise BlueprintAIParsingError(f"GPT-4V API call failed: {str(api_error)}")
            
            # Parse response
            response_text = response.choices[0].message.content
            logger.info(f"GPT-4V response length: {len(response_text) if response_text else 0}")
            logger.info(f"GPT-4V response preview: {repr(response_text[:200]) if response_text else 'None'}")
            
            if not response_text or not response_text.strip():
                raise BlueprintAIParsingError("GPT-4V returned empty response")
            
            # Extract JSON from response (handle markdown code blocks)
            json_text = self._extract_json_from_response(response_text)
            logger.info(f"Extracted JSON preview: {repr(json_text[:200])}")
            blueprint_data = json.loads(json_text)
            
            # Validate response structure
            if not isinstance(blueprint_data, dict) or 'rooms' not in blueprint_data:
                raise BlueprintAIParsingError("Invalid response structure from GPT-4V")
            
            return blueprint_data
            
        except json.JSONDecodeError as e:
            raise BlueprintAIParsingError(f"Failed to parse GPT-4V response as JSON: {str(e)}")
        except Exception as e:
            raise BlueprintAIParsingError(f"GPT-4V API call failed: {str(e)}")
    
    def _create_blueprint_prompt(self) -> str:
        """Create comprehensive prompt for accurate HVAC data extraction with confidence tracking"""
        return """
Analyze this architectural floor plan for HVAC load calculations. Your goal is to identify ALL rooms in the building.

CRITICAL STEP 1 - FIND THE SCALE:
Look for scale notation in:
- Title block (usually bottom right)
- Near the drawing title
- Common formats: "1/4" = 1'-0"", "1/8" = 1'-0"", "3/16" = 1'-0"", "1:48", "SCALE: 1/4" = 1'-0""

CRITICAL STEP 2 - EXTRACT DIMENSIONS CORRECTLY:
- Read dimensions EXACTLY as shown (e.g., "12'-6"", "15'0"", "29 x 12")
- DO NOT convert or calculate - report raw dimensions
- Note whether dimensions are shown for each room

CRITICAL STEP 3 - IDENTIFY ALL ROOMS:
You MUST identify EVERY room visible on the floor plan, including:
- All bedrooms (Master, Bedroom 1, 2, 3, etc.)
- All bathrooms (Full bath, half bath, powder room)
- Kitchen and dining areas
- Living spaces (Living room, family room, great room)
- Utility spaces (Laundry, mudroom, pantry)
- Storage areas (Closets, storage rooms)
- Entry areas (Foyer, vestibule)
- Hallways and corridors
- Any other labeled spaces

Return the following JSON structure:

{
  "scale_found": true,
  "scale_notation": "1/4\" = 1'-0\"",
  "scale_factor": 48,
  "scale_confidence": 0.9,
  "north_arrow_found": false,
  "north_direction": "unknown",
  "orientation_confidence": 0.0,
  "total_area": 1500.0,
  "total_area_source": "labeled|calculated|estimated",
  "stories": 1,
  "rooms": [
    {
      "name": "Living Room",
      "raw_dimensions": "29' x 12'",
      "dimensions_ft": [29.0, 12.0],
      "area": 348.0,
      "area_matches_dimensions": true,
      "floor": 1,
      "windows": 2,
      "exterior_doors": 0,
      "orientation": "unknown",
      "room_type": "living",
      "exterior_walls": 1,
      "corner_room": false,
      "ceiling_height": 9.0,
      "confidence": 0.8,
      "dimension_source": "measured|estimated|unclear",
      "notes": "Clear dimensions visible on plan"
    }
  ]
}

IMPORTANT INSTRUCTIONS:
1. SCALE VALIDATION:
   - If scale_found is false, set all dimensions as "estimated" with confidence < 0.5
   - Common scale factors: 1/4"=1' is 48, 1/8"=1' is 96, 3/16"=1' is 64
   - CRITICAL: Report dimensions in FEET, not inches!

2. DIMENSION SANITY CHECKS:
   - Typical residential room sizes:
     * Bedroom: 100-200 sq ft (10x10 to 14x14)
     * Master bedroom: 150-400 sq ft
     * Bathroom: 20-100 sq ft
     * Kitchen: 100-300 sq ft
     * Living room: 200-400 sq ft
     * Great room: 300-800 sq ft
     * Closet: 10-50 sq ft
     * Hallway: 30-100 sq ft
   - If any room > 800 sq ft (except great rooms), double-check your dimensions
   - If total area > 10,000 sq ft for residential, flag as suspicious

3. ROOM DETECTION:
   - Scan the ENTIRE floor plan systematically
   - Expected room counts:
     * Small homes (1000-1500 sqft): 6-12 rooms
     * Medium homes (1500-2500 sqft): 10-18 rooms
     * Large homes (2500+ sqft): 15-30 rooms
   - Common missed rooms: Pantry, Laundry, Mudroom, Walk-in Closets, Powder rooms

4. AREA VALIDATION:
   - ALWAYS verify: width × length = area
   - Set area_matches_dimensions to false if calculation differs by > 5%
   - If dimensions produce unrealistic area (e.g., 29,000 sq ft for a room), flag it

5. CONFIDENCE SCORING:
   - 0.9-1.0: Clearly labeled room with visible dimensions that pass sanity checks
   - 0.7-0.8: Clearly labeled room without dimensions
   - 0.5-0.6: Unlabeled room with clear boundaries
   - 0.3-0.4: Partially visible or uncertain room
   - 0.0-0.2: Dimensions or area failed sanity checks

6. Mark dimension_source as:
   - "measured" if dimensions are clearly marked on the plan
   - "scaled" if you calculated from scale bar/grid
   - "estimated" if you're estimating from typical sizes
   - "error" if dimensions produce impossible areas

CONSTRUCTION DETAILS TO FIND:
- Wall construction (e.g., "2x6 frame", "R-21 insulation")
- Window specs (e.g., "Low-E", "U-0.30")
- Insulation values (e.g., "R-38 attic", "R-19 walls")
- Any scale or dimension notes

Return only valid JSON. Flag suspicious dimensions rather than reporting incorrect values.
"""
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from GPT response, handling markdown code blocks"""
        response_text = response_text.strip()
        
        # Remove markdown code block markers if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        return response_text.strip()
    
    def _create_blueprint_schema(
        self, 
        blueprint_data: Dict[str, Any], 
        project_id: str, 
        zip_code: str,
        parsing_metadata: ParsingMetadata
    ) -> BlueprintSchema:
        """Create BlueprintSchema from enhanced GPT-4V extracted data"""
        try:
            # Log scale information for debugging
            scale_found = blueprint_data.get('scale_found', False)
            scale_notation = blueprint_data.get('scale_notation', 'unknown')
            scale_factor = blueprint_data.get('scale_factor', 48)  # Default to 1/4" scale
            
            logger.info(f"Scale detection: found={scale_found}, notation={scale_notation}, factor={scale_factor}")
            
            # Extract rooms with enhanced data
            rooms = []
            suspicious_rooms = []
            
            for room_data in blueprint_data.get('rooms', []):
                # Extract and validate dimensions
                raw_dims = room_data.get('raw_dimensions', '')
                dims_ft = room_data.get('dimensions_ft', [12.0, 12.0])
                area = room_data.get('area', 144.0)
                area_matches = room_data.get('area_matches_dimensions', True)
                
                # Validate room area against typical sizes
                room_name = room_data.get('name', 'Unknown Room')
                room_type = room_data.get('room_type', self._classify_room_type(room_name))
                
                # Check for suspicious areas
                if area > 800 and room_type not in ['great_room', 'warehouse', 'garage']:
                    logger.warning(f"Suspicious room area: {room_name} = {area} sq ft (type: {room_type})")
                    suspicious_rooms.append(f"{room_name}: {area} sq ft")
                    # Reduce confidence for suspicious dimensions
                    room_data['confidence'] = min(room_data.get('confidence', 0.5), 0.3)
                
                # Extract confidence and validate
                confidence = room_data.get('confidence', 0.5)
                if confidence < 0.3:
                    logger.warning(f"Low confidence ({confidence}) for room: {room_name}")
                
                # Handle orientation with confidence tracking
                orientation = room_data.get('orientation', 'unknown')
                if orientation == 'unknown' or not blueprint_data.get('north_arrow_found', False):
                    orientation = 'unknown'
                    orientation_confidence = 0.0
                else:
                    orientation_confidence = blueprint_data.get('orientation_confidence', 0.5)
                
                room = Room(
                    name=room_name,
                    dimensions_ft=tuple(dims_ft),
                    floor=room_data.get('floor', 1),
                    windows=room_data.get('windows', 1),
                    orientation=orientation,
                    area=area,
                    room_type=room_type,
                    confidence=confidence,
                    center_position=(0.0, 0.0),  # Not available from vision
                    label_found=True,  # GPT-4V identified the room
                    dimensions_source=room_data.get('dimension_source', 'estimated'),
                    # Store enhanced HVAC data in source_elements for load calculations
                    source_elements={
                        "raw_dimensions": raw_dims,
                        "area_matches_dimensions": area_matches,
                        "exterior_doors": room_data.get('exterior_doors', 0),
                        "exterior_walls": room_data.get('exterior_walls', 1),
                        "corner_room": room_data.get('corner_room', False),
                        "ceiling_height": room_data.get('ceiling_height', 9.0),
                        "notes": room_data.get('notes', ''),
                        "scale_found": scale_found,
                        "scale_notation": scale_notation,
                        "scale_factor": scale_factor,
                        "north_arrow_found": blueprint_data.get('north_arrow_found', False),
                        "north_direction": blueprint_data.get('north_direction', 'unknown'),
                        "orientation_confidence": orientation_confidence,
                        "dimension_source": room_data.get('dimension_source', 'estimated'),
                        "thermal_exposure": self._calculate_thermal_exposure(room_data)
                    }
                )
                rooms.append(room)
            
            # Calculate totals and validate
            total_area_calculated = sum(room.area for room in rooms)
            total_area_declared = blueprint_data.get('total_area', total_area_calculated)
            total_area_source = blueprint_data.get('total_area_source', 'calculated')
            stories = blueprint_data.get('stories', 1)
            
            # Validate total area
            if total_area_declared > 10000:
                logger.warning(f"Suspicious total area: {total_area_declared} sq ft for residential building")
                if suspicious_rooms:
                    logger.warning(f"Suspicious rooms found: {', '.join(suspicious_rooms)}")
            
            # Check if calculated matches declared
            if abs(total_area_calculated - total_area_declared) / total_area_declared > 0.2:
                logger.warning(f"Total area mismatch: calculated={total_area_calculated}, declared={total_area_declared}")
            
            # Store building-level data in raw_geometry for Manual J calculations
            building_data = {
                "building_orientation": blueprint_data.get('building_orientation', ''),
                "total_conditioned_area": total_area_declared,
                "total_area_calculated": total_area_calculated,
                "total_area_source": total_area_source,
                "stories": stories,
                "parsing_method": "gpt4v_enhanced",
                "scale_found": scale_found,
                "scale_notation": scale_notation,
                "scale_factor": scale_factor,
                "suspicious_rooms": suspicious_rooms,
                "room_count": len(rooms),
                "hvac_load_factors": {
                    "total_exterior_windows": sum(room.windows for room in rooms),
                    "total_exterior_doors": sum(room.source_elements.get("exterior_doors", 0) for room in rooms),
                    "corner_rooms": len([r for r in rooms if r.source_elements.get("corner_room", False)]),
                    "thermal_zones": len(rooms)
                }
            }
            
            # Add warnings to parsing metadata
            if suspicious_rooms:
                parsing_metadata.warnings.append(f"Suspicious room areas detected: {', '.join(suspicious_rooms)}")
            if not scale_found:
                parsing_metadata.warnings.append("No scale found on blueprint - dimensions are estimated")
            
            return BlueprintSchema(
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                zip_code=zip_code,
                sqft_total=total_area_declared,
                stories=stories,
                rooms=rooms,
                raw_geometry=building_data,  # Enhanced building data for HVAC calculations
                raw_text={"ai_analysis_notes": [room.source_elements.get("notes", "") for room in rooms]},
                dimensions=[],  # Integrated into room data
                labels=[],  # Integrated into room data
                geometric_elements=[],  # Vision-based, not geometric
                parsing_metadata=parsing_metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating enhanced BlueprintSchema: {str(e)}")
            raise BlueprintAIParsingError(f"Failed to create blueprint schema: {str(e)}")
    
    def _calculate_thermal_exposure(self, room_data: Dict[str, Any]) -> str:
        """Calculate thermal exposure level for HVAC load calculations"""
        exterior_walls = room_data.get('exterior_walls', 1)
        corner_room = room_data.get('corner_room', False)
        windows = room_data.get('windows', 1)
        
        if corner_room and exterior_walls >= 2:
            return "high"  # Corner rooms with multiple exterior walls
        elif exterior_walls >= 2 or windows >= 3:
            return "medium"  # Multiple exterior walls or many windows
        else:
            return "low"  # Interior or minimally exposed rooms
    
    def _classify_room_type(self, room_name: str) -> str:
        """Classify room type from name"""
        name_lower = room_name.lower()
        
        if any(word in name_lower for word in ['bed', 'br']):
            return 'bedroom'
        elif any(word in name_lower for word in ['bath', 'ba']):
            return 'bathroom'
        elif any(word in name_lower for word in ['kitchen', 'kit']):
            return 'kitchen'
        elif any(word in name_lower for word in ['living', 'lr', 'family']):
            return 'living'
        elif any(word in name_lower for word in ['dining', 'dr']):
            return 'dining'
        elif any(word in name_lower for word in ['office', 'study', 'den']):
            return 'office'
        else:
            return 'other'
    
    def _create_fallback_blueprint(
        self, 
        zip_code: str, 
        project_id: Optional[str], 
        metadata: ParsingMetadata, 
        error: str
    ) -> BlueprintSchema:
        """Create fallback blueprint when GPT-4V parsing fails"""
        fallback_room = Room(
            name="GPT-4V Parsing Failed - Unknown Room",
            dimensions_ft=(20.0, 15.0),
            floor=1,
            windows=2,
            orientation="",
            area=300.0,
            room_type="unknown",
            confidence=0.0,
            center_position=(0.0, 0.0),
            label_found=False,
            dimensions_source="error_fallback"
        )
        
        return BlueprintSchema(
            project_id=UUID(project_id) if project_id and isinstance(project_id, str) else project_id or uuid4(),
            zip_code=zip_code,
            sqft_total=300.0,
            stories=1,
            rooms=[fallback_room],
            raw_geometry={},
            raw_text={},
            dimensions=[],
            labels=[],
            geometric_elements=[],
            parsing_metadata=metadata
        )


# Global instance
blueprint_ai_parser = BlueprintAIParser()