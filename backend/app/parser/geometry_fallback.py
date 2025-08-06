"""
Geometry-based fallback parser for AutoHVAC
Used when AI parsing fails to extract meaningful room data from blueprints
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4, UUID
from datetime import datetime

from .schema import BlueprintSchema, Room, RawGeometry, RawText, ParsingMetadata, ParsingStatus
from .exceptions import RoomDetectionFailedError, LowConfidenceError
from .polygon_detector import polygon_detector

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
        self.MIN_ROOM_AREA = 10  # Minimum for small closets/pantries
        self.MAX_ROOM_AREA = 1200  # Maximum for large residential rooms (great rooms)
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
        
        # First try polygon detection from wall lines
        rooms = []
        if raw_geo and raw_geo.lines and len(raw_geo.lines) > 10:
            logger.info("Attempting polygon-based room detection from wall lines")
            try:
                polygon_rooms = polygon_detector.detect_rooms(
                    lines=raw_geo.lines,
                    page_width=raw_geo.page_width,
                    page_height=raw_geo.page_height,
                    scale_factor=raw_geo.scale_factor
                )
                
                if polygon_rooms:
                    logger.info(f"Polygon detection found {len(polygon_rooms)} rooms")
                    # Convert polygon rooms to Room objects
                    for idx, poly_room in enumerate(polygon_rooms):
                        room = Room(
                            name=f"Room {idx + 1} (Polygon)",
                            dimensions_ft=(poly_room['width_ft'], poly_room['height_ft']),
                            floor=1,
                            windows=2,  # Default estimate
                            orientation="",
                            area=poly_room['area_sqft'],
                            room_type="unknown",
                            confidence=poly_room['confidence'],
                            center_position=poly_room['centroid'],
                            label_found=False,
                            dimensions_source="polygon_detection",
                            source_elements={
                                "detection_method": "polygon_from_walls",
                                "vertex_count": poly_room['vertex_count'],
                                "area_pixels": poly_room['area_pixels']
                            }
                        )
                        rooms.append(room)
                        
            except Exception as e:
                logger.error(f"Polygon detection failed: {e}")
        
        # If polygon detection didn't work, try rectangle extraction
        if not rooms:
            logger.info("Polygon detection failed or no walls found, trying rectangle extraction")
            rooms = self._extract_rooms_from_geometry(raw_geo, raw_text)
        
        if not rooms:
            logger.warning("No valid rooms found in geometry - trying alternative approaches")
            
            # First try: Relax thresholds even more
            original_min = self.MIN_ROOM_AREA
            original_max = self.MAX_ROOM_AREA
            self.MIN_ROOM_AREA = 8  # Lower threshold for tiny rooms
            self.MAX_ROOM_AREA = 1500  # Higher threshold for very large rooms
            
            rooms = self._extract_rooms_from_geometry(raw_geo, raw_text)
            
            # Restore original thresholds
            self.MIN_ROOM_AREA = original_min
            self.MAX_ROOM_AREA = original_max
            
            # Second try: If still no rooms and scale seems wrong, try different scales
            if not rooms and raw_geo.scale_factor:
                original_scale = raw_geo.scale_factor
                
                # Try common architectural scales if current scale seems wrong
                alternative_scales = []
                if original_scale > 80:  # Might be 1/8" scale incorrectly detected
                    alternative_scales = [48.0, 24.0, 12.0]  # Try 1/4", 1/2", 1" scales
                elif original_scale < 20:  # Might be too small
                    alternative_scales = [48.0, 96.0]  # Try 1/4", 1/8" scales
                
                for alt_scale in alternative_scales:
                    logger.info(f"Trying alternative scale factor: {alt_scale:.1f} px/ft (original: {original_scale:.1f})")
                    raw_geo.scale_factor = alt_scale
                    rooms = self._extract_rooms_from_geometry(raw_geo, raw_text)
                    if rooms:
                        logger.info(f"Success with alternative scale {alt_scale:.1f} - found {len(rooms)} rooms")
                        metadata.warnings.append(f"Used alternative scale {alt_scale:.1f} instead of detected {original_scale:.1f}")
                        break
                
                # Restore original scale if nothing worked
                if not rooms:
                    raw_geo.scale_factor = original_scale
            
            if not rooms:
                logger.error("Still no rooms found after trying alternatives - likely parsing issue")
                # NEVER create fallback silently - require user intervention
                walls_found = len(raw_geo.lines) if raw_geo and raw_geo.lines else 0
                raise RoomDetectionFailedError(
                    walls_found=walls_found,
                    polygons_found=0,
                    confidence=0.0
                )
        
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
        
        logger.info(f"Starting room extraction from geometry:")
        logger.info(f"  Page dimensions: {page_width:.0f} x {page_height:.0f} pixels")
        logger.info(f"  Scale factor from parser: {scale_factor}")
        logger.info(f"  Total rectangles to process: {len(raw_geo.rectangles)}")
        
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
        
        # Validate detected scale factor
        # Common architectural scales result in these pixel/foot ratios:
        # 1/8" = 1' → 96 px/ft (at 72 DPI)
        # 1/4" = 1' → 48 px/ft
        # 1/2" = 1' → 24 px/ft
        # 1" = 1' → 12 px/ft
        if scale_factor > 150 or scale_factor < 4:
            logger.warning(f"Scale factor {scale_factor:.1f} seems incorrect (outside 4-150 px/ft range)")
            logger.warning(f"This may indicate a parsing error or unusual drawing scale")
        
        # Process rectangles as potential rooms
        rectangles = sorted(
            raw_geo.rectangles,
            key=lambda r: r.get('area', 0),
            reverse=True
        )
        
        logger.info(f"Processing {len(rectangles)} rectangles as potential rooms")
        
        # Track used labels to avoid duplicates
        used_labels = set()
        filtered_count = 0
        
        for idx, rect in enumerate(rectangles):
            # Calculate dimensions first
            width = rect.get('width', 0) or abs(rect.get('x1', 0) - rect.get('x0', 0))
            height = rect.get('height', 0) or abs(rect.get('y1', 0) - rect.get('y0', 0))
            
            # Skip if dimensions invalid
            if width <= 0 or height <= 0:
                logger.debug(f"Rectangle {idx}: Skipped - invalid dimensions ({width} x {height})")
                continue
            
            # Use pre-converted values if available, otherwise convert from page units
            # The geometry parser now provides both pixel and feet measurements
            if rect.get('width_ft') is not None and rect.get('height_ft') is not None:
                width_ft = rect['width_ft']
                height_ft = rect['height_ft']
                area_ft = rect.get('area_sqft', width_ft * height_ft)
            else:
                # Fallback: convert from page units to feet using scale factor
                width_ft = width / scale_factor  # pixels / (pixels/foot) = feet
                height_ft = height / scale_factor
                area_ft = width_ft * height_ft
            
            # Log the conversion for debugging
            if idx < 5 or area_ft > 50:  # Log first 5 or significant rectangles
                logger.debug(f"Rectangle {idx}: page_units=({width:.0f}x{height:.0f}), "
                           f"feet=({width_ft:.1f}x{height_ft:.1f}), area={area_ft:.1f} sq ft")
            
            # NOW check if the converted area is reasonable
            # Be more lenient with filtering to catch more rooms
            if area_ft < self.MIN_ROOM_AREA:
                # Only filter if it's really too small (< MIN_ROOM_AREA)
                logger.debug(f"Rectangle {idx}: Filtered - area {area_ft:.1f} sq ft too small (< {self.MIN_ROOM_AREA})")
                filtered_count += 1
                continue
            elif area_ft > self.MAX_ROOM_AREA:
                # For large areas, check aspect ratio - might be entire floor
                aspect_ratio = max(width_ft, height_ft) / min(width_ft, height_ft)
                if aspect_ratio > 4.0:
                    # Very elongated - likely a wall or entire building
                    logger.debug(f"Rectangle {idx}: Filtered - area {area_ft:.1f} sq ft with aspect ratio {aspect_ratio:.1f}")
                    filtered_count += 1
                    continue
                elif area_ft > self.MAX_ROOM_AREA * 2:
                    # Way too large - likely entire floor or building outline
                    logger.debug(f"Rectangle {idx}: Filtered - area {area_ft:.1f} sq ft too large (> {self.MAX_ROOM_AREA * 2})")
                    filtered_count += 1
                    continue
                else:
                    # Large but reasonable - might be a great room or open concept
                    logger.info(f"Rectangle {idx}: Large room accepted - {area_ft:.1f} sq ft")
            
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
                logger.info(f"Reached maximum of 20 rooms, stopping extraction")
                break
        
        logger.info(f"Room extraction completed:")
        logger.info(f"  Rectangles processed: {len(rectangles)}")
        logger.info(f"  Rectangles filtered: {filtered_count}")
        logger.info(f"  Rooms extracted: {len(rooms)}")
        if rooms:
            total_area = sum(room.area for room in rooms)
            logger.info(f"  Total area: {total_area:.0f} sq ft")
        
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
        """DEPRECATED - Never create fallback rooms silently"""
        # This method should never be called anymore
        # We always raise an exception requiring user intervention
        raise RoomDetectionFailedError(
            walls_found=0,
            polygons_found=0,
            confidence=0.0
        )
    
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