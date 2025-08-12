"""
Latitude-aware Solar Heat Gain Factors for HVAC calculations
Based on ASHRAE Fundamentals data
"""

def get_shgf_by_latitude(latitude: float, orientation: str, month: str = 'jul', hour: int = 14) -> float:
    """
    Get Solar Heat Gain Factor by latitude band
    
    Args:
        latitude: Geographic latitude
        orientation: Cardinal direction (N, E, S, W, NE, SE, SW, NW)
        month: Design month (default 'jul' for cooling)
        hour: Hour of day (default 14 for peak cooling)
        
    Returns:
        SHGF in BTU/hr/sqft
    """
    # ASHRAE Fundamentals Table - BTU/hr/sqft for clear day
    SHGF_TABLES = {
        'lat_24_32': {  # Southern US (Miami, Houston, Phoenix)
            'N': {'jul': 38, 'jan': 27, 'apr': 32, 'oct': 30},
            'NE': {'jul': 89, 'jan': 55, 'apr': 120, 'oct': 65},
            'E': {'jul': 216, 'jan': 166, 'apr': 198, 'oct': 180},
            'SE': {'jul': 161, 'jan': 204, 'apr': 182, 'oct': 195},
            'S': {'jul': 97, 'jan': 254, 'apr': 140, 'oct': 220},
            'SW': {'jul': 161, 'jan': 204, 'apr': 182, 'oct': 195},
            'W': {'jul': 216, 'jan': 166, 'apr': 198, 'oct': 180},
            'NW': {'jul': 89, 'jan': 55, 'apr': 120, 'oct': 65}
        },
        'lat_32_40': {  # Central US (Atlanta, Dallas, Los Angeles)
            'N': {'jul': 41, 'jan': 24, 'apr': 34, 'oct': 28},
            'NE': {'jul': 84, 'jan': 42, 'apr': 110, 'oct': 55},
            'E': {'jul': 198, 'jan': 139, 'apr': 186, 'oct': 162},
            'SE': {'jul': 142, 'jan': 189, 'apr': 168, 'oct': 180},
            'S': {'jul': 89, 'jan': 238, 'apr': 126, 'oct': 198},
            'SW': {'jul': 142, 'jan': 189, 'apr': 168, 'oct': 180},
            'W': {'jul': 198, 'jan': 139, 'apr': 186, 'oct': 162},
            'NW': {'jul': 84, 'jan': 42, 'apr': 110, 'oct': 55}
        },
        'lat_40_48': {  # Northern US (Chicago, New York, Seattle)
            'N': {'jul': 46, 'jan': 20, 'apr': 36, 'oct': 25},
            'NE': {'jul': 78, 'jan': 28, 'apr': 98, 'oct': 45},
            'E': {'jul': 178, 'jan': 109, 'apr': 170, 'oct': 140},
            'SE': {'jul': 120, 'jan': 168, 'apr': 150, 'oct': 162},
            'S': {'jul': 82, 'jan': 214, 'apr': 110, 'oct': 176},
            'SW': {'jul': 120, 'jan': 168, 'apr': 150, 'oct': 162},
            'W': {'jul': 178, 'jan': 109, 'apr': 170, 'oct': 140},
            'NW': {'jul': 78, 'jan': 28, 'apr': 98, 'oct': 45}
        },
        'lat_48_56': {  # Far Northern US/Canada (Anchorage, Calgary)
            'N': {'jul': 52, 'jan': 15, 'apr': 38, 'oct': 22},
            'NE': {'jul': 72, 'jan': 18, 'apr': 85, 'oct': 35},
            'E': {'jul': 156, 'jan': 78, 'apr': 150, 'oct': 115},
            'SE': {'jul': 98, 'jan': 142, 'apr': 128, 'oct': 140},
            'S': {'jul': 75, 'jan': 186, 'apr': 95, 'oct': 152},
            'SW': {'jul': 98, 'jan': 142, 'apr': 128, 'oct': 140},
            'W': {'jul': 156, 'jan': 78, 'apr': 150, 'oct': 115},
            'NW': {'jul': 72, 'jan': 18, 'apr': 85, 'oct': 35}
        }
    }
    
    # Select table by latitude band
    if latitude < 32:
        table = SHGF_TABLES['lat_24_32']
    elif latitude < 40:
        table = SHGF_TABLES['lat_32_40']
    elif latitude < 48:
        table = SHGF_TABLES['lat_40_48']
    else:
        table = SHGF_TABLES['lat_48_56']
    
    # Get values for orientation and month
    orientation_data = table.get(orientation.upper(), table.get('S'))  # Default to South
    month_value = orientation_data.get(month.lower(), orientation_data.get('jul'))
    
    # Apply time-of-day adjustment (simplified)
    # Peak is around 14:00 (2 PM), reduce for other hours
    if hour < 8 or hour > 18:
        month_value *= 0.1  # Minimal solar gain outside daylight
    elif hour < 10:
        month_value *= 0.5  # Morning ramp-up
    elif hour > 16:
        month_value *= 0.5  # Evening ramp-down
    # else: use full value for 10-16 hours
    
    return month_value


def get_cooling_design_month(latitude: float) -> str:
    """
    Get the design month for cooling calculations based on latitude
    
    Args:
        latitude: Geographic latitude
        
    Returns:
        Month string ('jul', 'aug', etc.)
    """
    if latitude < 30:
        # Southern regions peak later
        return 'aug'
    elif latitude < 35:
        return 'jul'
    elif latitude < 45:
        return 'jul'
    else:
        # Northern regions peak earlier
        return 'jun'


def get_heating_design_month(latitude: float) -> str:
    """
    Get the design month for heating calculations based on latitude
    
    Args:
        latitude: Geographic latitude
        
    Returns:
        Month string ('jan', 'dec', etc.)
    """
    if latitude < 35:
        # Southern regions coldest in January
        return 'jan'
    else:
        # Northern regions may be colder in December
        return 'dec'