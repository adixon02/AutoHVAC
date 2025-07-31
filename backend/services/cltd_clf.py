"""
CLTD/CLF Load Calculation Methods for ACCA Manual J
Implements proper cooling load factor and cooling load temperature difference calculations
"""

import math
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime

# Cooling Load Temperature Differences (CLTD) for different wall types
# Based on ASHRAE fundamentals - simplified for common construction types
# Using NumPy arrays for vectorized calculations
WALL_CLTD_DATA = {
    # Wall type: [CLTD values by hour 0-23] for east-facing wall
    'frame_light': np.array([5, 4, 3, 3, 4, 7, 12, 18, 22, 24, 25, 24, 22, 19, 16, 13, 11, 9, 8, 7, 6, 6, 5, 5]),
    'frame_medium': np.array([4, 3, 2, 2, 3, 5, 9, 14, 18, 21, 22, 22, 21, 19, 17, 14, 12, 10, 8, 7, 6, 5, 5, 4]),
    'frame_heavy': np.array([3, 2, 1, 1, 2, 3, 6, 10, 14, 17, 19, 20, 20, 19, 18, 16, 14, 12, 10, 8, 6, 5, 4, 3]),
    'masonry_light': np.array([6, 5, 4, 4, 5, 8, 13, 19, 24, 27, 28, 27, 25, 22, 18, 15, 12, 10, 9, 8, 7, 7, 6, 6]),
    'masonry_heavy': np.array([4, 3, 2, 2, 3, 4, 7, 12, 16, 20, 22, 23, 23, 22, 20, 18, 15, 13, 11, 9, 7, 6, 5, 4]),
    'masonry_medium': np.array([5, 4, 3, 3, 4, 6, 10, 15, 20, 23, 25, 25, 24, 21, 19, 16, 13, 11, 10, 8, 7, 6, 5, 5])
}

# Roof CLTD values - simplified for common roof types
ROOF_CLTD_DATA = {
    'light_roof': np.array([8, 6, 5, 4, 4, 6, 10, 16, 23, 30, 36, 40, 42, 42, 40, 36, 31, 25, 19, 15, 12, 10, 9, 8]),
    'medium_roof': np.array([6, 4, 3, 2, 2, 4, 7, 12, 18, 24, 29, 33, 35, 36, 35, 32, 28, 23, 18, 14, 11, 9, 8, 7]),
    'heavy_roof': np.array([4, 3, 2, 1, 1, 2, 4, 8, 13, 18, 23, 27, 30, 31, 31, 29, 26, 22, 17, 13, 10, 8, 6, 5])
}

# Cooling Load Factors (CLF) for internal gains
INTERNAL_CLF_DATA = {
    # CLF values by hour for different internal heat sources
    'people': np.array([0.49, 0.52, 0.55, 0.58, 0.61, 0.64, 0.67, 0.70, 0.73, 0.76, 0.78, 0.80, 0.82, 0.83, 0.84, 0.84, 0.84, 0.83, 0.82, 0.80, 0.78, 0.75, 0.71, 0.67]),
    'lighting': np.ones(24),  # Simplified - assume instant effect
    'equipment': np.array([0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.7, 0.8, 0.9, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.6, 0.6, 0.6, 0.6])
}

