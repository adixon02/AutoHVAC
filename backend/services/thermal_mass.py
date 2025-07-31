"""
Thermal Mass Calculations for ACCA Manual J
Implements thermal lag and damping effects for high-mass construction
"""

import math
from typing import Dict, Tuple, Optional
from enum import Enum


class MassLevel(Enum):
    """Building mass levels per ACCA Manual J"""
    LIGHT = "light"      # Wood frame, minimal mass
    MEDIUM = "medium"    # Standard construction
    HEAVY = "heavy"      # Concrete/masonry walls or floors


def classify_thermal_mass(wall_type: str, floor_type: str, 
                         exposed_slab: bool = False,
                         interior_mass_walls: Optional[str] = None) -> MassLevel:
    """
    Classify building thermal mass level based on construction
    
    Args:
        wall_type: Wall construction type
        floor_type: Floor construction type  
        exposed_slab: Whether slab is exposed to interior
        interior_mass_walls: Interior mass wall type if any
        
    Returns:
        MassLevel classification
    """
    mass_score = 0
    
    # Wall mass contribution
    if any(mass in wall_type.lower() for mass in ["concrete", "masonry", "icf", "brick", "block"]):
        mass_score += 3
    elif "sip" in wall_type.lower():
        mass_score += 1
    
    # Floor mass contribution
    if "slab" in floor_type.lower() and exposed_slab:
        mass_score += 2
    elif "concrete" in floor_type.lower():
        mass_score += 1
    
    # Interior mass walls
    if interior_mass_walls and any(mass in interior_mass_walls.lower() 
                                  for mass in ["concrete", "brick", "masonry"]):
        mass_score += 2
    
    # Classify based on total score
    if mass_score >= 4:
        return MassLevel.HEAVY
    elif mass_score >= 2:
        return MassLevel.MEDIUM
    else:
        return MassLevel.LIGHT


def calculate_mass_factor(mass_level: MassLevel, load_type: str = "cooling") -> float:
    """
    Calculate thermal mass factor for load adjustment
    
    Thermal mass reduces peak cooling loads and can slightly increase heating loads
    
    Args:
        mass_level: Building mass classification
        load_type: "cooling" or "heating"
        
    Returns:
        Mass factor multiplier (typically 0.85-1.0 for cooling)
    """
    if load_type == "cooling":
        # Mass reduces cooling loads by damping temperature swings
        mass_factors = {
            MassLevel.LIGHT: 1.0,   # No reduction
            MassLevel.MEDIUM: 0.95, # 5% reduction
            MassLevel.HEAVY: 0.90   # 10% reduction
        }
    else:  # heating
        # Mass can slightly increase heating loads (slower warmup)
        mass_factors = {
            MassLevel.LIGHT: 1.0,   # No change
            MassLevel.MEDIUM: 1.02, # 2% increase
            MassLevel.HEAVY: 1.05   # 5% increase
        }
    
    return mass_factors.get(mass_level, 1.0)


def calculate_time_lag(mass_level: MassLevel, wall_thickness: float = 8.0) -> float:
    """
    Calculate thermal lag in hours for peak load timing
    
    Args:
        mass_level: Building mass classification
        wall_thickness: Wall thickness in inches
        
    Returns:
        Time lag in hours
    """
    # Simplified thermal diffusivity-based lag calculation
    # Light frame: ~1-2 hours, Heavy mass: ~4-8 hours
    
    base_lag = {
        MassLevel.LIGHT: 1.0,
        MassLevel.MEDIUM: 2.5,
        MassLevel.HEAVY: 4.0
    }
    
    # Adjust for wall thickness
    thickness_factor = math.sqrt(wall_thickness / 8.0)
    
    return base_lag.get(mass_level, 1.0) * thickness_factor


def adjust_peak_hour(standard_peak: int, mass_level: MassLevel, 
                    orientation: str = "S") -> int:
    """
    Adjust peak cooling hour based on thermal mass
    
    Args:
        standard_peak: Standard peak hour (typically 14-16)
        mass_level: Building mass classification
        orientation: Primary glazing orientation
        
    Returns:
        Adjusted peak hour (0-23)
    """
    # Get time lag
    lag = calculate_time_lag(mass_level)
    
    # Orientation adjustments (east peaks earlier, west later)
    orientation_shift = {
        "E": -2, "SE": -1, "S": 0, "SW": 1, "W": 2,
        "NE": -1, "N": 0, "NW": 1
    }
    
    # Calculate adjusted peak
    adjusted = standard_peak + lag + orientation_shift.get(orientation, 0)
    
    # Constrain to valid hours
    return int(max(12, min(20, adjusted)))


