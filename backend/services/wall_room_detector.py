"""
Wall-based Room Detection for Blueprints
Rooms are spaces enclosed by walls (lines), not filled rectangles
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np
import fitz  # PyMuPDF
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class Line:
    """Represents a wall line"""
    x1: float
    y1: float
    x2: float
    y2: float
    
    def length(self) -> float:
        return math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)
    
    def is_horizontal(self, tolerance: float = 5) -> bool:
        return abs(self.y2 - self.y1) < tolerance
    
    def is_vertical(self, tolerance: float = 5) -> bool:
        return abs(self.x2 - self.x1) < tolerance


@dataclass
class WallRoom:
    """Room detected from wall intersections"""
    polygon: List[Tuple[float, float]]  # Corner points
    area_sqft: float
    center: Tuple[float, float]
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2


class WallRoomDetector:
    """
    Detect rooms by finding enclosed spaces formed by walls
    This is how rooms actually exist in blueprints - as wall-enclosed spaces
    """
    
    def extract_rooms_from_walls(
        self,
        pdf_path: str,
        page_num: int,
        pixels_per_foot: float
    ) -> List[WallRoom]:
        """
        Extract rooms by detecting wall lines and finding enclosed spaces
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            pixels_per_foot: Scale conversion factor
            
        Returns:
            List of detected rooms
        """
        start_time = time.time()
        logger.info("Starting wall-based room detection...")
        
        # Step 1: Extract all lines (walls) from the PDF
        lines = self._extract_wall_lines(pdf_path, page_num)
        logger.info(f"Extracted {len(lines)} potential wall lines")
        
        # Step 2: Filter to keep only significant lines (likely walls)
        wall_lines = self._filter_wall_lines(lines, pixels_per_foot)
        logger.info(f"Filtered to {len(wall_lines)} wall lines")
        
        # Step 3: Find intersections and build graph
        rooms = self._find_enclosed_spaces(wall_lines, pixels_per_foot)
        logger.info(f"Found {len(rooms)} enclosed spaces (rooms)")
        
        # Step 4: Calculate areas and filter
        valid_rooms = self._validate_rooms(rooms, pixels_per_foot)
        logger.info(f"Validated {len(valid_rooms)} rooms in {time.time() - start_time:.2f}s")
        
        return valid_rooms
    
    def _extract_wall_lines(self, pdf_path: str, page_num: int) -> List[Line]:
        """Extract all lines from PDF drawings"""
        lines = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                doc.close()
                return lines
            
            page = doc[page_num]
            drawings = page.get_drawings()
            
            # Extract lines from drawing items
            for drawing in drawings:
                if 'items' in drawing:
                    for item in drawing['items']:
                        if item[0] == 'l':  # Line
                            p1, p2 = item[1], item[2]
                            # Convert points to coordinates
                            if hasattr(p1, 'x'):
                                x1, y1 = p1.x, p1.y
                                x2, y2 = p2.x, p2.y
                            else:
                                x1, y1 = p1
                                x2, y2 = p2
                            
                            lines.append(Line(x1, y1, x2, y2))
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting lines: {e}")
        
        return lines
    
    def _filter_wall_lines(
        self, 
        lines: List[Line], 
        pixels_per_foot: float
    ) -> List[Line]:
        """Filter lines to keep only those likely to be walls"""
        wall_lines = []
        
        # Minimum wall length (2 feet)
        min_wall_length = 2 * pixels_per_foot
        
        for line in lines:
            length = line.length()
            
            # Keep if:
            # 1. Long enough to be a wall
            # 2. Horizontal or vertical (most walls are)
            if length >= min_wall_length:
                if line.is_horizontal() or line.is_vertical():
                    wall_lines.append(line)
        
        return wall_lines
    
    def _find_enclosed_spaces(
        self,
        walls: List[Line],
        pixels_per_foot: float
    ) -> List[WallRoom]:
        """Find enclosed spaces formed by intersecting walls"""
        rooms = []
        
        # Group walls by proximity to find potential room boundaries
        # This is a simplified approach - a full implementation would use
        # graph algorithms to find closed polygons
        
        # Find axis-aligned bounding boxes formed by perpendicular walls
        horizontal_walls = [w for w in walls if w.is_horizontal()]
        vertical_walls = [w for w in walls if w.is_vertical()]
        
        # Sort walls by position
        horizontal_walls.sort(key=lambda w: w.y1)
        vertical_walls.sort(key=lambda w: w.x1)
        
        # Find rectangular regions (simplified room detection)
        # Look for rectangles formed by pairs of parallel walls
        for i, h_wall1 in enumerate(horizontal_walls):
            for h_wall2 in horizontal_walls[i+1:]:
                # Check if walls are roughly aligned horizontally
                if abs(h_wall1.x1 - h_wall2.x1) > 20 or abs(h_wall1.x2 - h_wall2.x2) > 20:
                    continue
                
                height = abs(h_wall2.y1 - h_wall1.y1)
                if height < 4 * pixels_per_foot or height > 30 * pixels_per_foot:
                    continue  # Room height should be reasonable
                
                # Find vertical walls that connect these horizontal walls
                for v_wall1 in vertical_walls:
                    for v_wall2 in vertical_walls:
                        if v_wall1 == v_wall2:
                            continue
                        
                        # Check if vertical walls connect the horizontal walls
                        if (self._walls_intersect_approx(h_wall1, v_wall1) and
                            self._walls_intersect_approx(h_wall1, v_wall2) and
                            self._walls_intersect_approx(h_wall2, v_wall1) and
                            self._walls_intersect_approx(h_wall2, v_wall2)):
                            
                            # Found a potential room
                            x1 = min(v_wall1.x1, v_wall2.x1)
                            x2 = max(v_wall1.x1, v_wall2.x1)
                            y1 = min(h_wall1.y1, h_wall2.y1)
                            y2 = max(h_wall1.y1, h_wall2.y1)
                            
                            width = x2 - x1
                            height = y2 - y1
                            
                            if width > 3 * pixels_per_foot and height > 3 * pixels_per_foot:
                                polygon = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                                area_pixels = width * height
                                area_sqft = area_pixels / (pixels_per_foot ** 2)
                                
                                rooms.append(WallRoom(
                                    polygon=polygon,
                                    area_sqft=area_sqft,
                                    center=((x1 + x2) / 2, (y1 + y2) / 2),
                                    bbox=(x1, y1, x2, y2)
                                ))
        
        # Remove duplicate/overlapping rooms
        unique_rooms = []
        for room in rooms:
            is_duplicate = False
            for existing in unique_rooms:
                if self._rooms_overlap(room, existing):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_rooms.append(room)
        
        return unique_rooms
    
    def _walls_intersect_approx(
        self,
        wall1: Line,
        wall2: Line,
        tolerance: float = 10
    ) -> bool:
        """Check if two walls intersect or nearly intersect"""
        # Simplified check for perpendicular walls
        if wall1.is_horizontal() and wall2.is_vertical():
            # Check if vertical wall crosses horizontal wall's y-level
            if (min(wall2.y1, wall2.y2) - tolerance <= wall1.y1 <= 
                max(wall2.y1, wall2.y2) + tolerance):
                # Check if horizontal wall crosses vertical wall's x-level
                if (min(wall1.x1, wall1.x2) - tolerance <= wall2.x1 <= 
                    max(wall1.x1, wall1.x2) + tolerance):
                    return True
        elif wall1.is_vertical() and wall2.is_horizontal():
            return self._walls_intersect_approx(wall2, wall1, tolerance)
        
        return False
    
    def _rooms_overlap(self, room1: WallRoom, room2: WallRoom) -> bool:
        """Check if two rooms overlap significantly"""
        x1_1, y1_1, x2_1, y2_1 = room1.bbox
        x1_2, y1_2, x2_2, y2_2 = room2.bbox
        
        # Calculate intersection
        ix1 = max(x1_1, x1_2)
        iy1 = max(y1_1, y1_2)
        ix2 = min(x2_1, x2_2)
        iy2 = min(y2_1, y2_2)
        
        if ix1 < ix2 and iy1 < iy2:
            intersection_area = (ix2 - ix1) * (iy2 - iy1)
            room1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
            room2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
            min_area = min(room1_area, room2_area)
            
            # If intersection is more than 50% of smaller room
            if intersection_area > min_area * 0.5:
                return True
        
        return False
    
    def _validate_rooms(
        self,
        rooms: List[WallRoom],
        pixels_per_foot: float
    ) -> List[WallRoom]:
        """Validate and filter rooms by reasonable criteria"""
        valid_rooms = []
        
        min_room_area = 20  # 20 sq ft minimum
        max_room_area = 1500  # 1500 sq ft maximum
        
        for room in rooms:
            if min_room_area <= room.area_sqft <= max_room_area:
                valid_rooms.append(room)
            else:
                logger.debug(f"Filtered out room with area {room.area_sqft:.1f} sq ft")
        
        return valid_rooms


# Global instance
wall_detector = WallRoomDetector()