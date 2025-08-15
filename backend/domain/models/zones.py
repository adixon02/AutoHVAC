"""
Thermal Zone Models for HVAC Load Calculations
Groups spaces that share similar thermal characteristics and HVAC control
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from domain.models.spaces import Space, SpaceType, BoundaryCondition


class ZoneType(Enum):
    """Types of thermal zones"""
    MAIN_LIVING = "main_living"  # Primary occupied areas
    SLEEPING = "sleeping"  # Bedrooms
    BONUS = "bonus"  # Bonus rooms over garage
    GARAGE = "garage"  # Unconditioned garage
    BASEMENT = "basement"  # Basement zones
    ATTIC = "attic"  # Unconditioned attic


@dataclass
class ThermalZone:
    """
    A thermal zone is a collection of spaces that:
    1. Share the same temperature setpoint
    2. Are served by the same HVAC equipment
    3. Have similar occupancy schedules
    """
    zone_id: str
    name: str
    zone_type: ZoneType
    floor_level: int
    
    # Spaces in this zone
    spaces: List[Space] = field(default_factory=list)
    
    # HVAC control
    is_conditioned: bool = True
    heating_setpoint_f: float = 70.0
    cooling_setpoint_f: float = 75.0
    has_separate_control: bool = False  # Separate thermostat?
    
    # Occupancy schedule
    occupancy_schedule: str = "residential"  # or "sleeping", "occasional"
    primary_occupancy: bool = True  # Primary living space?
    
    # Special characteristics
    is_bonus_zone: bool = False
    requires_zoning: bool = False
    
    @property
    def total_area_sqft(self) -> float:
        """Total floor area of all spaces in zone"""
        return sum(space.area_sqft for space in self.spaces)
    
    @property
    def total_volume_cuft(self) -> float:
        """Total volume of all spaces in zone"""
        return sum(space.volume_cuft for space in self.spaces)
    
    @property
    def has_garage_below(self) -> bool:
        """Check if any space in zone is over garage"""
        return any(space.is_over_garage for space in self.spaces)
    
    @property
    def exterior_wall_area(self) -> float:
        """Total exterior wall area in zone"""
        return sum(space.exterior_wall_area for space in self.spaces)
    
    def get_infiltration_modifier(self, is_heating: bool) -> float:
        """
        Get infiltration modifier for this zone.
        Upper zones have more infiltration in heating (stack effect).
        """
        if is_heating:
            if self.floor_level > 1:
                if self.is_bonus_zone:
                    return 1.4  # 40% more infiltration for bonus rooms
                return 1.2  # 20% more for upper floors
        else:
            # Cooling: less stack effect
            if self.floor_level > 1:
                return 1.1
        return 1.0
    
    def get_internal_gains_schedule(self, hour: int) -> Dict[str, float]:
        """
        Get internal gains multiplier by hour of day.
        Different zones have different occupancy patterns.
        """
        if self.zone_type == ZoneType.MAIN_LIVING:
            # Living areas: high during day and evening
            if 7 <= hour <= 22:
                return {"occupancy": 0.8, "lighting": 0.6, "equipment": 0.9}
            else:
                return {"occupancy": 0.1, "lighting": 0.1, "equipment": 0.5}
        
        elif self.zone_type == ZoneType.SLEEPING:
            # Bedrooms: high at night
            if 22 <= hour or hour <= 7:
                return {"occupancy": 1.0, "lighting": 0.2, "equipment": 0.3}
            else:
                return {"occupancy": 0.0, "lighting": 0.0, "equipment": 0.2}
        
        elif self.zone_type == ZoneType.BONUS:
            # Bonus rooms: occasional use
            if 19 <= hour <= 22:
                return {"occupancy": 0.5, "lighting": 0.4, "equipment": 0.4}
            else:
                return {"occupancy": 0.0, "lighting": 0.0, "equipment": 0.1}
        
        else:
            # Unconditioned zones
            return {"occupancy": 0.0, "lighting": 0.0, "equipment": 0.0}


@dataclass
class BuildingThermalModel:
    """
    Complete thermal model of the building with all zones
    """
    building_id: str
    total_conditioned_area_sqft: float
    total_floors: int
    
    # All zones
    zones: List[ThermalZone] = field(default_factory=list)
    
    # Building characteristics
    foundation_type: str = "crawlspace"  # slab, crawlspace, basement
    has_bonus_over_garage: bool = False
    has_vaulted_spaces: bool = False
    
    # Climate data
    climate_zone: str = ""
    winter_design_temp: float = 0
    summer_design_temp: float = 95
    
    @property
    def conditioned_zones(self) -> List[ThermalZone]:
        """Get only conditioned zones"""
        return [z for z in self.zones if z.is_conditioned]
    
    @property
    def primary_zones(self) -> List[ThermalZone]:
        """Get primary occupancy zones for cooling scenarios"""
        return [z for z in self.zones if z.primary_occupancy]
    
    @property
    def bonus_zones(self) -> List[ThermalZone]:
        """Get bonus zones that may need special handling"""
        return [z for z in self.zones if z.is_bonus_zone]
    
    def get_heating_zones(self) -> List[ThermalZone]:
        """All zones that need heating (all conditioned)"""
        return self.conditioned_zones
    
    def get_cooling_zones(self, scenario: str = "whole_house") -> List[ThermalZone]:
        """
        Get zones for cooling based on scenario.
        
        Args:
            scenario: "whole_house" or "primary_occupancy"
        """
        if scenario == "primary_occupancy":
            # Only primary zones for cooling
            return self.primary_zones
        else:
            # All conditioned zones
            return self.conditioned_zones
    
    def validate_model(self) -> Tuple[bool, List[str]]:
        """
        Validate the thermal model for consistency.
        Returns (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for orphaned spaces
        all_spaces = []
        for zone in self.zones:
            all_spaces.extend(zone.spaces)
        
        if not all_spaces:
            issues.append("No spaces defined in any zone")
        
        # Check area consistency
        total_zone_area = sum(z.total_area_sqft for z in self.conditioned_zones)
        if abs(total_zone_area - self.total_conditioned_area_sqft) > 10:
            issues.append(f"Zone areas ({total_zone_area:.0f}) don't match total ({self.total_conditioned_area_sqft:.0f})")
        
        # Check for bonus room configuration
        if self.has_bonus_over_garage:
            if not self.bonus_zones:
                issues.append("Building has bonus over garage but no bonus zones defined")
        
        # Check for reasonable zone sizes
        for zone in self.zones:
            if zone.is_conditioned and zone.total_area_sqft < 50:
                issues.append(f"Zone {zone.name} seems too small ({zone.total_area_sqft:.0f} sqft)")
        
        return len(issues) == 0, issues