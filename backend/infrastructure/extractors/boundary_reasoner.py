"""
Boundary Reasoner
Intelligently determines thermal boundary conditions for spaces
Critical for accurate heat transfer calculations
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from domain.models.spaces import Space, SpaceType, BoundaryCondition

logger = logging.getLogger(__name__)


@dataclass
class BoundaryAnalysis:
    """Analysis of a thermal boundary"""
    space_id: str
    surface_type: str  # 'floor', 'ceiling', 'wall'
    adjacent_condition: BoundaryCondition
    adjacent_space_id: Optional[str]
    temperature_difference: float  # Expected ΔT
    heat_flow_direction: str  # 'out', 'in', 'neutral'
    confidence: float
    reasoning: List[str]


class BoundaryReasoner:
    """
    Reasons about thermal boundary conditions between spaces.
    Uses building physics and spatial relationships to determine conditions.
    """
    
    # Temperature assumptions for adjacent conditions (winter/summer)
    ADJACENT_TEMPS = {
        # Winter conditions (heating)
        'winter': {
            BoundaryCondition.EXTERIOR: 0,      # Outdoor design temp
            BoundaryCondition.GROUND: 45,       # Ground temperature
            BoundaryCondition.GARAGE: 40,       # Unheated garage
            BoundaryCondition.CRAWLSPACE: 35,   # Vented crawl
            BoundaryCondition.ATTIC: 20,        # Vented attic
            BoundaryCondition.CONDITIONED: 70,  # Other conditioned space
            BoundaryCondition.UNCONDITIONED: 50, # Generic unconditioned
            BoundaryCondition.ADIABATIC: 70    # No heat transfer
        },
        # Summer conditions (cooling)
        'summer': {
            BoundaryCondition.EXTERIOR: 95,
            BoundaryCondition.GROUND: 55,
            BoundaryCondition.GARAGE: 85,
            BoundaryCondition.CRAWLSPACE: 75,
            BoundaryCondition.ATTIC: 120,       # Hot attic
            BoundaryCondition.CONDITIONED: 75,
            BoundaryCondition.UNCONDITIONED: 85,
            BoundaryCondition.ADIABATIC: 75
        }
    }
    
    def analyze_space_boundaries(
        self,
        space: Space,
        all_spaces: List[Space],
        building_info: Dict[str, Any]
    ) -> List[BoundaryAnalysis]:
        """
        Analyze all boundaries of a space.
        
        Args:
            space: Space to analyze
            all_spaces: All spaces in building
            building_info: Building metadata
            
        Returns:
            List of BoundaryAnalysis for each surface
        """
        analyses = []
        
        # Analyze floor
        floor_analysis = self._analyze_floor(space, all_spaces, building_info)
        if floor_analysis:
            analyses.append(floor_analysis)
        
        # Analyze ceiling
        ceiling_analysis = self._analyze_ceiling(space, all_spaces, building_info)
        if ceiling_analysis:
            analyses.append(ceiling_analysis)
        
        # Analyze walls (simplified - assumes all exterior for now)
        wall_analysis = self._analyze_walls(space, all_spaces, building_info)
        analyses.extend(wall_analysis)
        
        return analyses
    
    def _analyze_floor(
        self,
        space: Space,
        all_spaces: List[Space],
        building_info: Dict[str, Any]
    ) -> Optional[BoundaryAnalysis]:
        """Analyze what's below this space"""
        
        reasoning = []
        confidence = 0.5
        
        # Check space's existing floor_over attribute
        if space.floor_over:
            adjacent = space.floor_over
            reasoning.append(f"Floor over {adjacent.value} (from space data)")
            confidence = 0.8
        else:
            # Reason based on floor level and building type
            if space.floor_level == 1:
                # First floor
                foundation_type = building_info.get('foundation_type', 'slab')
                
                if foundation_type == 'slab':
                    adjacent = BoundaryCondition.GROUND
                    reasoning.append("First floor on slab-on-grade")
                elif foundation_type == 'crawlspace':
                    adjacent = BoundaryCondition.CRAWLSPACE
                    reasoning.append("First floor over crawlspace")
                elif foundation_type == 'basement':
                    adjacent = BoundaryCondition.CONDITIONED  # Assume finished basement
                    reasoning.append("First floor over basement")
                else:
                    adjacent = BoundaryCondition.GROUND
                    reasoning.append("First floor, assuming ground contact")
                
                confidence = 0.7
                
            elif space.floor_level == 2:
                # Second floor
                
                # Check if over garage (special case)
                if space.is_over_garage:
                    adjacent = BoundaryCondition.GARAGE
                    reasoning.append("Second floor space over garage")
                    confidence = 0.9
                else:
                    # Look for space directly below
                    space_below = self._find_space_below(space, all_spaces)
                    
                    if space_below:
                        if space_below.is_conditioned:
                            adjacent = BoundaryCondition.CONDITIONED
                            reasoning.append(f"Over conditioned space: {space_below.name}")
                        else:
                            adjacent = BoundaryCondition.UNCONDITIONED
                            reasoning.append(f"Over unconditioned space: {space_below.name}")
                        confidence = 0.8
                    else:
                        # Assume over conditioned space
                        adjacent = BoundaryCondition.CONDITIONED
                        reasoning.append("Second floor, assuming over conditioned space")
                        confidence = 0.6
            
            elif space.floor_level == 0:
                # Basement
                adjacent = BoundaryCondition.GROUND
                reasoning.append("Basement floor on ground")
                confidence = 0.9
            
            else:
                adjacent = BoundaryCondition.CONDITIONED
                reasoning.append("Unknown floor level, assuming conditioned below")
                confidence = 0.4
        
        # Calculate temperature difference
        winter_delta = 70 - self.ADJACENT_TEMPS['winter'][adjacent]
        
        return BoundaryAnalysis(
            space_id=space.space_id,
            surface_type='floor',
            adjacent_condition=adjacent,
            adjacent_space_id=None,  # Could be populated if we found specific space
            temperature_difference=winter_delta,
            heat_flow_direction='out' if winter_delta > 0 else 'neutral',
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _analyze_ceiling(
        self,
        space: Space,
        all_spaces: List[Space],
        building_info: Dict[str, Any]
    ) -> Optional[BoundaryAnalysis]:
        """Analyze what's above this space"""
        
        reasoning = []
        confidence = 0.5
        
        # Check space's existing ceiling_under attribute
        if space.ceiling_under:
            adjacent = space.ceiling_under
            reasoning.append(f"Ceiling under {adjacent.value} (from space data)")
            confidence = 0.8
        else:
            total_floors = building_info.get('floor_count', 2)
            
            if space.floor_level == total_floors:
                # Top floor - ceiling to attic/roof
                adjacent = BoundaryCondition.ATTIC
                reasoning.append("Top floor ceiling to vented attic")
                confidence = 0.8
                
            elif space.floor_level < total_floors:
                # Not top floor - check what's above
                
                # Look for space directly above
                space_above = self._find_space_above(space, all_spaces)
                
                if space_above:
                    if space_above.is_conditioned:
                        adjacent = BoundaryCondition.CONDITIONED
                        reasoning.append(f"Under conditioned space: {space_above.name}")
                    else:
                        adjacent = BoundaryCondition.UNCONDITIONED
                        reasoning.append(f"Under unconditioned space: {space_above.name}")
                    confidence = 0.8
                else:
                    # Assume conditioned space above
                    adjacent = BoundaryCondition.CONDITIONED
                    reasoning.append("Ceiling to conditioned space above")
                    confidence = 0.6
            
            else:
                adjacent = BoundaryCondition.ATTIC
                reasoning.append("Unknown configuration, assuming attic above")
                confidence = 0.4
        
        # Special case: vaulted ceiling
        if space.has_cathedral_ceiling:
            adjacent = BoundaryCondition.EXTERIOR  # Direct to outdoor through roof
            reasoning.append("Vaulted/cathedral ceiling - direct to exterior")
            confidence = 0.9
        
        # Special case: open to below
        if space.open_to_below:
            return None  # No ceiling boundary
        
        # Calculate temperature difference
        winter_delta = 70 - self.ADJACENT_TEMPS['winter'][adjacent]
        
        return BoundaryAnalysis(
            space_id=space.space_id,
            surface_type='ceiling',
            adjacent_condition=adjacent,
            adjacent_space_id=None,
            temperature_difference=winter_delta,
            heat_flow_direction='out' if winter_delta > 0 else 'neutral',
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _analyze_walls(
        self,
        space: Space,
        all_spaces: List[Space],
        building_info: Dict[str, Any]
    ) -> List[BoundaryAnalysis]:
        """Analyze wall boundaries"""
        
        analyses = []
        
        # For now, simplified analysis
        # Assume perimeter walls are exterior, internal walls are adiabatic
        
        # Estimate exterior wall percentage
        if space.space_type == SpaceType.HALLWAY:
            exterior_fraction = 0.2  # Hallways have few exterior walls
        elif space.space_type in [SpaceType.BATHROOM, SpaceType.STORAGE]:
            exterior_fraction = 0.3  # Interior rooms
        else:
            exterior_fraction = 0.5  # Typical rooms have ~50% exterior
        
        # Create exterior wall analysis
        if exterior_fraction > 0:
            analyses.append(BoundaryAnalysis(
                space_id=space.space_id,
                surface_type='wall_exterior',
                adjacent_condition=BoundaryCondition.EXTERIOR,
                adjacent_space_id=None,
                temperature_difference=70,  # Winter condition
                heat_flow_direction='out',
                confidence=0.6,
                reasoning=[f"Estimated {exterior_fraction:.0%} of walls are exterior"]
            ))
        
        # Create interior wall analysis
        if exterior_fraction < 1.0:
            analyses.append(BoundaryAnalysis(
                space_id=space.space_id,
                surface_type='wall_interior',
                adjacent_condition=BoundaryCondition.ADIABATIC,
                adjacent_space_id=None,
                temperature_difference=0,
                heat_flow_direction='neutral',
                confidence=0.6,
                reasoning=[f"Estimated {1-exterior_fraction:.0%} of walls are interior"]
            ))
        
        return analyses
    
    def _find_space_below(
        self,
        space: Space,
        all_spaces: List[Space]
    ) -> Optional[Space]:
        """Find space directly below given space"""
        
        for other in all_spaces:
            if other.floor_level == space.floor_level - 1:
                # Check if areas overlap (simplified - just check names)
                if self._spaces_overlap(space, other):
                    return other
        
        return None
    
    def _find_space_above(
        self,
        space: Space,
        all_spaces: List[Space]
    ) -> Optional[Space]:
        """Find space directly above given space"""
        
        for other in all_spaces:
            if other.floor_level == space.floor_level + 1:
                # Check if areas overlap
                if self._spaces_overlap(space, other):
                    return other
        
        return None
    
    def _spaces_overlap(
        self,
        space1: Space,
        space2: Space
    ) -> bool:
        """Check if two spaces overlap vertically"""
        
        # Simplified check - would need actual geometry
        # For now, check if names suggest overlap
        
        # Bonus room over garage
        if 'BONUS' in space1.name.upper() and space2.space_type == SpaceType.GARAGE:
            return True
        if 'BONUS' in space2.name.upper() and space1.space_type == SpaceType.GARAGE:
            return True
        
        # Master over master, etc.
        if space1.name.lower() == space2.name.lower():
            return True
        
        # Bathrooms often stack
        if (space1.space_type == SpaceType.BATHROOM and 
            space2.space_type == SpaceType.BATHROOM):
            return True
        
        # Default: assume some overlap if on different floors
        return space1.floor_level != space2.floor_level
    
    def apply_boundary_conditions(
        self,
        space: Space,
        analyses: List[BoundaryAnalysis]
    ):
        """
        Apply analyzed boundary conditions to space.
        
        Args:
            space: Space to update
            analyses: Boundary analyses for this space
        """
        
        for analysis in analyses:
            if analysis.surface_type == 'floor':
                space.floor_over = analysis.adjacent_condition
                logger.debug(f"Set {space.name} floor over {analysis.adjacent_condition.value}")
                
            elif analysis.surface_type == 'ceiling':
                space.ceiling_under = analysis.adjacent_condition
                logger.debug(f"Set {space.name} ceiling under {analysis.adjacent_condition.value}")
            
            # Walls would update surface objects if we had them
    
    def calculate_boundary_loads(
        self,
        analyses: List[BoundaryAnalysis],
        areas: Dict[str, float],
        u_values: Dict[str, float],
        is_heating: bool = True
    ) -> Dict[str, float]:
        """
        Calculate heat transfer through boundaries.
        
        Args:
            analyses: Boundary analyses
            areas: Surface areas by type
            u_values: U-values by surface type
            is_heating: True for heating, False for cooling
            
        Returns:
            Dict of loads by surface type
        """
        
        loads = {}
        season = 'winter' if is_heating else 'summer'
        indoor_temp = 70 if is_heating else 75
        
        for analysis in analyses:
            surface = analysis.surface_type
            
            if surface not in areas or surface not in u_values:
                continue
            
            # Get adjacent temperature
            adjacent_temp = self.ADJACENT_TEMPS[season][analysis.adjacent_condition]
            
            # Calculate delta T
            delta_t = abs(indoor_temp - adjacent_temp)
            
            # Skip if no temperature difference
            if delta_t < 0.1:
                continue
            
            # Calculate heat transfer: Q = U × A × ΔT
            load = u_values[surface] * areas[surface] * delta_t
            
            loads[surface] = load
            
            logger.debug(f"{surface}: U={u_values[surface]:.3f} × "
                        f"A={areas[surface]:.0f} × ΔT={delta_t:.0f} = "
                        f"{load:.0f} BTU/hr")
        
        return loads


# Singleton instance
_boundary_reasoner = None


def get_boundary_reasoner() -> BoundaryReasoner:
    """Get or create the global boundary reasoner"""
    global _boundary_reasoner
    if _boundary_reasoner is None:
        _boundary_reasoner = BoundaryReasoner()
    return _boundary_reasoner