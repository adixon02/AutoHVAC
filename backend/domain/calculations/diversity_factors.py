"""
Diversity Factors for HVAC Load Calculations
Implements ACCA Manual J diversity factors for different space types and occupancy patterns
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from domain.models.spaces import SpaceType
from domain.models.zones import ZoneType

logger = logging.getLogger(__name__)


class OccupancySchedule(Enum):
    """Building occupancy schedules"""
    RESIDENTIAL = "residential"
    SLEEPING = "sleeping"
    OCCASIONAL = "occasional"
    OFFICE = "office"
    MINIMAL = "minimal"


@dataclass
class DiversityFactors:
    """Diversity factors for load calculations"""
    occupancy: float = 1.0  # People diversity
    lighting: float = 1.0   # Lighting diversity
    equipment: float = 1.0  # Equipment diversity
    ventilation: float = 1.0  # Ventilation diversity
    
    @property
    def average(self) -> float:
        """Average diversity factor"""
        return (self.occupancy + self.lighting + self.equipment) / 3


class DiversityCalculator:
    """
    Calculates diversity factors based on ACCA Manual J guidelines.
    Diversity factors account for the fact that not all loads occur simultaneously.
    """
    
    # Space type diversity factors for cooling
    SPACE_DIVERSITY = {
        SpaceType.BEDROOM: DiversityFactors(
            occupancy=0.5,    # Bedrooms empty during day
            lighting=0.2,     # Minimal lighting during day
            equipment=0.3,    # Low equipment use
            ventilation=0.7   # Reduced ventilation when unoccupied
        ),
        SpaceType.BATHROOM: DiversityFactors(
            occupancy=0.3,    # Intermittent use
            lighting=0.3,
            equipment=0.5,    # Exhaust fans intermittent
            ventilation=0.5
        ),
        SpaceType.KITCHEN: DiversityFactors(
            occupancy=0.7,    # Peak during meal times
            lighting=0.6,
            equipment=0.8,    # Appliances not all on simultaneously
            ventilation=1.0   # Full ventilation needed
        ),
        SpaceType.LIVING: DiversityFactors(
            occupancy=0.8,    # Primary occupied space
            lighting=0.7,
            equipment=0.9,    # TVs, electronics
            ventilation=1.0
        ),
        SpaceType.DINING: DiversityFactors(
            occupancy=0.5,    # Only during meals
            lighting=0.4,
            equipment=0.2,    # Minimal equipment
            ventilation=0.6
        ),
        SpaceType.HALLWAY: DiversityFactors(
            occupancy=0.1,    # Transit only
            lighting=0.3,
            equipment=0.1,
            ventilation=0.3
        ),
        SpaceType.STORAGE: DiversityFactors(
            occupancy=0.0,    # Unoccupied
            lighting=0.1,
            equipment=0.1,
            ventilation=0.2
        ),
        SpaceType.GARAGE: DiversityFactors(
            occupancy=0.0,    # Unconditioned
            lighting=0.0,
            equipment=0.0,
            ventilation=0.0
        )
    }
    
    # Zone type diversity factors
    ZONE_DIVERSITY = {
        ZoneType.MAIN_LIVING: DiversityFactors(
            occupancy=0.85,
            lighting=0.75,
            equipment=0.90,
            ventilation=1.0
        ),
        ZoneType.SLEEPING: DiversityFactors(
            occupancy=0.40,   # Low during cooling peak (afternoon)
            lighting=0.20,
            equipment=0.30,
            ventilation=0.60
        ),
        ZoneType.BONUS: DiversityFactors(
            occupancy=0.30,   # Occasional use
            lighting=0.25,
            equipment=0.40,
            ventilation=0.50
        ),
        ZoneType.GARAGE: DiversityFactors(
            occupancy=0.0,
            lighting=0.0,
            equipment=0.0,
            ventilation=0.0
        ),
        ZoneType.BASEMENT: DiversityFactors(
            occupancy=0.40,
            lighting=0.30,
            equipment=0.50,
            ventilation=0.60
        )
    }
    
    # Time-of-day factors (for future hourly calculations)
    HOURLY_FACTORS = {
        # Hour: (occupancy, lighting, equipment)
        0: (0.9, 0.1, 0.5),   # Midnight - sleeping
        1: (0.9, 0.0, 0.4),
        2: (0.9, 0.0, 0.4),
        3: (0.9, 0.0, 0.4),
        4: (0.9, 0.0, 0.4),
        5: (0.8, 0.1, 0.5),
        6: (0.7, 0.3, 0.7),   # Morning routine
        7: (0.6, 0.4, 0.8),
        8: (0.3, 0.2, 0.9),   # Work/school
        9: (0.2, 0.1, 0.9),
        10: (0.2, 0.1, 0.9),
        11: (0.2, 0.1, 0.9),
        12: (0.3, 0.2, 0.9),  # Lunch
        13: (0.2, 0.1, 0.9),
        14: (0.2, 0.1, 0.9),  # Peak cooling hour
        15: (0.3, 0.2, 0.9),
        16: (0.4, 0.3, 0.9),
        17: (0.6, 0.5, 1.0),  # Evening return
        18: (0.8, 0.7, 1.0),  # Dinner
        19: (0.9, 0.8, 1.0),
        20: (0.9, 0.9, 1.0),  # Peak occupancy
        21: (0.9, 0.8, 0.9),
        22: (0.9, 0.6, 0.7),  # Bedtime
        23: (0.9, 0.3, 0.6)
    }
    
    def get_space_diversity(
        self,
        space_type: SpaceType,
        is_heating: bool = False
    ) -> DiversityFactors:
        """
        Get diversity factors for a space type.
        
        Args:
            space_type: Type of space
            is_heating: True for heating, False for cooling
            
        Returns:
            DiversityFactors for the space
        """
        
        if is_heating:
            # Heating typically uses less diversity (worst case)
            # All spaces need to be heated simultaneously in morning
            return DiversityFactors(
                occupancy=1.0,
                lighting=0.5,   # Some lighting in morning
                equipment=0.7,  # Some equipment
                ventilation=1.0
            )
        else:
            # Cooling uses diversity factors
            return self.SPACE_DIVERSITY.get(
                space_type,
                DiversityFactors()  # Default to 1.0 all
            )
    
    def get_zone_diversity(
        self,
        zone_type: ZoneType,
        is_heating: bool = False
    ) -> DiversityFactors:
        """
        Get diversity factors for a zone type.
        
        Args:
            zone_type: Type of zone
            is_heating: True for heating, False for cooling
            
        Returns:
            DiversityFactors for the zone
        """
        
        if is_heating:
            # Less diversity for heating
            if zone_type == ZoneType.BONUS:
                # Bonus rooms might not be heated continuously
                return DiversityFactors(
                    occupancy=0.7,
                    lighting=0.3,
                    equipment=0.5,
                    ventilation=0.7
                )
            else:
                # Most zones need full heating
                return DiversityFactors(
                    occupancy=1.0,
                    lighting=0.5,
                    equipment=0.7,
                    ventilation=1.0
                )
        else:
            # Cooling uses full diversity
            return self.ZONE_DIVERSITY.get(
                zone_type,
                DiversityFactors()
            )
    
    def calculate_building_diversity(
        self,
        zone_loads: List[Dict[str, Any]],
        is_heating: bool = False
    ) -> float:
        """
        Calculate overall building diversity factor.
        
        Args:
            zone_loads: List of zone load dictionaries
            is_heating: True for heating, False for cooling
            
        Returns:
            Building-level diversity factor (0.0 to 1.0)
        """
        
        if is_heating:
            # Heating has minimal diversity
            # All zones need to be heated simultaneously on cold morning
            return 1.0
        
        # For cooling, calculate weighted diversity
        total_load = sum(z.get('cooling_load', 0) for z in zone_loads)
        if total_load == 0:
            return 1.0
        
        weighted_diversity = 0
        for zone in zone_loads:
            load = zone.get('cooling_load', 0)
            zone_type = zone.get('zone_type', ZoneType.MAIN_LIVING)
            
            # Get zone diversity
            diversity = self.get_zone_diversity(zone_type, is_heating)
            
            # Weight by load contribution
            weight = load / total_load
            weighted_diversity += diversity.average * weight
        
        # Apply minimum diversity (never less than 70% for residential)
        return max(0.7, weighted_diversity)
    
    def apply_diversity_to_loads(
        self,
        heating_load: float,
        cooling_load: float,
        building_type: str = "residential",
        has_bonus_room: bool = False
    ) -> Dict[str, float]:
        """
        Apply diversity factors to whole-building loads.
        
        Args:
            heating_load: Calculated heating load (BTU/hr)
            cooling_load: Calculated cooling load (BTU/hr)
            building_type: Type of building
            has_bonus_room: Whether building has bonus room
            
        Returns:
            Dictionary with adjusted loads
        """
        
        # Heating diversity (minimal)
        heating_diversity = 1.0  # No reduction for heating
        
        # Cooling diversity
        if building_type == "residential":
            if has_bonus_room:
                # Can reduce cooling if bonus room not primary occupied
                cooling_diversity = 0.85  # 15% reduction
                logger.info("Applying 85% diversity for cooling with bonus room")
            else:
                # Standard residential diversity
                cooling_diversity = 0.90  # 10% reduction
        else:
            cooling_diversity = 1.0  # No reduction for commercial
        
        return {
            'heating_load': heating_load * heating_diversity,
            'cooling_load': cooling_load * cooling_diversity,
            'heating_diversity': heating_diversity,
            'cooling_diversity': cooling_diversity
        }
    
    def get_hourly_factor(
        self,
        hour: int,
        factor_type: str = "occupancy"
    ) -> float:
        """
        Get hourly diversity factor.
        
        Args:
            hour: Hour of day (0-23)
            factor_type: "occupancy", "lighting", or "equipment"
            
        Returns:
            Hourly factor (0.0 to 1.0)
        """
        
        if hour not in self.HOURLY_FACTORS:
            return 1.0
        
        factors = self.HOURLY_FACTORS[hour]
        
        if factor_type == "occupancy":
            return factors[0]
        elif factor_type == "lighting":
            return factors[1]
        elif factor_type == "equipment":
            return factors[2]
        else:
            return 1.0
    
    def calculate_peak_cooling_hour(
        self,
        zone_loads: List[Dict[str, Any]]
    ) -> int:
        """
        Determine peak cooling hour based on load profiles.
        
        Args:
            zone_loads: List of zone loads
            
        Returns:
            Hour of peak cooling (typically 14-16)
        """
        
        # For residential, peak is typically 2-4 PM
        # When outdoor temp is highest and solar gain peaks
        
        # Check for west-facing zones (peak later)
        has_west_exposure = any(
            z.get('west_window_area', 0) > 0 
            for z in zone_loads
        )
        
        if has_west_exposure:
            return 16  # 4 PM for west exposure
        else:
            return 14  # 2 PM standard
    
    def get_ventilation_diversity(
        self,
        zone_type: ZoneType,
        occupancy_schedule: OccupancySchedule
    ) -> float:
        """
        Get ventilation diversity factor.
        
        Args:
            zone_type: Type of zone
            occupancy_schedule: Occupancy pattern
            
        Returns:
            Ventilation diversity factor
        """
        
        # Ventilation should track occupancy
        if occupancy_schedule == OccupancySchedule.RESIDENTIAL:
            if zone_type == ZoneType.MAIN_LIVING:
                return 1.0  # Full ventilation for main areas
            elif zone_type == ZoneType.SLEEPING:
                return 0.6  # Reduced during day
            elif zone_type == ZoneType.BONUS:
                return 0.5  # Minimal for bonus rooms
            else:
                return 0.7
        
        elif occupancy_schedule == OccupancySchedule.OCCASIONAL:
            return 0.4  # Minimal ventilation for occasional use
        
        else:
            return 1.0  # Default to full ventilation


# Singleton instance
_diversity_calculator = None


def get_diversity_calculator() -> DiversityCalculator:
    """Get or create the global diversity calculator"""
    global _diversity_calculator
    if _diversity_calculator is None:
        _diversity_calculator = DiversityCalculator()
    return _diversity_calculator