"""
North Arrow Detector
Detects north arrow orientation from vector glyphs and OCR text
"""

import logging
import numpy as np
import re
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import math

from services.vector_extractor import (
    VectorExtractor,
    VectorData,
    VectorPath,
    VectorText,
    get_vector_extractor
)

logger = logging.getLogger(__name__)


@dataclass
class NorthArrowResult:
    """Result of north arrow detection"""
    angle_degrees: float  # 0 = North pointing up, 90 = East, etc.
    confidence: float
    method: str  # 'vector_glyph', 'text_label', 'default'
    details: Dict[str, Any]


class NorthArrowDetector:
    """
    Detects north arrow orientation from blueprints
    Uses both vector analysis and text recognition
    """
    
    def __init__(self):
        self.vector_extractor = get_vector_extractor()
        
        # Common north arrow patterns
        self.arrow_keywords = ['north', 'n', 'true north', 'magnetic north']
        self.compass_keywords = ['n', 'e', 's', 'w', 'ne', 'nw', 'se', 'sw']
        
        # Arrow detection parameters
        self.min_arrow_length = 20  # pixels
        self.max_arrow_angle_deviation = 15  # degrees
        
    def detect_north_arrow(
        self,
        pdf_path: str,
        page_num: int = 0
    ) -> NorthArrowResult:
        """
        Detect north arrow orientation from a blueprint page
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to analyze
            
        Returns:
            NorthArrowResult with detected orientation
        """
        logger.info(f"Detecting north arrow on page {page_num + 1}")
        
        # Extract vector data
        vector_data = self.vector_extractor.extract_vectors(pdf_path, page_num)
        
        # Try multiple detection methods
        
        # 1. Try vector glyph detection (most accurate)
        result = self._detect_vector_arrow(vector_data)
        if result and result.confidence >= 0.8:
            logger.info(f"Found north arrow via vector: {result.angle_degrees}° "
                       f"(confidence: {result.confidence:.2%})")
            return result
        
        # 2. Try text-based detection
        result = self._detect_text_arrow(vector_data)
        if result and result.confidence >= 0.7:
            logger.info(f"Found north arrow via text: {result.angle_degrees}° "
                       f"(confidence: {result.confidence:.2%})")
            return result
        
        # 3. Try combined vector-text analysis
        result = self._detect_combined_arrow(vector_data)
        if result and result.confidence >= 0.6:
            logger.info(f"Found north arrow via combined analysis: {result.angle_degrees}° "
                       f"(confidence: {result.confidence:.2%})")
            return result
        
        # 4. Default to north pointing up
        logger.warning("No north arrow detected, defaulting to north = up")
        return NorthArrowResult(
            angle_degrees=0.0,
            confidence=0.3,
            method='default',
            details={'reason': 'No north arrow found'}
        )
    
    def _detect_vector_arrow(self, vector_data: VectorData) -> Optional[NorthArrowResult]:
        """
        Detect north arrow from vector graphics
        Looks for arrow-like shapes near north indicators
        """
        # Find text elements with north keywords
        north_texts = []
        for text in vector_data.texts:
            text_lower = text.text.lower().strip()
            if any(keyword in text_lower for keyword in self.arrow_keywords):
                north_texts.append(text)
        
        if not north_texts:
            return None
        
        # Look for arrow-like vectors near north text
        for north_text in north_texts:
            text_pos = north_text.position
            
            # Find nearby paths that could be arrows
            arrow_candidates = self._find_arrow_paths(
                vector_data.paths,
                text_pos,
                search_radius=100  # pixels
            )
            
            if arrow_candidates:
                # Analyze arrow direction
                arrow_angle = self._calculate_arrow_angle(arrow_candidates[0])
                
                return NorthArrowResult(
                    angle_degrees=arrow_angle,
                    confidence=0.9,
                    method='vector_glyph',
                    details={
                        'text_label': north_text.text,
                        'arrow_paths': len(arrow_candidates)
                    }
                )
        
        return None
    
    def _detect_text_arrow(self, vector_data: VectorData) -> Optional[NorthArrowResult]:
        """
        Detect north orientation from text labels
        E.g., "N ↑" or compass rose labels
        """
        # Look for compass direction labels
        compass_texts = {}
        for text in vector_data.texts:
            text_clean = text.text.strip().upper()
            if text_clean in ['N', 'E', 'S', 'W', 'NE', 'NW', 'SE', 'SW']:
                compass_texts[text_clean] = text.position
        
        if not compass_texts:
            return None
        
        # If we have N and at least one other direction, calculate orientation
        if 'N' in compass_texts:
            north_pos = compass_texts['N']
            
            # Check for other directions to determine rotation
            if 'E' in compass_texts:
                east_pos = compass_texts['E']
                # Calculate angle from N to E
                dx = east_pos[0] - north_pos[0]
                dy = east_pos[1] - north_pos[1]
                
                # Expected angle from N to E is 90 degrees
                actual_angle = math.degrees(math.atan2(dx, -dy))  # Negative dy for screen coords
                rotation = actual_angle - 90  # How much the compass is rotated
                
                return NorthArrowResult(
                    angle_degrees=rotation % 360,
                    confidence=0.85,
                    method='text_label',
                    details={
                        'compass_points': list(compass_texts.keys()),
                        'calculated_from': 'N-E'
                    }
                )
            
            elif 'S' in compass_texts:
                south_pos = compass_texts['S']
                # Calculate angle from N to S
                dx = south_pos[0] - north_pos[0]
                dy = south_pos[1] - north_pos[1]
                
                # Expected angle from N to S is 180 degrees
                actual_angle = math.degrees(math.atan2(dx, -dy))
                rotation = actual_angle - 180
                
                return NorthArrowResult(
                    angle_degrees=rotation % 360,
                    confidence=0.85,
                    method='text_label',
                    details={
                        'compass_points': list(compass_texts.keys()),
                        'calculated_from': 'N-S'
                    }
                )
        
        return None
    
    def _detect_combined_arrow(self, vector_data: VectorData) -> Optional[NorthArrowResult]:
        """
        Combined detection using both vectors and text
        Less accurate but more robust
        """
        # Look for any arrow-like shapes in the drawing
        all_arrows = []
        
        for path in vector_data.paths:
            if self._is_arrow_like(path):
                angle = self._calculate_path_angle(path)
                all_arrows.append(angle)
        
        if not all_arrows:
            return None
        
        # Look for text hints about orientation
        has_north_text = any(
            'north' in text.text.lower() 
            for text in vector_data.texts
        )
        
        if has_north_text and all_arrows:
            # Use the most vertical arrow as north
            # (closest to 0 or 180 degrees)
            best_arrow = min(all_arrows, key=lambda a: min(abs(a), abs(a - 180)))
            
            # Normalize to 0-360 range with 0 = north up
            if abs(best_arrow - 180) < abs(best_arrow):
                # Arrow points down, north is opposite
                north_angle = (best_arrow + 180) % 360
            else:
                # Arrow points up, that's north
                north_angle = best_arrow
            
            return NorthArrowResult(
                angle_degrees=north_angle,
                confidence=0.65,
                method='combined',
                details={
                    'arrow_count': len(all_arrows),
                    'has_north_text': has_north_text
                }
            )
        
        return None
    
    def _find_arrow_paths(
        self,
        paths: List[VectorPath],
        near_position: Tuple[float, float],
        search_radius: float
    ) -> List[VectorPath]:
        """Find paths that look like arrows near a position"""
        arrow_paths = []
        
        for path in paths:
            # Check if path is near the position
            if not self._is_path_near_position(path, near_position, search_radius):
                continue
            
            # Check if path looks like an arrow
            if self._is_arrow_like(path):
                arrow_paths.append(path)
        
        return arrow_paths
    
    def _is_path_near_position(
        self,
        path: VectorPath,
        position: Tuple[float, float],
        radius: float
    ) -> bool:
        """Check if any point in path is within radius of position"""
        for point in path.points:
            dx = point[0] - position[0]
            dy = point[1] - position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            if distance <= radius:
                return True
        return False
    
    def _is_arrow_like(self, path: VectorPath) -> bool:
        """Check if a path looks like an arrow"""
        if path.path_type != "line" or len(path.points) < 2:
            return False
        
        # Calculate path length
        total_length = 0
        for i in range(len(path.points) - 1):
            p1, p2 = path.points[i], path.points[i + 1]
            segment_length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            total_length += segment_length
        
        # Check minimum length
        if total_length < self.min_arrow_length:
            return False
        
        # Check if relatively straight (for simple arrows)
        if len(path.points) == 2:
            return True  # Simple line arrow
        
        # For multi-segment paths, check if segments form arrow shape
        # (This is simplified - could be enhanced with more sophisticated checks)
        if len(path.points) == 3:
            # Could be arrow with head (V shape at end)
            return True
        
        return False
    
    def _calculate_arrow_angle(self, path: VectorPath) -> float:
        """
        Calculate the angle of an arrow path
        Returns degrees with 0 = pointing up (north)
        """
        if len(path.points) < 2:
            return 0
        
        # For simple line arrows, use start to end
        if len(path.points) == 2:
            return self._calculate_path_angle(path)
        
        # For complex arrows, use the main shaft
        # (Simplified: use first to last point)
        p1 = path.points[0]
        p2 = path.points[-1]
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Calculate angle (0 degrees = pointing up)
        # Note: Screen coordinates have Y increasing downward
        angle = math.degrees(math.atan2(dx, -dy))
        
        return angle % 360
    
    def _calculate_path_angle(self, path: VectorPath) -> float:
        """Calculate angle of a path from start to end"""
        if len(path.points) < 2:
            return 0
        
        p1 = path.points[0]
        p2 = path.points[-1]
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Angle with 0 = pointing up (north)
        angle = math.degrees(math.atan2(dx, -dy))
        
        return angle % 360
    
    def apply_north_rotation(
        self,
        room_orientations: Dict[str, float],
        north_angle: float
    ) -> Dict[str, float]:
        """
        Apply north arrow rotation to room orientations
        
        Args:
            room_orientations: Original orientations (0 = east in drawing)
            north_angle: Detected north angle (0 = north pointing up)
            
        Returns:
            Corrected orientations with true north
        """
        corrected = {}
        
        for room_id, original_angle in room_orientations.items():
            # Rotate by north angle to get true orientation
            true_angle = (original_angle - north_angle) % 360
            corrected[room_id] = true_angle
        
        return corrected


# Singleton instance
_north_arrow_detector = None

def get_north_arrow_detector() -> NorthArrowDetector:
    """Get or create the global north arrow detector"""
    global _north_arrow_detector
    if _north_arrow_detector is None:
        _north_arrow_detector = NorthArrowDetector()
    return _north_arrow_detector