"""
Geometry-based fallback parser for AutoHVAC
Used when AI parsing fails to extract meaningful room data from blueprints
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4, UUID
from datetime import datetime

from .schema import BlueprintSchema, Room, RawGeometry, RawText, ParsingMetadata, ParsingStatus

logger = logging.getLogger(__name__)


class GeometryFallbackParser:
    """
    Fallback parser that creates room structures from raw geometry when AI fails
    
    This parser:
    1. Identifies room candidates from rectangles
    2. Matches text labels to rooms by proximity
    3. Calculates room areas from actual geometry
    4. Provides reasonable defaults for missing data
    """
    
    def __init__(self):
        # Room size thresholds (in square feet)
        self.MIN_ROOM_AREA = 15  # Minimum for closets
        self.MAX_ROOM_AREA = 800  # Maximum for residential rooms
        self.TYPICAL_CEILING_HEIGHT = 9.0  # feet
        
        # Room type classification by area
        self.ROOM_SIZE_RANGES = {
            'closet': (15, 50),
            'bathroom': (35, 100),
            'bedroom': (80, 300),
            'kitchen': (100, 300),
            'living': (150, 500),
            'dining': (100, 250),
            'hallway': (20, 150),
            'laundry': (30, 80),
            'pantry': (20, 60),
            'office': (80, 200),
        }
    
    def create_fallback_blueprint(
        self,
        raw_geo: RawGeometry,
        raw_text: RawText,
        zip_code: str,
        project_id: Optional[str] = None,
        metadata: Optional[ParsingMetadata] = None,
        error_msg: str = ""
    ) -> BlueprintSchema:
        """
        Create a blueprint from geometry when AI parsing fails
        
        Args:
            raw_geo: Raw geometry data
            raw_text: Raw text data
            zip_code: Project zip code
            project_id: Optional project ID
            metadata: Existing parsing metadata
            error_msg: Error message from failed parsing
            
        Returns:
            BlueprintSchema with geometry-based room data
        """
        logger.info(f"Creating geometry-based fallback blueprint (AI error: {error_msg})")
        
        # Initialize or update metadata
        if metadata is None:
            metadata = self._create_metadata()
        
        metadata.warnings.append(f"Using geometry fallback due to: {error_msg}")
        metadata.geometry_status = ParsingStatus.PARTIAL
        metadata.ai_status = ParsingStatus.FAILED
        
        # Extract rooms from geometry
        rooms = self._extract_rooms_from_geometry(raw_geo, raw_text)
        
        if not rooms:
            logger.warning("No valid rooms found in geometry - creating minimal fallback")
            rooms = self._create_minimal_fallback_rooms()
            metadata.geometry_status = ParsingStatus.FAILED
        
        # Calculate totals
        total_area = sum(room.area for room in rooms)
        
        # Log extraction results
        logger.info(f"Geometry fallback extracted {len(rooms)} rooms, total area: {total_area:.0f} sq ft")
        
        # Update confidence based on extraction success
        if len(rooms) >= 5:
            metadata.overall_confidence = 0.6
            metadata.geometry_confidence = 0.7
        else:
            metadata.overall_confidence = 0.3
            metadata.geometry_confidence = 0.4
        
        return BlueprintSchema(
            project_id=UUID(project_id) if project_id else uuid4(),
            zip_code=zip_code,
            sqft_total=total_area,
            stories=1,  # Default to single story
            rooms=rooms,
            raw_geometry=raw_geo.dict() if raw_geo else {},
            raw_text=raw_text.dict() if raw_text else {},
            dimensions=[],
            labels=[],
            geometric_elements=[],
            parsing_metadata=metadata
        )
    
    def _extract_rooms_from_geometry(
        self, 
        raw_geo: RawGeometry, 
        raw_text: RawText
    ) -> List[Room]:
        """Extract room structures from raw geometry data"""
        rooms = []
        
        # Get page dimensions for scaling
        page_width = raw_geo.page_width or 792.0
        page_height = raw_geo.page_height or 612.0
        scale_factor = raw_geo.scale_factor
        
        # If no scale factor detected, estimate based on typical architectural drawings
        if not scale_factor:
            # Estimate scale based on page size
            # Standard architectural drawings are often at 1/4" = 1' scale (48:1)
            # For a typical 2000 sq ft home on 24"x36" sheet:
            # Home dimensions ~40'x50', sheet ~800x1200 pixels at 72dpi
            # So scale factor = real_size / page_size * 12
            
            # Assume the page represents approximately 100' x 75' of real space
            # This is typical for residential floor plans
            estimated_width_ft = 100.0  # Typical building width on drawing
            estimated_height_ft = 75.0   # Typical building depth on drawing
            
            # Calculate scale factors for width and height
            # Using pixels per foot for consistency with geometry_parser.py
            scale_x = page_width / estimated_width_ft  # pixels per foot
            scale_y = page_height / estimated_height_ft  # pixels per foot
            
            # Use the average, but prefer standard architectural scales
            avg_scale = (scale_x + scale_y) / 2
            
            # Use the calculated scale directly
            scale_factor = avg_scale
            
            # Validate the calculated scale is reasonable
            # Typical architectural PDFs at 72 DPI have 6-12 pixels per foot
            if scale_factor < 4 or scale_factor > 20:
                logger.warning(f"Unusual scale {scale_factor:.1f} px/ft, using default 8 px/ft")
                scale_factor = 8.0  # Conservative default for residential blueprints
            
            logger.info(f"No scale detected, estimated scale factor: {scale_factor:.1f} pixels/foot")
        
        # Process rectangles as potential rooms
        rectangles = sorted(
            raw_geo.rectangles,
            key=lambda r: r.get('area', 0),
            reverse=True
        )
        
        # Track used labels to avoid duplicates
        used_labels = set()
        
        for idx, rect in enumerate(rectangles):
            # Calculate dimensions first
            width = rect.get('width', 0) or abs(rect.get('x1', 0) - rect.get('x0', 0))
            height = rect.get('height', 0) or abs(rect.get('y1', 0) - rect.get('y0', 0))
            
            # Skip if dimensions invalid
            if width <= 0 or height <= 0:
                continue
            
            # ALWAYS convert from page units to feet using scale factor
            # The geometry parser returns coordinates in page units (pixels/points)
            width_ft = width / scale_factor  # pixels / (pixels/foot) = feet
            height_ft = height / scale_factor
            area_ft = width_ft * height_ft
            
            # NOW check if the converted area is reasonable
            if area_ft < self.MIN_ROOM_AREA or area_ft > self.MAX_ROOM_AREA:
                logger.debug(f"Skipping rectangle {idx}: area {area_ft:.1f} sq ft outside range {self.MIN_ROOM_AREA}-{self.MAX_ROOM_AREA}")
                continue
            
            # Find nearby text label
            center_x = rect.get('center_x', (rect.get('x0', 0) + rect.get('x1', 0)) / 2)
            center_y = rect.get('center_y', (rect.get('y0', 0) + rect.get('y1', 0)) / 2)
            
            room_label = self._find_nearest_label(
                center_x, center_y, 
                raw_text.room_labels, 
                used_labels,
                max_distance=50
            )
            
            if room_label:
                room_name = room_label.get('text', 'Room')
                room_type = room_label.get('room_type', 'unknown')
                confidence = 0.7  # Higher confidence with label
                label_found = True
                used_labels.add(room_label.get('text'))
            else:
                # Infer room type from size
                room_type = self._infer_room_type_from_size(area_ft)
                room_name = f"{room_type.title()} {idx + 1}"
                confidence = 0.4  # Lower confidence without label
                label_found = False
            
            # Estimate windows based on room type and size
            windows = self._estimate_windows(room_type, area_ft)
            
            # Create room
            room = Room(
                name=f"{room_name} (Geometry)",
                dimensions_ft=(round(width_ft, 1), round(height_ft, 1)),
                floor=1,
                windows=windows,
                orientation="",  # Unknown from geometry alone
                area=round(area_ft, 0),
                room_type=room_type,
                confidence=confidence,
                center_position=(center_x, center_y),
                label_found=label_found,
                dimensions_source="geometry",
                source_elements={
                    "rectangle_index": idx,
                    "original_width": width,
                    "original_height": height,
                    "scale_factor": scale_factor,
                    "room_probability": rect.get('room_probability', 0.5),
                    "parsing_method": "geometry_fallback"
                }
            )
            
            rooms.append(room)
            
            # Stop if we have enough rooms
            if len(rooms) >= 20:
                break
        
        return rooms
    
    def _find_nearest_label(
        self,
        x: float,
        y: float,
        labels: List[Dict[str, Any]],
        used_labels: set,
        max_distance: float = 50
    ) -> Optional[Dict[str, Any]]:
        """Find the nearest unused text label to a point"""
        best_label = None
        best_distance = max_distance
        
        for label in labels:
            # Skip if already used
            if label.get('text') in used_labels:
                continue
            
            # Calculate distance
            label_x = label.get('x0', 0) + (label.get('width', 0) / 2 if 'width' in label else 0)
            label_y = label.get('top', label.get('y0', 0))
            
            distance = ((x - label_x) ** 2 + (y - label_y) ** 2) ** 0.5
            
            if distance < best_distance:
                best_distance = distance
                best_label = label
        
        return best_label
    
    def _infer_room_type_from_size(self, area: float) -> str:
        """Infer room type based on area"""
        # Check each room type's typical size range
        for room_type, (min_area, max_area) in self.ROOM_SIZE_RANGES.items():
            if min_area <= area <= max_area:
                # Prioritize common room types
                if room_type in ['bedroom', 'bathroom', 'kitchen', 'living']:
                    return room_type
        
        # Default classifications by size
        if area < 50:
            return 'closet'
        elif area < 100:
            return 'bathroom'
        elif area < 200:
            return 'bedroom'
        elif area < 350:
            return 'living'
        else:
            return 'other'
    
    def _estimate_windows(self, room_type: str, area: float) -> int:
        """Estimate number of windows based on room type and size"""
        # Room types that typically have fewer/no windows
        if room_type in ['bathroom', 'closet', 'pantry', 'hallway']:
            return 0 if room_type == 'closet' else 1
        
        # Estimate based on area for other rooms
        if area < 100:
            return 1
        elif area < 200:
            return 2
        elif area < 300:
            return 3
        else:
            return 4
    
    def _create_minimal_fallback_rooms(self) -> List[Room]:
        """Create minimal fallback rooms when geometry extraction fails"""
        logger.error("Creating minimal fallback room layout")
        
        # Single generic room as last resort
        return [
            Room(
                name="Main Space (Fallback)",
                dimensions_ft=(30.0, 33.7),
                floor=1,
                windows=4,
                orientation="",
                area=1010.0,
                room_type="other",
                confidence=0.1,
                center_position=(0.0, 0.0),
                label_found=False,
                dimensions_source="fallback",
                source_elements={
                    "error": "Complete parsing failure",
                    "warning": "Using generic layout - results unreliable"
                }
            )
        ]
    
    def _create_metadata(self) -> ParsingMetadata:
        """Create initial parsing metadata"""
        return ParsingMetadata(
            parsing_timestamp=datetime.utcnow(),
            processing_time_seconds=0.0,
            pdf_filename="unknown.pdf",
            pdf_page_count=0,
            selected_page=1,
            geometry_status=ParsingStatus.FAILED,
            text_status=ParsingStatus.FAILED,
            ai_status=ParsingStatus.FAILED,
            overall_confidence=0.0,
            geometry_confidence=0.0,
            text_confidence=0.0
        )


# Global instance
geometry_fallback_parser = GeometryFallbackParser()