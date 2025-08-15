"""
Stair Detector
Identifies stairs and stairwells for multi-floor alignment
Critical for properly aligning upper floors over lower floors
"""

import logging
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StairLocation:
    """Location and properties of detected stairs"""
    stair_id: str
    floor_from: int  # Starting floor (1=main, 2=second)
    floor_to: int    # Ending floor
    location_x: float  # X coordinate (center)
    location_y: float  # Y coordinate (center)
    width_ft: float    # Stair width
    length_ft: float   # Stair run length
    stair_type: str    # 'straight', 'L-shaped', 'U-shaped', 'spiral'
    is_open: bool      # Open stairwell (affects thermal)
    confidence: float
    evidence: List[str]


@dataclass
class FloorAlignmentAnchors:
    """Anchor points for aligning multiple floors"""
    stairs: List[StairLocation]
    plumbing_stacks: List[Tuple[float, float]]  # Bathrooms typically stack
    structural_walls: List[Tuple[float, float]]  # Load-bearing walls align
    chimney_locations: List[Tuple[float, float]]  # Chimneys go through floors
    alignment_confidence: float


class StairDetector:
    """
    Detects stairs and identifies alignment points between floors.
    Essential for accurate multi-story thermal modeling.
    """
    
    # Text patterns for stairs
    STAIR_PATTERNS = [
        r'STAIR(?:S|WELL|WAY)?',
        r'STR(?:S)?',  # Abbreviation
        r'UP\s*(?:TO|\/)',  # "UP TO 2ND"
        r'DN\s*(?:TO|\/)',  # "DN TO BASEMENT"
        r'DOWN\s*(?:TO|\/)',
        r'(?:TO|FROM)\s*(?:2ND|SECOND|UPPER|LOWER|BASEMENT)',
        r'OPEN\s*(?:TO|STAIR)',
        r'SPIRAL\s*STAIR',
        r'CIRCULAR\s*STAIR',
        r'WINDER',
        r'LANDING',
        r'RISER',
        r'TREAD'
    ]
    
    # Dimension patterns for stairs
    STAIR_DIMENSIONS = [
        r'(\d+)[\'"\s]*(?:RISERS?|R)',  # "14 RISERS"
        r'(\d+)[\'"\s]*(?:TREADS?|T)',  # "13 TREADS"
        r'(\d+)[\'"\s]*[xX]\s*(\d+)[\'"\s]*(?:STAIR|STR)',  # "4' x 12' STAIR"
        r'(?:STAIR|STR).*?(\d+)[\'"\s]*[xX]\s*(\d+)',
    ]
    
    # Plumbing fixtures (usually stack vertically)
    PLUMBING_PATTERNS = [
        r'(?:BATH|BATHROOM|BTH)\s*(?:ROOM)?',
        r'TOILET|WC|WATER\s*CLOSET',
        r'SHOWER|TUB|BATH',
        r'(?:KITCHEN|KIT)(?:CHEN)?',
        r'SINK',
        r'WASHER|LAUNDRY',
        r'POWDER\s*(?:ROOM)?'
    ]
    
    # Structural elements that align
    STRUCTURAL_PATTERNS = [
        r'BEARING\s*WALL',
        r'LOAD\s*BEARING',
        r'COLUMN|COL',
        r'POST',
        r'BEAM',
        r'CHIMNEY|FIREPLACE|FP'
    ]
    
    # Standard stair dimensions
    STANDARD_STAIR = {
        'min_width': 3.0,     # 3' minimum width
        'max_width': 6.0,     # 6' maximum typical
        'tread_depth': 0.916,  # 11" typical tread
        'riser_height': 0.625, # 7.5" typical riser
        'min_run': 10.0,      # Minimum run length
        'max_run': 20.0       # Maximum straight run
    }
    
    def detect_stairs(
        self,
        text_blocks: List[Dict[str, Any]],
        vector_data: Optional[Dict[str, Any]] = None,
        floor_level: int = 1
    ) -> List[StairLocation]:
        """
        Detect stairs in blueprint.
        
        Args:
            text_blocks: Text extracted from blueprint
            vector_data: Optional vector paths
            floor_level: Which floor this plan represents
            
        Returns:
            List of StairLocation objects
        """
        stairs = []
        
        # Find stair text annotations
        stair_texts = self._find_stair_text(text_blocks)
        
        for stair_text in stair_texts:
            stair = self._analyze_stair(stair_text, floor_level)
            if stair:
                stairs.append(stair)
        
        # Look for stairs in vector data if available
        if vector_data:
            vector_stairs = self._detect_stairs_from_vectors(vector_data)
            stairs.extend(vector_stairs)
        
        # Deduplicate
        stairs = self._deduplicate_stairs(stairs)
        
        if stairs:
            logger.info(f"Found {len(stairs)} stairs on floor {floor_level}")
            for stair in stairs:
                logger.debug(f"  {stair.stair_id}: {stair.stair_type} "
                           f"from floor {stair.floor_from} to {stair.floor_to}")
        
        return stairs
    
    def _find_stair_text(
        self,
        text_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find text blocks mentioning stairs"""
        
        stair_texts = []
        
        for block in text_blocks:
            text = block.get('text', '').upper()
            
            for pattern in self.STAIR_PATTERNS:
                if re.search(pattern, text):
                    stair_texts.append({
                        'text': text,
                        'bbox': block.get('bbox', []),
                        'page': block.get('page', 0)
                    })
                    break
        
        return stair_texts
    
    def _analyze_stair(
        self,
        stair_text: Dict[str, Any],
        floor_level: int
    ) -> Optional[StairLocation]:
        """Analyze stair text to create StairLocation"""
        
        text = stair_text['text']
        bbox = stair_text.get('bbox', [])
        evidence = []
        
        # Determine stair direction
        floor_from = floor_level
        floor_to = floor_level
        
        if 'UP' in text or 'TO 2ND' in text or 'TO SECOND' in text:
            floor_to = floor_level + 1
            evidence.append("Goes up")
        elif 'DN' in text or 'DOWN' in text or 'TO BASEMENT' in text:
            floor_to = floor_level - 1 if floor_level > 0 else 0
            evidence.append("Goes down")
        
        # Determine stair type
        stair_type = 'straight'  # Default
        if 'SPIRAL' in text or 'CIRCULAR' in text:
            stair_type = 'spiral'
            evidence.append("Spiral stair")
        elif 'WINDER' in text or 'L-SHAPE' in text:
            stair_type = 'L-shaped'
            evidence.append("L-shaped stair")
        elif 'U-SHAPE' in text or 'SWITCH' in text:
            stair_type = 'U-shaped'
            evidence.append("U-shaped stair")
        
        # Check if open
        is_open = 'OPEN' in text
        if is_open:
            evidence.append("Open stairwell")
        
        # Extract dimensions if present
        width = 3.5  # Default width
        length = 12.0  # Default length
        
        dim_match = re.search(r'(\d+)[\'"\s]*[xX]\s*(\d+)', text)
        if dim_match:
            width = float(dim_match.group(1))
            length = float(dim_match.group(2))
            evidence.append(f"Dimensions: {width}' x {length}'")
        
        # Calculate position from bbox if available
        if len(bbox) >= 4:
            location_x = (bbox[0] + bbox[2]) / 2
            location_y = (bbox[1] + bbox[3]) / 2
        else:
            location_x = 0
            location_y = 0
        
        # Generate ID
        stair_id = f"stair_f{floor_from}_to_f{floor_to}"
        
        return StairLocation(
            stair_id=stair_id,
            floor_from=floor_from,
            floor_to=floor_to,
            location_x=location_x,
            location_y=location_y,
            width_ft=width,
            length_ft=length,
            stair_type=stair_type,
            is_open=is_open,
            confidence=0.7 if evidence else 0.4,
            evidence=evidence
        )
    
    def _detect_stairs_from_vectors(
        self,
        vector_data: Dict[str, Any]
    ) -> List[StairLocation]:
        """Detect stairs from vector geometry"""
        
        # This would analyze vector paths to find:
        # - Parallel lines indicating stair treads
        # - Rectangular enclosures of stair size
        # - Zigzag patterns of stair symbols
        
        # Placeholder for now
        return []
    
    def _deduplicate_stairs(
        self,
        stairs: List[StairLocation]
    ) -> List[StairLocation]:
        """Remove duplicate stair detections"""
        
        unique = {}
        for stair in stairs:
            key = f"{stair.floor_from}_{stair.floor_to}"
            if key not in unique or unique[key].confidence < stair.confidence:
                unique[key] = stair
        
        return list(unique.values())
    
    def find_alignment_anchors(
        self,
        floor1_text: List[Dict[str, Any]],
        floor2_text: List[Dict[str, Any]],
        floor1_stairs: List[StairLocation],
        floor2_stairs: List[StairLocation]
    ) -> FloorAlignmentAnchors:
        """
        Find anchor points for aligning two floors.
        
        Args:
            floor1_text: Text from first floor
            floor2_text: Text from second floor
            floor1_stairs: Stairs detected on first floor
            floor2_stairs: Stairs detected on second floor
            
        Returns:
            FloorAlignmentAnchors with alignment points
        """
        
        # Combine stairs from both floors
        all_stairs = floor1_stairs + floor2_stairs
        
        # Find plumbing stacks (bathrooms above bathrooms)
        plumbing1 = self._find_plumbing_locations(floor1_text)
        plumbing2 = self._find_plumbing_locations(floor2_text)
        
        # Match plumbing between floors
        plumbing_stacks = self._match_vertical_features(plumbing1, plumbing2)
        
        # Find structural elements
        structural1 = self._find_structural_elements(floor1_text)
        structural2 = self._find_structural_elements(floor2_text)
        structural_walls = self._match_vertical_features(structural1, structural2)
        
        # Find chimneys/fireplaces
        chimney_locations = self._find_chimneys(floor1_text + floor2_text)
        
        # Calculate confidence
        anchor_count = (
            len(all_stairs) + 
            len(plumbing_stacks) + 
            len(structural_walls) + 
            len(chimney_locations)
        )
        
        confidence = min(1.0, anchor_count * 0.15)  # More anchors = better
        
        return FloorAlignmentAnchors(
            stairs=all_stairs,
            plumbing_stacks=plumbing_stacks,
            structural_walls=structural_walls,
            chimney_locations=chimney_locations,
            alignment_confidence=confidence
        )
    
    def _find_plumbing_locations(
        self,
        text_blocks: List[Dict[str, Any]]
    ) -> List[Tuple[float, float]]:
        """Find plumbing fixture locations"""
        
        locations = []
        
        for block in text_blocks:
            text = block.get('text', '').upper()
            bbox = block.get('bbox', [])
            
            for pattern in self.PLUMBING_PATTERNS:
                if re.search(pattern, text) and len(bbox) >= 4:
                    x = (bbox[0] + bbox[2]) / 2
                    y = (bbox[1] + bbox[3]) / 2
                    locations.append((x, y))
                    break
        
        return locations
    
    def _find_structural_elements(
        self,
        text_blocks: List[Dict[str, Any]]
    ) -> List[Tuple[float, float]]:
        """Find structural element locations"""
        
        locations = []
        
        for block in text_blocks:
            text = block.get('text', '').upper()
            bbox = block.get('bbox', [])
            
            for pattern in self.STRUCTURAL_PATTERNS:
                if re.search(pattern, text) and len(bbox) >= 4:
                    x = (bbox[0] + bbox[2]) / 2
                    y = (bbox[1] + bbox[3]) / 2
                    locations.append((x, y))
                    break
        
        return locations
    
    def _find_chimneys(
        self,
        text_blocks: List[Dict[str, Any]]
    ) -> List[Tuple[float, float]]:
        """Find chimney/fireplace locations"""
        
        locations = []
        
        for block in text_blocks:
            text = block.get('text', '').upper()
            bbox = block.get('bbox', [])
            
            if ('CHIMNEY' in text or 'FIREPLACE' in text or 'FP' in text) and len(bbox) >= 4:
                x = (bbox[0] + bbox[2]) / 2
                y = (bbox[1] + bbox[3]) / 2
                locations.append((x, y))
        
        return locations
    
    def _match_vertical_features(
        self,
        floor1_features: List[Tuple[float, float]],
        floor2_features: List[Tuple[float, float]],
        tolerance: float = 50.0  # Pixel tolerance
    ) -> List[Tuple[float, float]]:
        """Match features between floors that should align vertically"""
        
        matched = []
        
        for f1 in floor1_features:
            for f2 in floor2_features:
                distance = math.sqrt((f1[0] - f2[0])**2 + (f1[1] - f2[1])**2)
                if distance < tolerance:
                    # Average position
                    matched.append(((f1[0] + f2[0])/2, (f1[1] + f2[1])/2))
                    break
        
        return matched
    
    def calculate_thermal_impact(
        self,
        stairs: List[StairLocation]
    ) -> Dict[str, float]:
        """
        Calculate thermal impact of stairs.
        Open stairs increase stack effect and infiltration.
        
        Args:
            stairs: List of detected stairs
            
        Returns:
            Dict with thermal modifiers
        """
        
        impact = {
            'infiltration_modifier': 1.0,
            'stack_effect_modifier': 1.0,
            'volume_addition': 0  # Extra volume from stairwell
        }
        
        open_stairs = [s for s in stairs if s.is_open]
        
        if open_stairs:
            # Open stairs increase stack effect
            impact['stack_effect_modifier'] = 1.2  # 20% more
            impact['infiltration_modifier'] = 1.1  # 10% more
            
            # Add stairwell volume
            for stair in open_stairs:
                # Assume 2-story height for open stairwell
                stair_volume = stair.width_ft * stair.length_ft * 18  # 18' height
                impact['volume_addition'] += stair_volume
            
            logger.info(f"Open stairwell impact: +{(impact['stack_effect_modifier']-1)*100:.0f}% stack effect")
        
        return impact


# Singleton instance
_stair_detector = None


def get_stair_detector() -> StairDetector:
    """Get or create the global stair detector"""
    global _stair_detector
    if _stair_detector is None:
        _stair_detector = StairDetector()
    return _stair_detector