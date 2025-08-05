"""
Spatial Matching Module for Blueprint Parsing
Matches OCR text to geometric elements based on proximity
"""

import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpatialMatch:
    """Represents a match between text and geometry"""
    text: str
    text_bbox: List[float]  # [x0, y0, x1, y1]
    geometry_type: str  # 'line', 'rectangle', 'polygon'
    geometry_index: int
    distance: float
    confidence: float
    match_type: str  # 'dimension', 'room_label', 'annotation'


class SpatialMatcher:
    """
    Matches OCR text to geometric elements using spatial proximity
    Key component for accurate dimension and room label association
    """
    
    def __init__(self, proximity_threshold: float = 50.0):
        """
        Initialize spatial matcher
        
        Args:
            proximity_threshold: Maximum distance in pixels for text-geometry association
        """
        self.proximity_threshold = proximity_threshold
        
    def match_text_to_geometry(
        self,
        text_elements: List[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        rectangles: List[Dict[str, Any]],
        polygons: List[Dict[str, Any]] = None
    ) -> List[SpatialMatch]:
        """
        Match OCR text elements to geometric shapes based on proximity
        
        Args:
            text_elements: List of OCR text with bounding boxes
            lines: List of line segments (walls, dimension lines)
            rectangles: List of rectangles (rooms, areas)
            polygons: Optional list of complex polygons
            
        Returns:
            List of spatial matches with confidence scores
        """
        matches = []
        
        # Match dimension text to lines
        dimension_matches = self._match_dimensions_to_lines(text_elements, lines)
        matches.extend(dimension_matches)
        
        # Match room labels to rectangles/polygons
        room_matches = self._match_labels_to_rooms(text_elements, rectangles, polygons)
        matches.extend(room_matches)
        
        # Match annotations to nearest geometry
        annotation_matches = self._match_annotations(text_elements, lines, rectangles)
        matches.extend(annotation_matches)
        
        logger.info(f"Spatial matching complete: {len(matches)} matches found")
        logger.info(f"  - Dimensions: {len(dimension_matches)}")
        logger.info(f"  - Room labels: {len(room_matches)}")
        logger.info(f"  - Annotations: {len(annotation_matches)}")
        
        return matches
    
    def _match_dimensions_to_lines(
        self,
        text_elements: List[Dict[str, Any]],
        lines: List[Dict[str, Any]]
    ) -> List[SpatialMatch]:
        """
        Match dimension text (e.g., "12'-6"") to nearby lines
        """
        matches = []
        dimension_pattern = r"\d+['\"][\s\-]*\d*['\"]?"
        
        for text_elem in text_elements:
            text = text_elem.get('text', '')
            
            # Check if this is dimension text
            if not self._is_dimension_text(text):
                continue
            
            # Find nearest line
            text_center = self._get_bbox_center(text_elem)
            nearest_line = None
            min_distance = float('inf')
            best_line_idx = -1
            
            for idx, line in enumerate(lines):
                distance = self._distance_point_to_line(
                    text_center,
                    (line.get('x0', 0), line.get('y0', 0)),
                    (line.get('x1', 0), line.get('y1', 0))
                )
                
                if distance < min_distance and distance < self.proximity_threshold:
                    min_distance = distance
                    nearest_line = line
                    best_line_idx = idx
            
            if nearest_line:
                # Calculate match confidence based on distance
                confidence = max(0.0, 1.0 - (min_distance / self.proximity_threshold))
                
                match = SpatialMatch(
                    text=text,
                    text_bbox=[
                        text_elem.get('x0', 0),
                        text_elem.get('top', text_elem.get('y0', 0)),
                        text_elem.get('x1', text_elem.get('x0', 0) + 50),
                        text_elem.get('bottom', text_elem.get('top', 0) + 10)
                    ],
                    geometry_type='line',
                    geometry_index=best_line_idx,
                    distance=min_distance,
                    confidence=confidence,
                    match_type='dimension'
                )
                matches.append(match)
                
                logger.debug(f"Matched dimension '{text}' to line {best_line_idx} (distance: {min_distance:.1f})")
        
        return matches
    
    def _match_labels_to_rooms(
        self,
        text_elements: List[Dict[str, Any]],
        rectangles: List[Dict[str, Any]],
        polygons: Optional[List[Dict[str, Any]]] = None
    ) -> List[SpatialMatch]:
        """
        Match room labels to rectangles or polygons
        """
        matches = []
        room_keywords = ['bedroom', 'bath', 'kitchen', 'living', 'dining', 'closet', 
                        'hall', 'garage', 'office', 'laundry', 'pantry', 'master']
        
        for text_elem in text_elements:
            text = text_elem.get('text', '').lower()
            
            # Check if this is a room label
            if not any(keyword in text for keyword in room_keywords):
                continue
            
            text_center = self._get_bbox_center(text_elem)
            
            # Check rectangles first
            for idx, rect in enumerate(rectangles):
                if self._point_in_rectangle(text_center, rect):
                    match = SpatialMatch(
                        text=text_elem.get('text', ''),
                        text_bbox=[
                            text_elem.get('x0', 0),
                            text_elem.get('top', text_elem.get('y0', 0)),
                            text_elem.get('x1', text_elem.get('x0', 0) + 50),
                            text_elem.get('bottom', text_elem.get('top', 0) + 10)
                        ],
                        geometry_type='rectangle',
                        geometry_index=idx,
                        distance=0.0,  # Inside the rectangle
                        confidence=0.95,
                        match_type='room_label'
                    )
                    matches.append(match)
                    logger.debug(f"Matched room label '{text}' to rectangle {idx}")
                    break
            
            # Check polygons if provided
            if polygons:
                for idx, polygon in enumerate(polygons):
                    if self._point_in_polygon(text_center, polygon):
                        match = SpatialMatch(
                            text=text_elem.get('text', ''),
                            text_bbox=[
                                text_elem.get('x0', 0),
                                text_elem.get('top', text_elem.get('y0', 0)),
                                text_elem.get('x1', text_elem.get('x0', 0) + 50),
                                text_elem.get('bottom', text_elem.get('top', 0) + 10)
                            ],
                            geometry_type='polygon',
                            geometry_index=idx,
                            distance=0.0,
                            confidence=0.95,
                            match_type='room_label'
                        )
                        matches.append(match)
                        logger.debug(f"Matched room label '{text}' to polygon {idx}")
                        break
        
        return matches
    
    def _match_annotations(
        self,
        text_elements: List[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        rectangles: List[Dict[str, Any]]
    ) -> List[SpatialMatch]:
        """
        Match general annotations (R-values, notes, etc.) to nearest geometry
        """
        matches = []
        
        # Patterns for annotations
        annotation_patterns = [
            r'R-\d+',  # Insulation values
            r'U-[\d.]+',  # U-values
            r'typ\.?',  # Typical
            r'scale',  # Scale notations
            r'\d+\s*sq\.?\s*ft',  # Square footage
        ]
        
        for text_elem in text_elements:
            text = text_elem.get('text', '')
            
            # Check if this is an annotation
            is_annotation = any(
                re.search(pattern, text, re.IGNORECASE) 
                for pattern in annotation_patterns
            )
            
            if not is_annotation:
                continue
            
            # Find nearest geometry
            text_center = self._get_bbox_center(text_elem)
            nearest_geometry = None
            min_distance = float('inf')
            geometry_type = None
            geometry_idx = -1
            
            # Check lines
            for idx, line in enumerate(lines):
                distance = self._distance_point_to_line(
                    text_center,
                    (line.get('x0', 0), line.get('y0', 0)),
                    (line.get('x1', 0), line.get('y1', 0))
                )
                
                if distance < min_distance:
                    min_distance = distance
                    geometry_type = 'line'
                    geometry_idx = idx
            
            # Check rectangles
            for idx, rect in enumerate(rectangles):
                distance = self._distance_point_to_rectangle(text_center, rect)
                
                if distance < min_distance:
                    min_distance = distance
                    geometry_type = 'rectangle'
                    geometry_idx = idx
            
            if min_distance < self.proximity_threshold * 2:  # More lenient for annotations
                confidence = max(0.0, 1.0 - (min_distance / (self.proximity_threshold * 2)))
                
                match = SpatialMatch(
                    text=text,
                    text_bbox=[
                        text_elem.get('x0', 0),
                        text_elem.get('top', text_elem.get('y0', 0)),
                        text_elem.get('x1', text_elem.get('x0', 0) + 50),
                        text_elem.get('bottom', text_elem.get('top', 0) + 10)
                    ],
                    geometry_type=geometry_type,
                    geometry_index=geometry_idx,
                    distance=min_distance,
                    confidence=confidence,
                    match_type='annotation'
                )
                matches.append(match)
        
        return matches
    
    def _is_dimension_text(self, text: str) -> bool:
        """Check if text represents a dimension"""
        import re
        # Common dimension patterns
        patterns = [
            r"\d+['\"][\s\-]*\d*['\"]?",  # 12'-6" or 12'
            r"\d+\s*x\s*\d+",  # 12 x 14
            r"\d+\.?\d*\s*ft",  # 12.5 ft
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _get_bbox_center(self, text_elem: Dict[str, Any]) -> Tuple[float, float]:
        """Get center point of text bounding box"""
        x0 = text_elem.get('x0', 0)
        y0 = text_elem.get('top', text_elem.get('y0', 0))
        x1 = text_elem.get('x1', x0 + 50)  # Default width
        y1 = text_elem.get('bottom', y0 + 10)  # Default height
        
        return ((x0 + x1) / 2, (y0 + y1) / 2)
    
    def _distance_point_to_line(
        self,
        point: Tuple[float, float],
        line_start: Tuple[float, float],
        line_end: Tuple[float, float]
    ) -> float:
        """Calculate minimum distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector from line_start to line_end
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line is a point
            return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # Parameter t for closest point on line
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx*dx + dy*dy)))
        
        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance to closest point
        return np.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)
    
    def _point_in_rectangle(self, point: Tuple[float, float], rect: Dict[str, Any]) -> bool:
        """Check if point is inside rectangle"""
        x, y = point
        x0 = rect.get('x0', 0)
        y0 = rect.get('y0', 0)
        x1 = rect.get('x1', rect.get('x0', 0) + rect.get('width', 0))
        y1 = rect.get('y1', rect.get('y0', 0) + rect.get('height', 0))
        
        return x0 <= x <= x1 and y0 <= y <= y1
    
    def _point_in_polygon(self, point: Tuple[float, float], polygon: Dict[str, Any]) -> bool:
        """Check if point is inside polygon using ray casting algorithm"""
        x, y = point
        vertices = polygon.get('polygon', polygon.get('vertices', []))
        
        if not vertices:
            return False
        
        n = len(vertices)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i] if isinstance(vertices[i], (list, tuple)) else (vertices[i].get('x', 0), vertices[i].get('y', 0))
            xj, yj = vertices[j] if isinstance(vertices[j], (list, tuple)) else (vertices[j].get('x', 0), vertices[j].get('y', 0))
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def _distance_point_to_rectangle(self, point: Tuple[float, float], rect: Dict[str, Any]) -> float:
        """Calculate minimum distance from point to rectangle"""
        x, y = point
        x0 = rect.get('x0', 0)
        y0 = rect.get('y0', 0)
        x1 = rect.get('x1', rect.get('x0', 0) + rect.get('width', 0))
        y1 = rect.get('y1', rect.get('y0', 0) + rect.get('height', 0))
        
        # If point is inside, distance is 0
        if self._point_in_rectangle(point, rect):
            return 0.0
        
        # Otherwise, find minimum distance to edges
        distances = [
            self._distance_point_to_line(point, (x0, y0), (x1, y0)),  # Top
            self._distance_point_to_line(point, (x1, y0), (x1, y1)),  # Right
            self._distance_point_to_line(point, (x1, y1), (x0, y1)),  # Bottom
            self._distance_point_to_line(point, (x0, y1), (x0, y0)),  # Left
        ]
        
        return min(distances)