# Solar Heat Gain Factors (SHGF) for different orientations and latitudes
# Simplified for common US latitudes (32-48°N) in BTU/hr/ft²
SOLAR_HEAT_GAIN_FACTORS = {
    'N': {'jan': 30, 'feb': 50, 'mar': 80, 'apr': 120, 'may': 150, 'jun': 160, 'jul': 150, 'aug': 120, 'sep': 80, 'oct': 50, 'nov': 30, 'dec': 25},
    'NE': {'jan': 30, 'feb': 80, 'mar': 140, 'apr': 180, 'may': 210, 'jun': 220, 'jul': 210, 'aug': 180, 'sep': 140, 'oct': 80, 'nov': 30, 'dec': 25},
    'E': {'jan': 120, 'feb': 160, 'mar': 200, 'apr': 220, 'may': 230, 'jun': 235, 'jul': 230, 'aug': 220, 'sep': 200, 'oct': 160, 'nov': 120, 'dec': 110},
    'SE': {'jan': 190, 'feb': 200, 'mar': 200, 'apr': 190, 'may': 180, 'jun': 175, 'jul': 180, 'aug': 190, 'sep': 200, 'oct': 200, 'nov': 190, 'dec': 185},
    'S': {'jan': 220, 'feb': 210, 'mar': 180, 'apr': 140, 'may': 110, 'jun': 100, 'jul': 110, 'aug': 140, 'sep': 180, 'oct': 210, 'nov': 220, 'dec': 225},
    'SW': {'jan': 190, 'feb': 200, 'mar': 200, 'apr': 190, 'may': 180, 'jun': 175, 'jul': 180, 'aug': 190, 'sep': 200, 'oct': 200, 'nov': 190, 'dec': 185},
    'W': {'jan': 120, 'feb': 160, 'mar': 200, 'apr': 220, 'may': 230, 'jun': 235, 'jul': 230, 'aug': 220, 'sep': 200, 'oct': 160, 'nov': 120, 'dec': 110},
    'NW': {'jan': 30, 'feb': 80, 'mar': 140, 'apr': 180, 'may': 210, 'jun': 220, 'jul': 210, 'aug': 180, 'sep': 140, 'oct': 80, 'nov': 30, 'dec': 25},
}

# Orientation correction factors for CLTD
ORIENTATION_CORRECTIONS = {
    'N': 0.0, 'NE': -5, 'E': -5, 'SE': 0, 'S': 5, 'SW': 0, 'W': -5, 'NW': -5
}


def get_wall_cltd(wall_type: str, orientation: str, hour: int = 14, outdoor_temp: float = 95, indoor_temp: float = 75) -> float:
    """
    Get Cooling Load Temperature Difference for walls
    
    Args:
        wall_type: Type of wall construction
        orientation: Wall orientation (N, E, S, W, etc.)
        hour: Hour of day (0-23), default 14 (2 PM peak)
        outdoor_temp: Outdoor design temperature
        indoor_temp: Indoor design temperature
        
    Returns:
        CLTD value adjusted for actual conditions
    """
    # Get base CLTD from tables
    base_cltd_data = WALL_CLTD_DATA.get(wall_type, WALL_CLTD_DATA['frame_medium'])
    base_cltd = base_cltd_data[min(hour, 23)]
    
    # Apply orientation correction
    orientation_correction = ORIENTATION_CORRECTIONS.get(orientation, 0)
    
    # Apply temperature correction
    temp_correction = (outdoor_temp - 95) + (indoor_temp - 75)
    
    # Final CLTD
    cltd = base_cltd + orientation_correction + temp_correction
    
    return max(cltd, 0)  # CLTD cannot be negative


def get_wall_cltd_vectorized(wall_types: List[str], orientations: List[str], 
                            outdoor_temps: np.ndarray, indoor_temp: float = 75,
                            hours: np.ndarray = None) -> np.ndarray:
    """
    Vectorized CLTD calculation for multiple walls
    
    Args:
        wall_types: List of wall construction types
        orientations: List of wall orientations
        outdoor_temps: Array of outdoor design temperatures
        indoor_temp: Indoor design temperature
        hours: Array of hours (default: peak hour 14)
        
    Returns:
        Array of CLTD values for each wall
    """
    if hours is None:
        hours = np.full(len(wall_types), 14)  # Default to 2 PM peak
    
    results = np.zeros(len(wall_types))
    
    for i, (wall_type, orientation, outdoor_temp, hour) in enumerate(zip(wall_types, orientations, outdoor_temps, hours)):
        # Get base CLTD
        base_cltd_data = WALL_CLTD_DATA.get(wall_type, WALL_CLTD_DATA['frame_medium'])
        base_cltd = base_cltd_data[min(int(hour), 23)]
        
        # Apply orientation correction
        orientation_correction = ORIENTATION_CORRECTIONS.get(orientation, 0)
        
        # Apply temperature correction
        temp_correction = (outdoor_temp - 95) + (indoor_temp - 75)
        
        # Final CLTD
        results[i] = max(base_cltd + orientation_correction + temp_correction, 0)
    
    return results


