"""
Climate Zone Lookup - Determine ASHRAE climate zone from ZIP code
"""

import logging

logger = logging.getLogger(__name__)


# Simplified climate zone mapping by ZIP code prefix
# Based on ASHRAE/IECC climate zones
ZIP_TO_CLIMATE_ZONE = {
    # Zone 1 - Very Hot Humid (Miami, Hawaii)
    "330": "1A", "331": "1A", "332": "1A", "333": "1A", "334": "1A",
    "967": "1A", "968": "1A",  # Hawaii
    
    # Zone 2 - Hot Humid/Dry (Houston, Phoenix)
    "700": "2A", "701": "2A", "770": "2A", "771": "2A", "772": "2A",
    "773": "2A", "774": "2A", "775": "2A", "776": "2A", "777": "2A",
    "778": "2A", "779": "2A",  # Texas
    "850": "2B", "851": "2B", "852": "2B", "853": "2B",  # Arizona
    
    # Zone 3 - Warm Humid/Dry (Atlanta, Los Angeles)
    "300": "3A", "301": "3A", "302": "3A", "303": "3A", "304": "3A",
    "305": "3A", "306": "3A", "307": "3A", "308": "3A", "309": "3A",
    "310": "3A", "311": "3A", "312": "3A", "313": "3A", "314": "3A",
    "315": "3A", "316": "3A", "317": "3A", "318": "3A", "319": "3A",  # Georgia
    "900": "3B", "901": "3B", "902": "3B", "903": "3B", "904": "3B",
    "905": "3B", "906": "3B", "907": "3B", "908": "3B",  # California
    
    # Zone 4 - Mixed Humid/Dry (DC, NYC, Seattle)
    "100": "4A", "101": "4A", "102": "4A", "103": "4A", "104": "4A",
    "105": "4A", "106": "4A", "107": "4A", "108": "4A", "109": "4A",
    "110": "4A", "111": "4A", "112": "4A", "113": "4A", "114": "4A",  # NYC area
    "200": "4A", "201": "4A", "202": "4A",  # DC area
    "980": "4C", "981": "4C", "982": "4C", "983": "4C", "984": "4C",  # Seattle
    
    # Zone 5 - Cool Humid/Dry (Chicago, Denver)
    "600": "5A", "601": "5A", "602": "5A", "603": "5A", "604": "5A",
    "605": "5A", "606": "5A",  # Chicago
    "800": "5B", "801": "5B", "802": "5B", "803": "5B", "804": "5B",  # Colorado
    
    # Zone 6 - Cold Humid/Dry (Minneapolis, Montana)
    "550": "6A", "551": "6A", "552": "6A", "553": "6A", "554": "6A",
    "555": "6A", "556": "6A", "557": "6A", "558": "6A", "559": "6A",  # Minnesota
    "590": "6B", "591": "6B", "592": "6B", "593": "6B", "594": "6B",  # Montana
    
    # Zone 7 - Very Cold (Northern Minnesota, Alaska interior)
    "560": "7", "561": "7", "562": "7", "563": "7", "564": "7",
    "565": "7", "566": "7", "567": "7",  # Northern MN
    "996": "7", "997": "7",  # Alaska interior
    
    # Zone 8 - Subarctic/Arctic (Alaska north)
    "998": "8", "999": "8",  # Northern Alaska
    
    # Special case for Washington state (99xxx)
    "990": "4C", "991": "4C", "992": "4C", "993": "4C", "994": "4C",
    
    # Add more mappings as needed...
}


