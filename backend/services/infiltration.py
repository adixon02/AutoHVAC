"""
Infiltration and Air Leakage Calculations for ACCA Manual J
Implements blower door test conversions and natural infiltration estimates
"""

import math
from typing import Dict, Tuple, Optional
from enum import Enum


class InfiltrationMethod(Enum):
    """Methods for determining infiltration rates"""
    BLOWER_DOOR_CFM50 = "blower_door_cfm50"
    BLOWER_DOOR_ACH50 = "blower_door_ach50"
    CONSTRUCTION_QUALITY = "construction_quality"
    IECC_CODE = "iecc_code"


class ConstructionQuality(Enum):
    """Construction quality levels for infiltration estimates"""
    VERY_TIGHT = "very_tight"  # High-performance, verified air sealing
    TIGHT = "tight"            # Good air sealing, Energy Star level
    AVERAGE = "average"        # Standard construction, code minimum
    LOOSE = "loose"            # Older construction, visible gaps
    VERY_LOOSE = "very_loose"  # Poor construction, major air leaks


def convert_cfm50_to_natural(cfm50: float, climate_zone: str, stories: int = 1,
                            shielding: str = "average") -> float:
    """
    Convert blower door CFM50 to natural infiltration CFM
    
    Uses LBL/ASHRAE correlation: CFM_natural = CFM50 / N
    where N is climate/building specific factor
    
    Args:
        cfm50: Blower door test result at 50 Pa
        climate_zone: IECC climate zone (e.g., "3A", "5B")
        stories: Number of stories in building
        shielding: Wind shielding ("exposed", "average", "well_shielded")
        
    Returns:
        Natural infiltration rate in CFM
    """
    # Extract numeric zone (1-8) from climate zone string
    zone_num = int(climate_zone[0]) if climate_zone and climate_zone[0].isdigit() else 4
    
    # LBL N-factors by climate zone (simplified from ASHRAE Fundamentals)
    # Lower N = more infiltration (windier/colder climates)
    n_factors = {
        1: 35,  # Very hot, minimal heating
        2: 30,  # Hot, minimal heating
        3: 25,  # Warm, moderate heating/cooling
        4: 20,  # Mixed, balanced heating/cooling
        5: 18,  # Cool, heating dominated
        6: 16,  # Cold, significant heating
        7: 14,  # Very cold, extreme heating
        8: 12   # Subarctic, extreme conditions
    }
    
    # Get base N-factor
    n_factor = n_factors.get(zone_num, 20)
    
    # Adjust for building height (taller = more stack effect)
    if stories >= 3:
        n_factor *= 0.9
    elif stories == 2:
        n_factor *= 0.95
    
    # Adjust for shielding
    shielding_factors = {
        "exposed": 0.9,      # Open terrain, no windbreaks
        "average": 1.0,      # Suburban, some trees/buildings
        "well_shielded": 1.1 # Urban, dense trees/buildings
    }
    n_factor *= shielding_factors.get(shielding, 1.0)
    
    # Convert to natural CFM
    cfm_natural = cfm50 / n_factor
    
    return cfm_natural


def convert_ach50_to_cfm50(ach50: float, volume: float) -> float:
    """
    Convert ACH50 (air changes per hour at 50 Pa) to CFM50
    
    Args:
        ach50: Air changes per hour at 50 Pa
        volume: Building/zone volume in cubic feet
        
    Returns:
        CFM at 50 Pa
    """
    return ach50 * volume / 60.0


def convert_ach_natural_to_cfm(ach_natural: float, volume: float) -> float:
    """
    Convert natural ACH to CFM
    
    Args:
        ach_natural: Natural air changes per hour
        volume: Building/zone volume in cubic feet
        
    Returns:
        Natural infiltration CFM
    """
    return ach_natural * volume / 60.0


def estimate_infiltration_by_quality(quality: ConstructionQuality, volume: float,
                                   climate_zone: str) -> Tuple[float, float]:
    """
    Estimate infiltration based on construction quality
    
    Args:
        quality: Construction quality level
        volume: Building/zone volume in cubic feet
        climate_zone: IECC climate zone
        
    Returns:
        Tuple of (cfm_natural, ach_natural)
    """
    # Typical ACH natural by construction quality
    # Based on ASHRAE Fundamentals and field studies
    ach_natural_ranges = {
        ConstructionQuality.VERY_TIGHT: (0.1, 0.2),   # Passive house level
        ConstructionQuality.TIGHT: (0.2, 0.35),       # Energy Star level
        ConstructionQuality.AVERAGE: (0.35, 0.5),     # Current code
        ConstructionQuality.LOOSE: (0.5, 0.8),        # Older homes
        ConstructionQuality.VERY_LOOSE: (0.8, 1.5)    # Poor construction
    }
    
    # Get range for quality level
    ach_min, ach_max = ach_natural_ranges.get(quality, (0.35, 0.5))
    
    # Use middle of range, adjusted for climate
    zone_num = int(climate_zone[0]) if climate_zone and climate_zone[0].isdigit() else 4
    
    # Colder climates tend to have tighter construction
    climate_factor = 1.0 + (zone_num - 4) * 0.05
    ach_natural = (ach_min + ach_max) / 2 * climate_factor
    
    # Clamp to reasonable range
    ach_natural = max(0.1, min(1.5, ach_natural))
    
    # Convert to CFM
    cfm_natural = convert_ach_natural_to_cfm(ach_natural, volume)
    
    return cfm_natural, ach_natural