def get_roof_cltd(roof_type: str, hour: int = 15, outdoor_temp: float = 95, indoor_temp: float = 75) -> float:
    """
    Get Cooling Load Temperature Difference for roofs
    
    Args:
        roof_type: Type of roof construction
        hour: Hour of day (0-23), default 15 (3 PM peak for roofs)
        outdoor_temp: Outdoor design temperature
        indoor_temp: Indoor design temperature
        
    Returns:
        CLTD value adjusted for actual conditions
    """
    # Get base CLTD from tables
    base_cltd_data = ROOF_CLTD_DATA.get(roof_type, ROOF_CLTD_DATA['medium_roof'])
    base_cltd = base_cltd_data[min(hour, 23)]
    
    # Apply temperature correction
    temp_correction = (outdoor_temp - 95) + (indoor_temp - 75)
    
    # Final CLTD
    cltd = base_cltd + temp_correction
    
    return max(cltd, 0)


def calculate_loads_vectorized(areas: np.ndarray, u_factors: np.ndarray, 
                              cltds: np.ndarray) -> np.ndarray:
    """
    Vectorized load calculation using Q = U × A × CLTD
    
    Args:
        areas: Array of areas in sq ft
        u_factors: Array of U-factors
        cltds: Array of CLTD values
        
    Returns:
        Array of cooling loads in BTU/hr
    """
    return areas * u_factors * cltds


def get_glass_clf(orientation: str, hour: int = 14) -> float:
    """
    Get Cooling Load Factor for glass/windows
    
    Args:
        orientation: Window orientation
        hour: Hour of day (0-23)
        
    Returns:
        CLF value for solar heat gain through glass
    """
    # Simplified CLF for glass - varies by orientation and time
    clf_data = {
        'N': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15],
        'NE': [0.15, 0.15, 0.15, 0.15, 0.15, 0.25, 0.50, 0.75, 0.90, 0.95, 0.85, 0.70, 0.55, 0.45, 0.35, 0.30, 0.25, 0.20, 0.20, 0.15, 0.15, 0.15, 0.15, 0.15],
        'E': [0.15, 0.15, 0.15, 0.15, 0.15, 0.30, 0.60, 0.85, 1.00, 0.95, 0.80, 0.65, 0.50, 0.40, 0.30, 0.25, 0.20, 0.20, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15],
        'SE': [0.15, 0.15, 0.15, 0.15, 0.15, 0.25, 0.45, 0.70, 0.90, 1.00, 0.95, 0.85, 0.70, 0.55, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15, 0.15, 0.15, 0.15, 0.15],
        'S': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.20, 0.30, 0.45, 0.65, 0.80, 0.90, 1.00, 0.95, 0.85, 0.70, 0.55, 0.40, 0.30, 0.25, 0.20, 0.15, 0.15, 0.15],
        'SW': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.20, 0.30, 0.45, 0.65, 0.80, 0.90, 1.00, 0.95, 0.85, 0.70, 0.50, 0.35, 0.25, 0.20, 0.15, 0.15, 0.15],
        'W': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.20, 0.25, 0.35, 0.50, 0.65, 0.80, 0.95, 1.00, 0.90, 0.75, 0.55, 0.40, 0.30, 0.25, 0.20, 0.15, 0.15],
        'NW': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.20, 0.30, 0.45, 0.60, 0.75, 0.90, 0.95, 0.85, 0.70, 0.50, 0.35, 0.25, 0.20, 0.15, 0.15, 0.15],
    }
    
    orientation_data = clf_data.get(orientation, clf_data['S'])
    return orientation_data[min(hour, 23)]


