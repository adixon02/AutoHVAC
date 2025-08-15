"""
Overlay Aligner
Aligns floor plans to detect vertically stacked spaces
Critical for identifying bonus-over-garage configurations
"""

import logging
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from domain.models.spaces import Space, SpaceType, BoundaryCondition

logger = logging.getLogger(__name__)


@dataclass
class FloorAlignment:
    """Result of aligning two floor plans"""
    aligned: bool
    offset_x: float  # Horizontal offset between floors
    offset_y: float  # Vertical offset between floors
    rotation: float  # Rotation angle if floors aren't aligned
    confidence: float
    overlapping_spaces: List[Tuple[Space, Space]]  # (upper, lower) pairs


@dataclass 
class OverlayResult:
    """Result of overlay analysis"""
    bonus_over_garage_detected: bool
    bonus_spaces: List[Space]
    garage_spaces: List[Space]
    alignment: FloorAlignment
    evidence: List[str]


class OverlayAligner:
    """
    Aligns multi-floor plans to detect vertical relationships.
    Essential for accurate thermal modeling of stacked spaces.
    """
    
    def __init__(self):
        self.overlap_threshold = 0.7  # 70% overlap to consider spaces stacked
        
    def detect_bonus_over_garage(
        self,
        all_spaces: List[Space],
        garage_result: Any = None
    ) -> OverlayResult:
        """
        Detect bonus room over garage configuration.
        
        Args:
            all_spaces: All detected spaces from all floors
            garage_result: Result from garage detector
            
        Returns:
            OverlayResult with bonus-over-garage detection
        """
        logger.info("Detecting bonus-over-garage configuration...")
        
        # Separate spaces by floor
        floor_1_spaces = [s for s in all_spaces if s.floor_level == 1]
        floor_2_spaces = [s for s in all_spaces if s.floor_level == 2]
        
        # Find garage on first floor
        garage_spaces = [
            s for s in floor_1_spaces 
            if s.space_type == SpaceType.GARAGE
        ]
        
        # Find potential bonus rooms on second floor
        bonus_candidates = [
            s for s in floor_2_spaces
            if 'BONUS' in s.name.upper() or 
            s.space_type == SpaceType.LIVING
        ]
        
        if not garage_spaces or not bonus_candidates:
            logger.info("No garage or bonus candidates found")
            return OverlayResult(
                bonus_over_garage_detected=False,
                bonus_spaces=[],
                garage_spaces=garage_spaces,
                alignment=FloorAlignment(
                    aligned=False, 
                    offset_x=0, 
                    offset_y=0, 
                    rotation=0, 
                    confidence=0,
                    overlapping_spaces=[]
                ),
                evidence=[]
            )
        
        # Deduplicate garage spaces (avoid counting same garage multiple times)
        unique_garages = []
        seen_areas = set()
        for garage in garage_spaces:
            area_key = round(garage.area_sqft / 50) * 50  # Round to nearest 50 sqft
            if area_key not in seen_areas:
                unique_garages.append(garage)
                seen_areas.add(area_key)
        
        garage_area = sum(g.area_sqft for g in unique_garages)
        evidence = []
        
        logger.info(f"Garage analysis: {len(garage_spaces)} detected, "
                   f"{len(unique_garages)} unique, {garage_area:.0f} sqft total")
        
        # Find bonus rooms that match garage footprint (more flexible matching)
        matched_bonus = []
        total_bonus_area = sum(b.area_sqft for b in bonus_candidates)
        
        # Try individual room matching first
        for bonus in bonus_candidates:
            area_ratio = bonus.area_sqft / garage_area if garage_area > 0 else 0
            
            # More flexible area matching for bonus-over-garage
            if 0.4 <= area_ratio <= 1.5:  # 40-150% range (bonus can be smaller than garage)
                matched_bonus.append(bonus)
                evidence.append(
                    f"Bonus room '{bonus.name}' ({bonus.area_sqft:.0f} sqft) "
                    f"overlaps garage area ({garage_area:.0f} sqft, ratio: {area_ratio:.1f})"
                )
                
                # Update space properties
                bonus.is_over_garage = True
                bonus.is_over_unconditioned = True
                bonus.floor_over = BoundaryCondition.GARAGE
                
                logger.info(f"Confirmed {bonus.name} is over garage (area ratio: {area_ratio:.2f})")
        
        # If no individual matches, try collective bonus area
        if not matched_bonus and total_bonus_area > 0:
            collective_ratio = total_bonus_area / garage_area
            if 0.5 <= collective_ratio <= 1.2:  # Collective bonus area matches garage
                matched_bonus = bonus_candidates
                evidence.append(
                    f"Total bonus area ({total_bonus_area:.0f} sqft) "
                    f"matches garage footprint ({garage_area:.0f} sqft)"
                )
                
                for bonus in matched_bonus:
                    bonus.is_over_garage = True
                    bonus.is_over_unconditioned = True
                    bonus.floor_over = BoundaryCondition.GARAGE
                    logger.info(f"Confirmed {bonus.name} is over garage (collective match)")
        
        # Additional evidence from garage detector
        if garage_result and garage_result.found:
            if garage_result.area_sqft > 0:
                evidence.append(
                    f"Garage detector found {garage_result.car_capacity}-car "
                    f"garage ({garage_result.area_sqft:.0f} sqft)"
                )
        
        # Check for explicit "bonus over garage" text
        for space in matched_bonus:
            if any(keyword in space.name.upper() for keyword in ['BONUS', 'SUITE', 'ROOM']):
                evidence.append(f"Space explicitly labeled as '{space.name}'")
        
        # Create alignment (simplified - would need actual geometry for real alignment)
        alignment = FloorAlignment(
            aligned=len(matched_bonus) > 0,
            offset_x=0,  # Assume aligned for now
            offset_y=0,
            rotation=0,
            confidence=0.8 if matched_bonus else 0.3,
            overlapping_spaces=[(b, garage_spaces[0]) for b in matched_bonus]
        )
        
        result = OverlayResult(
            bonus_over_garage_detected=len(matched_bonus) > 0,
            bonus_spaces=matched_bonus,
            garage_spaces=garage_spaces,
            alignment=alignment,
            evidence=evidence
        )
        
        if result.bonus_over_garage_detected:
            logger.info(f"Bonus-over-garage detected with {len(evidence)} evidence points")
            for e in evidence:
                logger.debug(f"  - {e}")
        
        return result
    
    def align_floor_plans(
        self,
        floor_1_spaces: List[Space],
        floor_2_spaces: List[Space],
        reference_points: Optional[List[Tuple[float, float]]] = None
    ) -> FloorAlignment:
        """
        Align two floor plans to find vertical relationships.
        
        Args:
            floor_1_spaces: Spaces on first floor
            floor_2_spaces: Spaces on second floor  
            reference_points: Optional known alignment points
            
        Returns:
            FloorAlignment with transformation parameters
        """
        
        # Simplified implementation
        # Full version would use:
        # 1. Feature matching (corners, stairs, plumbing stacks)
        # 2. ICP (Iterative Closest Point) algorithm
        # 3. RANSAC for robust alignment
        
        # For now, assume floors are aligned
        overlapping = []
        
        # Find overlapping spaces based on area and type
        for upper in floor_2_spaces:
            for lower in floor_1_spaces:
                if self._spaces_overlap(upper, lower):
                    overlapping.append((upper, lower))
        
        confidence = len(overlapping) / max(len(floor_2_spaces), 1)
        
        return FloorAlignment(
            aligned=len(overlapping) > 0,
            offset_x=0,
            offset_y=0,
            rotation=0,
            confidence=min(1.0, confidence),
            overlapping_spaces=overlapping
        )
    
    def _spaces_overlap(
        self,
        upper: Space,
        lower: Space
    ) -> bool:
        """
        Check if two spaces overlap vertically.
        Simplified - just checks area similarity.
        """
        
        # Special case: bonus over garage
        if (upper.space_type in [SpaceType.LIVING, SpaceType.BEDROOM] and
            lower.space_type == SpaceType.GARAGE):
            # Check area match
            area_ratio = upper.area_sqft / lower.area_sqft if lower.area_sqft > 0 else 0
            return 0.7 <= area_ratio <= 1.3
        
        # Regular spaces - would need actual geometry
        return False
    
    def calculate_thermal_impact(
        self,
        overlay_result: OverlayResult
    ) -> Dict[str, float]:
        """
        Calculate thermal impact of overlay configuration.
        
        Returns:
            Dictionary with thermal modifiers
        """
        
        impact = {
            'heating_modifier': 1.0,
            'cooling_modifier': 1.0,
            'infiltration_modifier': 1.0
        }
        
        if overlay_result.bonus_over_garage_detected:
            # Bonus over garage has significant thermal impact
            impact['heating_modifier'] = 1.3  # 30% more heating needed
            impact['cooling_modifier'] = 1.2  # 20% more cooling
            impact['infiltration_modifier'] = 1.4  # 40% more infiltration
            
            total_bonus_area = sum(s.area_sqft for s in overlay_result.bonus_spaces)
            
            logger.info(
                f"Thermal impact of {total_bonus_area:.0f} sqft bonus over garage: "
                f"heating +{(impact['heating_modifier']-1)*100:.0f}%, "
                f"cooling +{(impact['cooling_modifier']-1)*100:.0f}%, "
                f"infiltration +{(impact['infiltration_modifier']-1)*100:.0f}%"
            )
        
        return impact


# Singleton instance
_overlay_aligner = None


def get_overlay_aligner() -> OverlayAligner:
    """Get or create the global overlay aligner"""
    global _overlay_aligner
    if _overlay_aligner is None:
        _overlay_aligner = OverlayAligner()
    return _overlay_aligner