def calculate_decrement_factor(mass_level: MassLevel, u_factor: float) -> float:
    """
    Calculate decrement factor for temperature amplitude reduction
    
    Thermal mass dampens the amplitude of temperature swings
    
    Args:
        mass_level: Building mass classification
        u_factor: Wall U-factor
        
    Returns:
        Decrement factor (0.0-1.0)
    """
    # Base decrement by mass level
    base_decrement = {
        MassLevel.LIGHT: 0.95,   # 5% amplitude reduction
        MassLevel.MEDIUM: 0.85,  # 15% amplitude reduction  
        MassLevel.HEAVY: 0.70    # 30% amplitude reduction
    }
    
    # Adjust for insulation level (lower U = better insulation = more damping)
    insulation_factor = 1.0 - min(0.2, u_factor * 0.5)
    
    return base_decrement.get(mass_level, 0.95) * insulation_factor


def apply_thermal_mass_to_loads(
    sensible_cooling: float,
    sensible_heating: float,
    mass_level: MassLevel,
    room_type: str = "living"
) -> Tuple[float, float]:
    """
    Apply thermal mass effects to room loads
    
    Args:
        sensible_cooling: Original sensible cooling load (BTU/hr)
        sensible_heating: Original sensible heating load (BTU/hr)
        mass_level: Building mass classification
        room_type: Type of room (affects mass impact)
        
    Returns:
        Tuple of (adjusted_cooling, adjusted_heating)
    """
    # Room type factors (some rooms benefit more from mass)
    room_factors = {
        "living": 1.0,     # Full mass benefit
        "bedroom": 0.8,    # Less benefit (night use)
        "kitchen": 0.6,    # High internal gains reduce benefit
        "bathroom": 0.5,   # Minimal benefit
        "office": 0.9,     # Good benefit
        "dining": 1.0,     # Full benefit
        "other": 0.7
    }
    
    room_factor = room_factors.get(room_type, 0.7)
    
    # Get base mass factors
    cooling_factor = calculate_mass_factor(mass_level, "cooling")
    heating_factor = calculate_mass_factor(mass_level, "heating")
    
    # Apply room-adjusted factors
    effective_cooling_factor = 1.0 - (1.0 - cooling_factor) * room_factor
    effective_heating_factor = 1.0 + (heating_factor - 1.0) * room_factor
    
    # Calculate adjusted loads
    adjusted_cooling = sensible_cooling * effective_cooling_factor
    adjusted_heating = sensible_heating * effective_heating_factor
    
    return adjusted_cooling, adjusted_heating


def estimate_flywheel_effect(
    mass_level: MassLevel,
    daily_temp_range: float,
    glazing_ratio: float = 0.15
) -> Dict[str, float]:
    """
    Estimate thermal flywheel effect for passive solar benefit
    
    Args:
        mass_level: Building mass classification
        daily_temp_range: Daily temperature swing (°F)
        glazing_ratio: Window area / floor area ratio
        
    Returns:
        Dict with flywheel metrics
    """
    # Mass effectiveness at storing/releasing heat
    effectiveness = {
        MassLevel.LIGHT: 0.2,
        MassLevel.MEDIUM: 0.5,
        MassLevel.HEAVY: 0.8
    }
    
    mass_effectiveness = effectiveness.get(mass_level, 0.2)
    
    # Temperature damping
    interior_swing = daily_temp_range * (1 - mass_effectiveness * 0.7)
    
    # Passive solar utilization (higher mass = better solar storage)
    solar_fraction = min(0.3, glazing_ratio * mass_effectiveness * 2)
    
    return {
        "interior_temp_swing": interior_swing,
        "exterior_temp_swing": daily_temp_range,
        "damping_ratio": interior_swing / daily_temp_range,
        "passive_solar_fraction": solar_fraction,
        "thermal_lag_hours": calculate_time_lag(mass_level)
    }