def calculate_wall_load_cltd(area: float, u_factor: float, wall_type: str, orientation: str, 
                            outdoor_temp: float, indoor_temp: float = 75, hour: int = 14) -> float:
    """
    Calculate cooling load through walls using CLTD method
    
    Q = U × A × CLTD
    
    Args:
        area: Wall area in sq ft
        u_factor: Overall heat transfer coefficient (1/R-value)
        wall_type: Construction type
        orientation: Wall orientation
        outdoor_temp: Outdoor design temperature
        indoor_temp: Indoor design temperature
        hour: Hour of day for peak calculation
        
    Returns:
        Cooling load in BTU/hr
    """
    cltd = get_wall_cltd(wall_type, orientation, hour, outdoor_temp, indoor_temp)
    return u_factor * area * cltd


def calculate_roof_load_cltd(area: float, u_factor: float, roof_type: str,
                            outdoor_temp: float, indoor_temp: float = 75, hour: int = 15) -> float:
    """
    Calculate cooling load through roof using CLTD method
    
    Args:
        area: Roof area in sq ft
        u_factor: Overall heat transfer coefficient (1/R-value)
        roof_type: Construction type
        outdoor_temp: Outdoor design temperature
        indoor_temp: Indoor design temperature
        hour: Hour of day for peak calculation
        
    Returns:
        Cooling load in BTU/hr
    """
    cltd = get_roof_cltd(roof_type, hour, outdoor_temp, indoor_temp)
    return u_factor * area * cltd


def calculate_window_solar_load(area: float, shading_coefficient: float, orientation: str,
                               month: str = 'jul', hour: int = 14, latitude: float = 40.0,
                               overhang_depth: float = 0.0, window_height: float = 4.0,
                               sill_height: float = 3.0) -> float:
    """
    Calculate solar heat gain through windows using enhanced CLF method with shading
    
    Q = A × SC × SHGF × CLF × Shading_Factor
    
    Args:
        area: Window area in sq ft
        shading_coefficient: Shading coefficient or SHGC (0.0-1.0)
        orientation: Window orientation
        month: Month for calculation (default July for peak)
        hour: Hour of day
        latitude: Building latitude for sun angle calculations
        overhang_depth: Depth of overhang in feet (0 if none)
        window_height: Height of window in feet
        sill_height: Height from floor to window sill in feet
        
    Returns:
        Solar cooling load in BTU/hr
    """
    # Get solar heat gain factor
    shgf_data = SOLAR_HEAT_GAIN_FACTORS.get(orientation, SOLAR_HEAT_GAIN_FACTORS['S'])
    shgf = shgf_data.get(month, shgf_data['jul'])
    
    # Get cooling load factor
    clf = get_glass_clf(orientation, hour)
    
    # Calculate shading factor if overhang present
    shading_factor = 1.0
    if overhang_depth > 0:
        shading_factor = calculate_overhang_shading(
            orientation, latitude, month, hour, 
            overhang_depth, window_height, sill_height
        )
    
    return area * shading_coefficient * shgf * clf * shading_factor


