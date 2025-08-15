"""
Space Detector
Identifies individual rooms and spaces from blueprint text and geometry
Critical for zone-based thermal modeling
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from domain.models.spaces import Space, SpaceType, CeilingType, BoundaryCondition, Surface

logger = logging.getLogger(__name__)


@dataclass
class SpaceDetectionResult:
    """Result of space detection"""
    spaces: List[Space]
    total_detected_area: float
    confidence: float
    detection_method: str  # "text", "geometry", "hybrid"
    warnings: List[str]


class SpaceDetector:
    """
    Detects individual spaces/rooms from blueprints.
    This is critical for accurate zone-based load calculations.
    """
    
    # Room name patterns mapped to SpaceType (more selective)
    ROOM_PATTERNS = {
        SpaceType.BEDROOM: [
            'BEDROOM', 'MASTER BEDROOM', 'GUEST BEDROOM', 
            'BR 1', 'BR 2', 'BR 3', 'BR 4', 'BDRM'
        ],
        SpaceType.BATHROOM: [
            'BATHROOM', 'MASTER BATH', 'GUEST BATH', 'POWDER ROOM',
            'BATH 1', 'BATH 2', 'BATH 3', 'HALF BATH', 'FULL BATH'
        ],
        SpaceType.KITCHEN: [
            'KITCHEN', 'PANTRY'
        ],
        SpaceType.LIVING: [
            'LIVING ROOM', 'GREAT ROOM', 'FAMILY ROOM', 'DEN',
            'BONUS ROOM', 'REC ROOM', 'MEDIA ROOM', 'GAME ROOM',
            'BONUS', '2ND FLOOR (BONUS)', 'BONUS FLOOR PLAN'
        ],
        SpaceType.DINING: [
            'DINING ROOM', 'DINING', 'BREAKFAST NOOK', 'NOOK'
        ],
        SpaceType.HALLWAY: [
            'HALLWAY', 'HALL', 'FOYER', 'ENTRY', 'ENTRYWAY'
        ],
        SpaceType.STORAGE: [
            'CLOSET', 'STORAGE', 'UTILITY ROOM', 'LAUNDRY ROOM',
            'LAUNDRY', 'MUDROOM', 'MECHANICAL ROOM'
        ],
        SpaceType.GARAGE: [
            'GARAGE', '2 CAR GARAGE', '3 CAR GARAGE'
        ]
    }
    
    # Size validation ranges (sqft) by room type
    SIZE_RANGES = {
        SpaceType.BEDROOM: (80, 500),
        SpaceType.BATHROOM: (30, 200),
        SpaceType.KITCHEN: (80, 400),
        SpaceType.LIVING: (150, 600),
        SpaceType.DINING: (100, 300),
        SpaceType.HALLWAY: (20, 200),
        SpaceType.STORAGE: (10, 150),
        SpaceType.GARAGE: (200, 1200)
    }
    
    # Ceiling height indicators
    VAULTED_PATTERNS = [
        r'VAULTED', r'CATHEDRAL', r'COFFERED', r'TRAY',
        r'\d+[\'"]?\s*CEILING', r'HIGH\s*CEILING'
    ]
    
    # Floor level indicators
    FLOOR_PATTERNS = {
        1: [r'FIRST\s*FLOOR', r'MAIN\s*FLOOR', r'GROUND\s*FLOOR', r'1ST\s*FL', r'1ST\s*FLOOR'],
        2: [
            r'SECOND\s*FLOOR', r'UPPER\s*FLOOR', r'2ND\s*FL', r'2ND\s*FLOOR', 
            r'UPSTAIRS', r'BONUS\s*FLOOR', r'BONUS.*PLAN', r'2ND\s*FLOOR.*BONUS'
        ],
        0: [r'BASEMENT', r'LOWER\s*LEVEL', r'CELLAR']
    }
    
    def detect_spaces(
        self,
        text_blocks: List[Dict[str, Any]],
        vector_data: Optional[Dict[str, Any]] = None,
        page_info: Optional[Dict[str, Any]] = None,
        total_sqft: Optional[float] = None
    ) -> SpaceDetectionResult:
        """
        Detect all spaces from blueprint data.
        
        Args:
            text_blocks: Text extracted from PDF
            vector_data: Vector paths from PDF (optional)
            page_info: Page metadata (floor level, type, etc.)
            total_sqft: Total building square footage for validation
            
        Returns:
            SpaceDetectionResult with all detected spaces
        """
        logger.info("Detecting spaces from blueprint...")
        
        # 1. Determine floor level from page
        floor_level = self._detect_floor_level(text_blocks, page_info)
        
        # 2. Find room labels in text
        room_texts = self._find_room_labels(text_blocks)
        logger.info(f"Found {len(room_texts)} room labels")
        
        # 3. Extract spaces from text
        spaces = []
        total_area = 0
        warnings = []
        
        for room_text in room_texts:
            space = self._create_space_from_text(room_text, floor_level)
            if space:
                # Validate space size
                if self._validate_space_size(space):
                    spaces.append(space)
                    total_area += space.area_sqft
                else:
                    warnings.append(f"Invalid size for {space.name}: {space.area_sqft} sqft")
        
        # 4. Always try geometry detection if vector data available
        if vector_data:
            logger.info("Attempting geometry detection to supplement text-based rooms")
            geometry_spaces = self._detect_from_geometry(vector_data, floor_level)
            
            if geometry_spaces:
                geometry_area = sum(s.area_sqft for s in geometry_spaces)
                text_area = total_area
                
                logger.info(f"Geometry found {len(geometry_spaces)} spaces ({geometry_area:.0f} sqft)")
                logger.info(f"Text found {len(spaces)} spaces ({text_area:.0f} sqft)")
                
                # Use geometry if it finds significantly more area
                if len(geometry_spaces) > len(spaces) or geometry_area > text_area * 1.5:
                    logger.info("Using geometry detection as primary method")
                    spaces = geometry_spaces
                    total_area = geometry_area
                else:
                    # Merge geometry spaces that don't duplicate text
                    logger.info("Merging geometry with text-based detection")
                    for g_space in geometry_spaces:
                        if not self._is_duplicate(g_space, spaces):
                            spaces.append(g_space)
                            total_area += g_space.area_sqft
        
        # 5. Check for special rooms (bonus over garage)
        self._detect_special_conditions(spaces, page_info)
        
        # 6. Validate total area
        if total_sqft and total_area > 0:
            area_ratio = total_area / total_sqft
            if area_ratio < 0.7:
                warnings.append(f"Only detected {area_ratio:.0%} of total area")
            elif area_ratio > 1.3:
                warnings.append(f"Detected area exceeds total by {area_ratio:.0%}")
        
        # 7. Calculate confidence
        confidence = self._calculate_confidence(
            len(spaces),
            total_area,
            total_sqft,
            len(warnings)
        )
        
        # 8. Determine detection method
        if len(room_texts) > len(spaces) * 0.7:
            method = "text"
        elif vector_data:
            method = "hybrid"
        else:
            method = "text"
        
        result = SpaceDetectionResult(
            spaces=spaces,
            total_detected_area=total_area,
            confidence=confidence,
            detection_method=method,
            warnings=warnings
        )
        
        logger.info(f"Detected {len(spaces)} spaces, {total_area:.0f} sqft total, "
                   f"confidence={confidence:.2f}")
        
        return result
    
    def _detect_floor_level(
        self,
        text_blocks: List[Dict],
        page_info: Optional[Dict]
    ) -> int:
        """Detect which floor level this page represents"""
        
        # Check page info first
        if page_info and 'floor_level' in page_info:
            return page_info['floor_level']
        
        # Search text for floor indicators
        for block in text_blocks:
            text = block.get('text', '').upper()
            
            for level, patterns in self.FLOOR_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text):
                        logger.debug(f"Detected floor level {level} from: {text}")
                        return level
        
        # Default to main floor
        return 1
    
    def _detect_floor_from_name(self, room_name: str) -> int:
        """Detect floor level from room name (e.g., '2ND FLOOR (BONUS)')"""
        
        room_name_upper = room_name.upper()
        
        for level, patterns in self.FLOOR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, room_name_upper):
                    return level
        
        return 1  # Default to main floor
    
    def _find_room_labels(self, text_blocks: List[Dict]) -> List[Dict]:
        """Find text blocks that describe actual rooms (not building code text)"""
        room_texts = []
        
        for block in text_blocks:
            text = block.get('text', '').upper().strip()
            
            # Skip if too long (likely building code text)
            if len(text) > 50:
                continue
                
            # Skip if contains building code indicators
            building_code_indicators = [
                'SHALL', 'SECTION', 'CODE', 'IRC', 'MINIMUM', 'MAXIMUM',
                'COMPLY', 'REQUIRED', 'INSTALLED', 'PROVIDED', 'ACCORDANCE',
                'CONSTRUCTION', 'STRUCTURAL', 'FIRE', 'SAFETY', 'VENTILATION',
                'FOOTNOTE', 'TABLE', 'FIGURE', 'SPECIFICATION', 'R314',
                'NEW ATTACHED', 'WALL', 'FOR GARAGE', 'SERVICING', 'BY'
            ]
            
            if any(indicator in text for indicator in building_code_indicators):
                continue
            
            # Only match exact room patterns (be more selective)
            for space_type, patterns in self.ROOM_PATTERNS.items():
                for pattern in patterns:
                    # Make pattern matching more strict
                    if pattern == text or (pattern in text and len(text) <= 30):
                        # Look for associated area in nearby text or same text
                        area_match = re.search(r'(\d+)\s*(?:SQ\.?\s*FT\.?|SF)', text)
                        dimensions_match = re.search(r'(\d+)[\'"]?\s*[xX-]\s*(\d+)[\'"]?', text)
                        
                        room_info = {
                            'text': text,
                            'type': space_type,
                            'bbox': block.get('bbox', []),
                            'page': block.get('page', 0)
                        }
                        
                        if area_match:
                            area = float(area_match.group(1))
                            # Validate area is reasonable for a room
                            if 25 <= area <= 1000:
                                room_info['area'] = area
                            else:
                                continue  # Skip unreasonable areas
                        elif dimensions_match:
                            w = float(dimensions_match.group(1))
                            h = float(dimensions_match.group(2))
                            area = w * h
                            if 25 <= area <= 1000:
                                room_info['area'] = area
                                room_info['dimensions'] = (w, h)
                            else:
                                continue
                        
                        # Only add if we haven't seen this exact room already
                        if not any(existing['text'] == text for existing in room_texts):
                            room_texts.append(room_info)
                        break
        
        return room_texts
    
    def _create_space_from_text(
        self,
        room_text: Dict,
        floor_level: int
    ) -> Optional[Space]:
        """Create a Space object from text data"""
        
        # Extract room name
        text = room_text['text']
        space_type = room_text['type']
        
        # Detect floor level from room name itself (override default)
        detected_floor = self._detect_floor_from_name(text)
        if detected_floor != 1:  # If we detected a specific floor, use it
            floor_level = detected_floor
            logger.debug(f"Overrode floor level to {floor_level} for room: {text}")
        
        # Clean up room name
        name = text
        for pattern in [r'\d+\s*SQ\.?\s*FT\.?', r'\d+[\'"]?\s*[xX-]\s*\d+[\'"]?']:
            name = re.sub(pattern, '', name).strip()
        
        # Get area
        area = room_text.get('area', 0)
        if area == 0:
            # Try to estimate from type
            min_size, max_size = self.SIZE_RANGES.get(space_type, (100, 300))
            area = (min_size + max_size) / 2
            logger.debug(f"Estimated {name} area as {area} sqft")
        
        # Check for special ceiling
        ceiling_type = CeilingType.FLAT
        for pattern in self.VAULTED_PATTERNS:
            if re.search(pattern, text):
                ceiling_type = CeilingType.VAULTED
                break
        
        # Determine boundary conditions based on floor level
        if floor_level == 1:
            floor_over = BoundaryCondition.GROUND
            ceiling_under = BoundaryCondition.CONDITIONED  # Assume 2nd floor above
        elif floor_level == 2:
            floor_over = BoundaryCondition.CONDITIONED  # 1st floor below
            ceiling_under = BoundaryCondition.ATTIC
        else:
            floor_over = BoundaryCondition.GROUND
            ceiling_under = BoundaryCondition.CONDITIONED
        
        # Check if over garage (will be updated later)
        is_over_garage = False
        if floor_level == 2 and 'BONUS' in text:
            is_over_garage = True  # Provisional, will verify with garage detection
        
        space = Space(
            space_id=f"{name.lower().replace(' ', '_')}_{floor_level}",
            name=name,
            space_type=space_type,
            floor_level=floor_level,
            area_sqft=area,
            ceiling_height_ft=9.0 if ceiling_type == CeilingType.FLAT else 12.0,
            ceiling_type=ceiling_type,
            floor_over=floor_over,
            ceiling_under=ceiling_under,
            is_conditioned=(space_type != SpaceType.GARAGE),
            is_over_garage=is_over_garage,
            surfaces=[],  # Will be populated by envelope builder
            design_occupants=2 if space_type == SpaceType.BEDROOM else 0,
            detection_confidence=0.8 if 'area' in room_text else 0.5,
            evidence=[{
                'type': 'text',
                'value': text,
                'location': room_text.get('bbox', [])
            }]
        )
        
        return space
    
    def _detect_from_geometry(
        self,
        vector_data: Dict,
        floor_level: int
    ) -> List[Space]:
        """Detect spaces from geometric rectangles (adapted from pipeline_v2)"""
        spaces = []
        
        if not vector_data or not hasattr(vector_data, 'paths'):
            logger.debug("No vector paths available for geometry detection")
            return spaces
        
        paths = vector_data.paths
        rectangles = []
        
        # Look for rectangular paths that could be rooms
        for i, path in enumerate(paths[:1000]):  # Limit for performance
            # VectorPath objects have points and path_type attributes
            points = path.points
            path_type = path.path_type
            
            # Only process rectangles and closed paths
            if path_type == 'rect' and len(points) >= 4:
                # Calculate area
                if len(points) >= 4:
                    width = abs(points[1][0] - points[0][0])
                    height = abs(points[2][1] - points[1][1])
                    area = width * height
                    
                    # Filter for room-sized areas
                    if 50 <= area <= 1500:  # 50-1500 sqft rooms
                        rectangles.append({
                            'points': points[:4],
                            'area': area,
                            'width': width,
                            'height': height
                        })
        
        logger.info(f"Found {len(rectangles)} potential room rectangles")
        
        # Convert rectangles to Space objects
        for i, rect in enumerate(rectangles):
            # Generate a generic name
            name = f"Room {i+1}"
            space_type = SpaceType.LIVING  # Default type
            
            # Create space
            space = Space(
                space_id=f"geom_{floor_level}_{i}",
                name=name,
                space_type=space_type,
                area_sqft=rect['area'],
                volume_cuft=rect['area'] * 9.0,  # Assume 9ft ceiling
                floor_level=floor_level,
                ceiling_height_ft=9.0,
                ceiling_type=CeilingType.FLAT,
                boundary_conditions={}
            )
            
            spaces.append(space)
            logger.debug(f"Created geometric space: {name} ({rect['area']:.0f} sqft)")
        
        logger.info(f"Geometry detection created {len(spaces)} spaces, "
                   f"{sum(s.area_sqft for s in spaces):.0f} sqft total")
        
        return spaces
    
    def _detect_special_conditions(
        self,
        spaces: List[Space],
        page_info: Optional[Dict]
    ):
        """Detect special conditions like bonus over garage"""
        
        # Check page info for hints
        if page_info and page_info.get('has_bonus_over_garage'):
            # Find bonus room and mark it
            for space in spaces:
                if 'BONUS' in space.name.upper():
                    space.is_over_garage = True
                    space.floor_over = BoundaryCondition.GARAGE
                    logger.info(f"Marked {space.name} as bonus over garage")
        
        # Check for open-to-below spaces
        for space in spaces:
            if 'OPEN' in space.name.upper() and 'BELOW' in space.name.upper():
                space.open_to_below = True
                space.ceiling_type = CeilingType.OPEN_TO_BELOW
    
    def _validate_space_size(self, space: Space) -> bool:
        """Validate if space size is reasonable"""
        if space.area_sqft <= 0:
            return False
        
        if space.space_type in self.SIZE_RANGES:
            min_size, max_size = self.SIZE_RANGES[space.space_type]
            
            # Allow some flexibility (20% margin)
            return min_size * 0.8 <= space.area_sqft <= max_size * 1.2
        
        # Unknown type, accept if reasonable
        return 10 <= space.area_sqft <= 1000
    
    def _is_duplicate(
        self,
        new_space: Space,
        existing_spaces: List[Space]
    ) -> bool:
        """Check if space is duplicate of existing"""
        for existing in existing_spaces:
            # Check name similarity
            if existing.name == new_space.name:
                return True
            
            # Check area overlap (within 10%)
            if abs(existing.area_sqft - new_space.area_sqft) < 0.1 * existing.area_sqft:
                # Similar size and same floor
                if existing.floor_level == new_space.floor_level:
                    return True
        
        return False
    
    def _calculate_confidence(
        self,
        num_spaces: int,
        detected_area: float,
        total_area: Optional[float],
        num_warnings: int
    ) -> float:
        """Calculate detection confidence"""
        confidence = 0.5  # Base confidence
        
        # More spaces = higher confidence
        if num_spaces >= 10:
            confidence += 0.2
        elif num_spaces >= 5:
            confidence += 0.1
        
        # Good area coverage
        if total_area and detected_area > 0:
            coverage = detected_area / total_area
            if 0.8 <= coverage <= 1.2:
                confidence += 0.2
            elif 0.6 <= coverage <= 1.4:
                confidence += 0.1
        
        # Fewer warnings = higher confidence
        if num_warnings == 0:
            confidence += 0.1
        elif num_warnings > 3:
            confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))


# Singleton instance
_space_detector = None


def get_space_detector() -> SpaceDetector:
    """Get or create the global space detector"""
    global _space_detector
    if _space_detector is None:
        _space_detector = SpaceDetector()
    return _space_detector