def calculate_infiltration_loads(cfm: float, outdoor_temp: float, indoor_temp: float,
                               outdoor_humidity_ratio: float = 0.008,
                               indoor_humidity_ratio: float = 0.009) -> Dict[str, float]:
    """
    Calculate sensible and latent infiltration loads
    
    Args:
        cfm: Infiltration rate in CFM
        outdoor_temp: Outdoor temperature (°F)
        indoor_temp: Indoor temperature (°F)
        outdoor_humidity_ratio: Outdoor humidity ratio (lb water/lb dry air)
        indoor_humidity_ratio: Indoor humidity ratio (lb water/lb dry air)
        
    Returns:
        Dict with sensible and latent loads in BTU/hr
    """
    # Sensible load: Q_sensible = 1.08 × CFM × ΔT
    sensible_load = 1.08 * cfm * abs(outdoor_temp - indoor_temp)
    
    # Latent load: Q_latent = 4840 × CFM × ΔW (for cooling)
    # Only calculate latent for cooling (when outdoor humidity > indoor)
    if outdoor_humidity_ratio > indoor_humidity_ratio:
        delta_w = outdoor_humidity_ratio - indoor_humidity_ratio
        latent_load = 4840 * cfm * delta_w
    else:
        latent_load = 0.0
    
    return {
        "sensible": sensible_load,
        "latent": latent_load,
        "total": sensible_load + latent_load
    }


def get_iecc_infiltration_requirements(climate_zone: str, year: int = 2021) -> Dict[str, float]:
    """
    Get IECC code requirements for infiltration
    
    Args:
        climate_zone: IECC climate zone
        year: IECC code year (2012, 2015, 2018, 2021)
        
    Returns:
        Dict with ACH50 requirements
    """
    # IECC infiltration requirements (ACH50)
    iecc_requirements = {
        2012: 5.0,  # 2012 IECC
        2015: 5.0,  # 2015 IECC (most zones)
        2018: 3.0,  # 2018 IECC
        2021: 3.0   # 2021 IECC
    }
    
    max_ach50 = iecc_requirements.get(year, 3.0)
    
    # Climate zones 3-8 have same requirement in recent codes
    # Zones 1-2 sometimes have relaxed requirements
    zone_num = int(climate_zone[0]) if climate_zone and climate_zone[0].isdigit() else 4
    if zone_num <= 2 and year <= 2015:
        max_ach50 = 5.0
    
    return {
        "max_ach50": max_ach50,
        "code_year": year,
        "climate_zone": climate_zone
    }


def calculate_mechanical_ventilation_rate(floor_area: float, bedrooms: int,
                                        occupants: Optional[int] = None) -> float:
    """
    Calculate required mechanical ventilation per ASHRAE 62.2
    
    Formula: CFM = 0.03 × floor_area + 7.5 × (bedrooms + 1)
    
    Args:
        floor_area: Conditioned floor area in sq ft
        bedrooms: Number of bedrooms
        occupants: Optional actual occupant count (overrides bedroom calc)
        
    Returns:
        Required ventilation rate in CFM
    """
    if occupants is not None:
        # Use actual occupancy if known
        people = occupants
    else:
        # Assume occupancy = bedrooms + 1
        people = bedrooms + 1
    
    # ASHRAE 62.2 formula
    cfm_required = 0.03 * floor_area + 7.5 * people
    
    return cfm_required


def calculate_balanced_ventilation_load(cfm: float, outdoor_temp: float, 
                                       indoor_temp: float, recovery_efficiency: float = 0.0,
                                       outdoor_humidity_ratio: float = 0.008,
                                       indoor_humidity_ratio: float = 0.009) -> Dict[str, float]:
    """
    Calculate load from balanced mechanical ventilation (HRV/ERV)
    
    Args:
        cfm: Ventilation rate in CFM
        outdoor_temp: Outdoor temperature (°F)
        indoor_temp: Indoor temperature (°F)
        recovery_efficiency: Heat/energy recovery efficiency (0.0-1.0)
        outdoor_humidity_ratio: Outdoor humidity ratio
        indoor_humidity_ratio: Indoor humidity ratio
        
    Returns:
        Dict with sensible and latent loads in BTU/hr
    """
    # Temperature after recovery
    if recovery_efficiency > 0:
        effective_outdoor_temp = indoor_temp + (outdoor_temp - indoor_temp) * (1 - recovery_efficiency)
        # ERV also recovers some moisture
        effective_outdoor_humidity = indoor_humidity_ratio + \
            (outdoor_humidity_ratio - indoor_humidity_ratio) * (1 - recovery_efficiency * 0.5)
    else:
        effective_outdoor_temp = outdoor_temp
        effective_outdoor_humidity = outdoor_humidity_ratio
    
    # Calculate loads with effective conditions
    return calculate_infiltration_loads(
        cfm, effective_outdoor_temp, indoor_temp,
        effective_outdoor_humidity, indoor_humidity_ratio
    )