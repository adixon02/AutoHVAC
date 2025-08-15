"""
Orientation Extractor - Detects building orientation from North arrows and site plans
Critical for accurate solar gain calculations in Manual J
"""

import logging
import re
import math
from typing import Dict, Any, Optional, Tuple
import fitz
from PIL import Image
import io
import numpy as np

logger = logging.getLogger(__name__)


class OrientationExtractor:
    """
    Detects building orientation by finding:
    1. North arrows on floor plans
    2. Site plan orientation
    3. Solar orientation notes
    """
    
    def __init__(self):
        # Keywords that indicate orientation information
        self.orientation_keywords = [
            "NORTH", "TRUE NORTH", "MAGNETIC NORTH",
            "SITE PLAN", "PLOT PLAN", 
            "SOLAR", "SUN PATH",
            "STREET", "ROAD"  # Streets often indicate orientation
        ]
        
        # Common text near north arrows
        self.north_indicators = [
            "N", "NORTH", "TRUE N", "MAG N",
            "↑", "⬆", "▲"  # Arrow symbols
        ]
    
    def extract_orientation(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract building orientation from PDF
        
        Returns:
            {
                "has_north_arrow": bool,
                "north_direction": float,  # Degrees from top (0-360)
                "confidence": float,
                "orientation_notes": [],
                "wall_orientations": {
                    "north": [],  # Room names with north walls
                    "south": [],
                    "east": [],
                    "west": []
                }
            }
        """
        logger.info(f"Extracting orientation from {pdf_path}")
        
        doc = fitz.open(pdf_path)
        orientation_data = {
            "has_north_arrow": False,
            "north_direction": 0,  # Default: top of page is north
            "confidence": 0.0,
            "orientation_notes": [],
            "wall_orientations": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Look for north arrow in text
            text = page.get_text()
            if self._has_north_indicator(text):
                logger.info(f"Found north indicator on page {page_num + 1}")
                orientation_data["has_north_arrow"] = True
                orientation_data["confidence"] = 0.7
                
                # Try to extract specific orientation
                angle = self._extract_north_angle(page)
                if angle is not None:
                    orientation_data["north_direction"] = angle
                    orientation_data["confidence"] = 0.9
                
                # Extract any orientation notes
                notes = self._extract_orientation_notes(text)
                orientation_data["orientation_notes"].extend(notes)
                
                break  # Usually only one north arrow per set
        
        doc.close()
        
        # If no north arrow found, check for site plan
        if not orientation_data["has_north_arrow"]:
            orientation_data["confidence"] = 0.3
            orientation_data["orientation_notes"].append(
                "No north arrow found - assuming top of page is north"
            )
        
        # Determine wall orientations based on north direction
        orientation_data["wall_orientations"] = self._determine_wall_orientations(
            orientation_data["north_direction"]
        )
        
        logger.info(f"Orientation: North at {orientation_data['north_direction']}° "
                   f"(confidence: {orientation_data['confidence']:.0%})")
        
        return orientation_data
    
    def _has_north_indicator(self, text: str) -> bool:
        """Check if text contains north arrow indicators"""
        text_upper = text.upper()
        
        # Look for explicit north arrow text
        for indicator in self.north_indicators:
            if indicator in text_upper:
                # Make sure it's not part of other words
                if re.search(rf'\b{re.escape(indicator)}\b', text_upper):
                    return True
        
        # Look for compass/orientation references
        if any(keyword in text_upper for keyword in ["COMPASS", "ORIENTATION", "SITE PLAN"]):
            return True
        
        return False
    
    def _extract_north_angle(self, page: fitz.Page) -> Optional[float]:
        """
        Extract the angle of north from the page
        Returns degrees where 0 = top, 90 = right, 180 = bottom, 270 = left
        """
        try:
            # Look for drawings that might be north arrows
            drawings = page.get_drawings()
            
            for drawing in drawings:
                # North arrows are typically small symbols
                items = drawing.get("items", [])
                if len(items) < 10:  # Small drawing
                    # Check if it contains arrow-like shapes
                    for item in items:
                        if item[0] == "l":  # Line
                            # Could be an arrow shaft
                            # This is simplified - real implementation would
                            # analyze the geometry more thoroughly
                            pass
            
            # Look for text annotations with angles
            text = page.get_text()
            
            # Pattern for angles like "N 30° E" or "TRUE NORTH 45°"
            angle_pattern = r'NORTH.*?(\d+).*?°'
            match = re.search(angle_pattern, text.upper())
            if match:
                angle = float(match.group(1))
                # Convert to our coordinate system
                return angle
            
            # Default to straight up if north is indicated but no angle
            if "NORTH" in text.upper():
                return 0.0
                
        except Exception as e:
            logger.debug(f"Failed to extract north angle: {e}")
        
        return None
    
    def _extract_orientation_notes(self, text: str) -> list:
        """Extract any notes about orientation"""
        notes = []
        lines = text.split('\n')
        
        for line in lines:
            line_upper = line.upper()
            
            # Look for orientation-related notes
            if any(keyword in line_upper for keyword in ["NORTH", "SOUTH", "EAST", "WEST"]):
                if any(word in line_upper for word in ["FACING", "EXPOSURE", "SIDE", "WALL"]):
                    notes.append(line.strip())
            
            # Solar orientation notes
            if "SOLAR" in line_upper or "SUN" in line_upper:
                notes.append(line.strip())
            
            # Prevailing wind notes (affects infiltration)
            if "WIND" in line_upper and "PREVAILING" in line_upper:
                notes.append(line.strip())
        
        return notes[:5]  # Limit to 5 most relevant notes
    
    def _determine_wall_orientations(self, north_angle: float) -> Dict[str, list]:
        """
        Determine which walls face which direction based on north angle
        
        For now, returns generic guidance. With real room geometry,
        this would map specific rooms to orientations.
        """
        # Simplified - assumes rectangular building aligned with page
        orientations = {
            "north": ["Rooms at top of floor plan"],
            "south": ["Rooms at bottom of floor plan"],
            "east": ["Rooms at right of floor plan"],
            "west": ["Rooms at left of floor plan"]
        }
        
        # Adjust based on north angle
        if north_angle == 90:  # North is to the right
            orientations = {
                "north": ["Rooms at right of floor plan"],
                "south": ["Rooms at left of floor plan"],
                "east": ["Rooms at bottom of floor plan"],
                "west": ["Rooms at top of floor plan"]
            }
        elif north_angle == 180:  # North is at bottom
            orientations = {
                "north": ["Rooms at bottom of floor plan"],
                "south": ["Rooms at top of floor plan"],
                "east": ["Rooms at left of floor plan"],
                "west": ["Rooms at right of floor plan"]
            }
        elif north_angle == 270:  # North is to the left
            orientations = {
                "north": ["Rooms at left of floor plan"],
                "south": ["Rooms at right of floor plan"],
                "east": ["Rooms at top of floor plan"],
                "west": ["Rooms at bottom of floor plan"]
            }
        
        return orientations
    
    def determine_room_orientation(
        self, 
        room_position: Tuple[float, float],
        building_center: Tuple[float, float],
        north_angle: float
    ) -> str:
        """
        Determine which direction a room faces based on its position
        
        Args:
            room_position: (x, y) coordinates of room center
            building_center: (x, y) coordinates of building center
            north_angle: Angle of north in degrees
            
        Returns:
            Primary orientation: "north", "south", "east", or "west"
        """
        # Calculate angle from building center to room
        dx = room_position[0] - building_center[0]
        dy = room_position[1] - building_center[1]
        
        # Angle in degrees (0 = right, 90 = up, 180 = left, 270 = down)
        room_angle = math.degrees(math.atan2(-dy, dx))  # Negative dy for PDF coordinates
        if room_angle < 0:
            room_angle += 360
        
        # Adjust for north orientation
        adjusted_angle = (room_angle - north_angle) % 360
        
        # Determine cardinal direction
        if 315 <= adjusted_angle or adjusted_angle < 45:
            return "east"
        elif 45 <= adjusted_angle < 135:
            return "north"
        elif 135 <= adjusted_angle < 225:
            return "west"
        else:
            return "south"


# Module instance
_orientation_extractor = None

def get_orientation_extractor():
    global _orientation_extractor
    if _orientation_extractor is None:
        _orientation_extractor = OrientationExtractor()
    return _orientation_extractor