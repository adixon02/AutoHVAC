"""
Parallel Path U-Value Calculator
Implements proper ASHRAE parallel-path calculations for framed assemblies
CRITICAL: The critique specifically requires this for accurate wall U-values
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FramedWallAssembly:
    """Properties of a framed wall assembly"""
    cavity_r_value: float  # R-value of insulation in cavity
    framing_r_value: float  # R-value of framing member (wood/steel)
    framing_fraction: float  # Fraction of wall that is framing (typically 0.15-0.25)
    interior_film_r: float = 0.68  # Interior air film
    exterior_film_r: float = 0.17  # Exterior air film
    sheathing_r: float = 0.5  # Typical OSB sheathing
    siding_r: float = 0.5  # Typical vinyl siding
    drywall_r: float = 0.45  # 1/2" drywall


class ParallelPathCalculator:
    """
    Calculates effective U-values for framed assemblies using parallel path method
    This is REQUIRED by Manual J for accurate load calculations
    """
    
    # REDLINE FIX: Correct framing fractions per critique
    FRAMING_FRACTIONS = {
        '16oc_2x4': 0.23,  # 16" o.c. walls per critique
        '24oc_2x4': 0.18,  # 24" o.c. walls per critique
        '16oc_2x6': 0.23,  # 16" o.c. 2x6 wall
        '24oc_2x6': 0.18,  # 24" o.c. 2x6 wall
        'advanced': 0.10,  # Advanced framing
        'steel': 0.25,  # Steel framing (higher due to thermal bridging)
        'rim_joist': 0.30,  # Rim joist band - higher framing fraction
    }
    
    # Framing member R-values
    FRAMING_R_VALUES = {
        'wood_2x4': 4.38,  # 3.5" wood at R-1.25/inch
        'wood_2x6': 6.88,  # 5.5" wood at R-1.25/inch
        'steel_2x4': 0.5,  # Steel has very low R-value
        'steel_2x6': 0.5,  # Steel thermal bridge
    }
    
    def calculate_wall_u_value(
        self,
        nominal_r_value: float,
        framing_type: str = '16oc_2x4',
        is_steel: bool = False
    ) -> float:
        """
        Calculate effective U-value for a framed wall assembly
        
        Args:
            nominal_r_value: Nominal R-value of cavity insulation (e.g., R-13, R-19)
            framing_type: Type of framing configuration
            is_steel: True for steel framing, False for wood
            
        Returns:
            Effective U-value accounting for thermal bridging
        """
        logger.info(f"Calculating parallel-path U-value for R-{nominal_r_value} wall")
        
        # Get framing fraction
        framing_fraction = self.FRAMING_FRACTIONS.get(framing_type, 0.15)
        
        # Get framing R-value
        if is_steel:
            if '2x6' in framing_type:
                framing_r = self.FRAMING_R_VALUES['steel_2x6']
            else:
                framing_r = self.FRAMING_R_VALUES['steel_2x4']
        else:
            if '2x6' in framing_type:
                framing_r = self.FRAMING_R_VALUES['wood_2x6']
            else:
                framing_r = self.FRAMING_R_VALUES['wood_2x4']
        
        # Create wall assembly
        wall = FramedWallAssembly(
            cavity_r_value=nominal_r_value,
            framing_r_value=framing_r,
            framing_fraction=framing_fraction
        )
        
        # Calculate parallel path R-value
        effective_r = self._calculate_parallel_path_r(wall)
        
        # Convert to U-value
        u_value = 1.0 / effective_r
        
        # Log the impact of thermal bridging
        simple_r = nominal_r_value + wall.interior_film_r + wall.exterior_film_r + \
                   wall.sheathing_r + wall.siding_r + wall.drywall_r
        simple_u = 1.0 / simple_r
        
        degradation = (u_value - simple_u) / simple_u * 100
        
        logger.info(f"  Nominal assembly: R-{simple_r:.1f} (U-{simple_u:.3f})")
        logger.info(f"  Effective w/framing: R-{effective_r:.1f} (U-{u_value:.3f})")
        logger.info(f"  Thermal bridging impact: {degradation:.1f}% increase in U-value")
        
        return u_value
    
    def _calculate_parallel_path_r(self, wall: FramedWallAssembly) -> float:
        """
        Calculate effective R-value using parallel path method
        REDLINE FIX: Films must be in BOTH paths per critique
        """
        # CRITICAL: Air films are part of BOTH paths
        # Path through cavity (insulation)
        r_cavity_path = (
            wall.interior_film_r +  # Interior air film
            wall.drywall_r +        # Drywall
            wall.cavity_r_value +   # Cavity insulation
            wall.sheathing_r +      # Sheathing
            wall.siding_r +         # Siding
            wall.exterior_film_r    # Exterior air film
        )
        
        # Path through framing
        r_framing_path = (
            wall.interior_film_r +   # Interior air film (same)
            wall.drywall_r +         # Drywall (same)
            wall.framing_r_value +   # Framing member instead of insulation
            wall.sheathing_r +       # Sheathing (same)
            wall.siding_r +          # Siding (same)
            wall.exterior_film_r     # Exterior air film (same)
        )
        
        # Calculate U-values for each path
        u_cavity = 1.0 / r_cavity_path
        u_framing = 1.0 / r_framing_path
        
        # Area-weighted average U-value
        cavity_fraction = 1.0 - wall.framing_fraction
        u_effective = (cavity_fraction * u_cavity) + (wall.framing_fraction * u_framing)
        
        # Convert back to R-value
        r_effective = 1.0 / u_effective
        
        logger.debug(f"  Cavity path: R-{r_cavity_path:.2f} ({cavity_fraction:.1%} of area)")
        logger.debug(f"  Framing path: R-{r_framing_path:.2f} ({wall.framing_fraction:.1%} of area)")
        logger.debug(f"  Effective R-value: {r_effective:.2f}")
        
        return r_effective
    
    def calculate_ceiling_u_value(
        self,
        nominal_r_value: float,
        joist_spacing: str = '24oc',
        joist_depth: int = 10
    ) -> float:
        """
        Calculate effective U-value for ceiling/roof assembly
        
        Args:
            nominal_r_value: Nominal R-value of insulation (e.g., R-38, R-49)
            joist_spacing: Joist spacing (16oc or 24oc)
            joist_depth: Depth of joists in inches
            
        Returns:
            Effective U-value
        """
        # Framing fraction for ceiling joists
        if joist_spacing == '16oc':
            framing_fraction = 0.07  # Less framing in ceilings
        else:
            framing_fraction = 0.05
        
        # Joist R-value (wood)
        joist_r = joist_depth * 1.25  # R-1.25 per inch for wood
        
        # Interior and exterior films
        interior_film = 0.61  # Ceiling, heat flow up
        exterior_film = 0.61  # Attic space
        
        # Path through insulation
        r_cavity = interior_film + nominal_r_value + exterior_film
        
        # Path through joists
        r_framing = interior_film + joist_r + exterior_film
        
        # Calculate effective U-value
        u_cavity = 1.0 / r_cavity
        u_framing = 1.0 / r_framing
        
        u_effective = ((1 - framing_fraction) * u_cavity) + (framing_fraction * u_framing)
        
        logger.debug(f"Ceiling U-value: {u_effective:.3f} (R-{1/u_effective:.1f} effective)")
        
        return u_effective
    
    def calculate_floor_u_value(
        self,
        nominal_r_value: float,
        joist_spacing: str = '16oc',
        over_unconditioned: bool = True
    ) -> float:
        """
        Calculate effective U-value for floor assembly
        
        Args:
            nominal_r_value: Nominal R-value of insulation
            joist_spacing: Joist spacing
            over_unconditioned: True if over crawlspace/unconditioned
            
        Returns:
            Effective U-value
        """
        # Framing fraction for floor joists
        if joist_spacing == '16oc':
            framing_fraction = 0.10
        else:
            framing_fraction = 0.07
        
        # Joist R-value (2x10 typical)
        joist_r = 10 * 1.25  # R-1.25 per inch
        
        # Films depend on location
        if over_unconditioned:
            interior_film = 0.92  # Floor, heat flow down
            exterior_film = 0.92  # Still air in crawl
        else:
            interior_film = 0.92
            exterior_film = 0.25  # Moving air
        
        # Add floor covering (carpet, wood, etc.)
        floor_covering = 1.23  # Carpet and pad
        subfloor = 0.94  # 3/4" plywood
        
        # Path through insulation
        r_cavity = interior_film + floor_covering + subfloor + nominal_r_value + exterior_film
        
        # Path through joists
        r_framing = interior_film + floor_covering + subfloor + joist_r + exterior_film
        
        # Calculate effective U-value
        u_cavity = 1.0 / r_cavity
        u_framing = 1.0 / r_framing
        
        u_effective = ((1 - framing_fraction) * u_cavity) + (framing_fraction * u_framing)
        
        logger.debug(f"Floor U-value: {u_effective:.3f} (R-{1/u_effective:.1f} effective)")
        
        return u_effective


# Singleton instance
_calculator = None


def get_parallel_path_calculator() -> ParallelPathCalculator:
    """Get or create the global calculator"""
    global _calculator
    if _calculator is None:
        _calculator = ParallelPathCalculator()
    return _calculator