def calculate_overhang_shading(orientation: str, latitude: float, month: str, hour: int,
                               overhang_depth: float, window_height: float, 
                               sill_height: float) -> float:
    """
    Calculate shading factor from overhang using simplified sun angle method
    
    Args:
        orientation: Window orientation
        latitude: Building latitude
        month: Month for calculation
        hour: Hour of day (0-23)
        overhang_depth: Horizontal projection of overhang (ft)
        window_height: Height of window (ft)
        sill_height: Height from floor to window sill (ft)
        
    Returns:
        Shading factor (0.0 = fully shaded, 1.0 = no shading)
    """
    # Simplified solar altitude angles by month and latitude
    # These are approximate noon values for mid-latitudes (30-45°N)
    solar_altitude = {
        'jan': 30, 'feb': 40, 'mar': 50, 'apr': 60, 'may': 70, 'jun': 75,
        'jul': 73, 'aug': 65, 'sep': 55, 'oct': 45, 'nov': 35, 'dec': 28
    }
    
    # Adjust for latitude (rough approximation)
    lat_adjustment = (latitude - 40) * 0.5
    altitude = solar_altitude.get(month, 60) - lat_adjustment
    
    # Time adjustment (peak shading typically 2-3 hours after solar noon)
    if 10 <= hour <= 16:
        time_factor = 1.0 - abs(hour - 13) * 0.1
    else:
        time_factor = 0.1  # Minimal solar gain outside peak hours
    
    # For east/west faces, adjust for azimuth angle
    if orientation in ['E', 'W']:
        if (orientation == 'E' and hour < 12) or (orientation == 'W' and hour > 12):
            azimuth_factor = 0.8
        else:
            azimuth_factor = 0.2
        time_factor *= azimuth_factor
    
    # Calculate shadow depth
    if altitude > 0:
        shadow_depth = overhang_depth / math.tan(math.radians(altitude))
    else:
        shadow_depth = 999  # Full shading at night
    
    # Calculate shaded fraction of window
    window_top = sill_height + window_height
    overhang_height = window_top  # Assume overhang at top of window
    
    if shadow_depth >= window_height:
        shaded_fraction = 1.0  # Fully shaded
    elif shadow_depth <= 0:
        shaded_fraction = 0.0  # No shading
    else:
        shaded_fraction = shadow_depth / window_height
    
    # Convert to shading factor (1 - shaded portion) with time adjustment
    shading_factor = (1.0 - shaded_fraction * time_factor)
    
    return max(0.1, min(1.0, shading_factor))  # Clamp between 0.1 and 1.0


def calculate_window_conduction_load(area: float, u_factor: float, outdoor_temp: float, 
                                   indoor_temp: float = 75) -> float:
    """
    Calculate conduction heat gain through windows
    
    Q = U × A × ΔT
    
    Args:
        area: Window area in sq ft
        u_factor: Window U-factor
        outdoor_temp: Outdoor design temperature
        indoor_temp: Indoor design temperature
        
    Returns:
        Conduction cooling load in BTU/hr
    """
    delta_t = outdoor_temp - indoor_temp
    return u_factor * area * delta_t


def calculate_internal_load_clf(heat_gain: float, source_type: str, hour: int = 14) -> float:
    """
    Calculate internal cooling load using CLF method
    
    Args:
        heat_gain: Internal heat gain in BTU/hr
        source_type: Type of heat source ('people', 'lighting', 'equipment')
        hour: Hour of day
        
    Returns:
        Cooling load in BTU/hr
    """
    clf_data = INTERNAL_CLF_DATA.get(source_type, INTERNAL_CLF_DATA['equipment'])
    clf = clf_data[min(hour, 23)]
    
    return heat_gain * clf


def get_diversity_factor(total_rooms: int, room_type: str = 'residential') -> float:
    """
    Get Manual J diversity factor to prevent oversizing
    
    Args:
        total_rooms: Total number of conditioned rooms
        room_type: Type of building ('residential', 'office', etc.)
        
    Returns:
        Diversity factor (typically 0.75-0.95)
    """
    if room_type == 'residential':
        # ACCA Manual J diversity factors for residential
        if total_rooms <= 3:
            return 1.0
        elif total_rooms <= 6:
            return 0.95
        elif total_rooms <= 10:
            return 0.90
        elif total_rooms <= 15:
            return 0.85
        else:
            return 0.80
    
    # Default for other building types
    return 0.90