def get_climate_zone(zip_code: str) -> str:
    """
    Get ASHRAE climate zone from ZIP code
    
    Args:
        zip_code: 5-digit ZIP code
        
    Returns:
        Climate zone string (e.g., "4A", "5B")
    """
    if not zip_code or len(zip_code) < 3:
        logger.warning(f"Invalid ZIP code: {zip_code}, defaulting to zone 4A")
        return "4A"
    
    # Try exact prefix match first (3 digits)
    prefix = zip_code[:3]
    if prefix in ZIP_TO_CLIMATE_ZONE:
        zone = ZIP_TO_CLIMATE_ZONE[prefix]
        logger.info(f"ZIP {zip_code} -> Climate Zone {zone}")
        return zone
    
    # Try 2-digit prefix for broader regions
    prefix2 = zip_code[:2]
    
    # Broad regional defaults
    region_defaults = {
        "00": "4A",  # Northeast
        "01": "5A",  # Massachusetts
        "02": "5A",  # Rhode Island
        "03": "6A",  # New Hampshire
        "04": "6A",  # Maine
        "05": "5A",  # Vermont
        "06": "5A",  # Connecticut
        "07": "4A",  # New Jersey
        "08": "4A",  # New Jersey
        "09": "4A",  # New Jersey
        "10": "4A",  # New York
        "11": "4A",  # New York
        "12": "5A",  # New York
        "13": "5A",  # New York
        "14": "5A",  # New York
        "15": "5A",  # Pennsylvania
        "16": "5A",  # Pennsylvania
        "17": "5A",  # Pennsylvania
        "18": "5A",  # Pennsylvania
        "19": "4A",  # Pennsylvania/Delaware
        "20": "4A",  # DC/Maryland
        "21": "4A",  # Maryland
        "22": "4A",  # Virginia
        "23": "4A",  # Virginia
        "24": "4A",  # West Virginia
        "25": "5A",  # West Virginia
        "26": "5A",  # West Virginia
        "27": "4A",  # North Carolina
        "28": "3A",  # North Carolina
        "29": "3A",  # South Carolina
        "30": "3A",  # Georgia
        "31": "3A",  # Georgia
        "32": "2A",  # Florida
        "33": "1A",  # Florida
        "34": "2A",  # Florida
        "35": "3A",  # Alabama
        "36": "3A",  # Alabama
        "37": "3A",  # Tennessee
        "38": "3A",  # Tennessee
        "39": "3A",  # Mississippi
        "40": "4A",  # Kentucky
        "41": "4A",  # Kentucky
        "42": "4A",  # Kentucky
        "43": "5A",  # Ohio
        "44": "5A",  # Ohio
        "45": "5A",  # Ohio
        "46": "5A",  # Indiana
        "47": "5A",  # Indiana
        "48": "5A",  # Illinois
        "49": "5A",  # Michigan
        "50": "5A",  # Iowa
        "51": "5A",  # Iowa
        "52": "5A",  # Iowa
        "53": "5A",  # Wisconsin
        "54": "6A",  # Wisconsin
        "55": "6A",  # Minnesota
        "56": "7",   # Minnesota/North Dakota
        "57": "6A",  # South Dakota
        "58": "6A",  # North Dakota
        "59": "6B",  # Montana
        "60": "5A",  # Illinois
        "61": "5A",  # Illinois
        "62": "5A",  # Illinois
        "63": "4A",  # Missouri
        "64": "4A",  # Missouri
        "65": "4A",  # Missouri
        "66": "4A",  # Kansas
        "67": "4A",  # Kansas
        "68": "5A",  # Nebraska
        "69": "5A",  # Nebraska
        "70": "2A",  # Louisiana
        "71": "3A",  # Louisiana
        "72": "3A",  # Arkansas
        "73": "3A",  # Oklahoma
        "74": "3A",  # Oklahoma
        "75": "2A",  # Texas
        "76": "2A",  # Texas
        "77": "2A",  # Texas
        "78": "2A",  # Texas
        "79": "3B",  # Texas
        "80": "5B",  # Colorado
        "81": "5B",  # Colorado
        "82": "6B",  # Wyoming
        "83": "6B",  # Idaho
        "84": "5B",  # Utah
        "85": "2B",  # Arizona
        "86": "3B",  # Arizona
        "87": "4B",  # New Mexico
        "88": "3B",  # New Mexico
        "89": "3B",  # Nevada
        "90": "3B",  # California
        "91": "3B",  # California
        "92": "3B",  # California
        "93": "3B",  # California
        "94": "3C",  # California
        "95": "3C",  # California
        "96": "3C",  # California
        "97": "4C",  # Oregon
        "98": "4C",  # Washington
        "99": "7",   # Alaska (default)
    }
    
    if prefix2 in region_defaults:
        zone = region_defaults[prefix2]
        logger.info(f"ZIP {zip_code} -> Climate Zone {zone} (regional default)")
        return zone
    
    # Default fallback
    logger.warning(f"Unknown ZIP {zip_code}, defaulting to zone 4A")
    return "4A"


def get_design_temperatures(climate_zone: str) -> Dict[str, float]:
    """
    Get design temperatures for a climate zone
    
    Args:
        climate_zone: ASHRAE climate zone
        
    Returns:
        Dict with winter and summer design temperatures
    """
    design_temps = {
        "1A": {"winter": 47, "summer": 92},  # Miami
        "2A": {"winter": 35, "summer": 94},  # Houston
        "2B": {"winter": 37, "summer": 108}, # Phoenix
        "3A": {"winter": 25, "summer": 91},  # Atlanta
        "3B": {"winter": 42, "summer": 83},  # Los Angeles
        "3C": {"winter": 38, "summer": 78},  # San Francisco
        "4A": {"winter": 17, "summer": 89},  # NYC
        "4B": {"winter": 18, "summer": 95},  # Albuquerque
        "4C": {"winter": 33, "summer": 81},  # Seattle
        "5A": {"winter": 6, "summer": 87},   # Chicago
        "5B": {"winter": 7, "summer": 88},   # Denver
        "6A": {"winter": -7, "summer": 86},  # Minneapolis
        "6B": {"winter": -10, "summer": 85}, # Helena
        "7": {"winter": -18, "summer": 82},  # Duluth
        "8": {"winter": -35, "summer": 73},  # Fairbanks
    }
    
    if climate_zone in design_temps:
        return design_temps[climate_zone]
    
    # Default to zone 4A
    logger.warning(f"Unknown climate zone {climate_zone}, using 4A defaults")
    return design_temps["4A"]