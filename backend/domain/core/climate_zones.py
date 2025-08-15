"""
IECC Climate Zone Configuration System
Provides zone-specific parameters for accurate Manual J calculations across all US climate zones

Based on authoritative sources:
- 2021 IECC (International Energy Conservation Code) Table R402.1.3
- ASHRAE Fundamentals Handbook
- ACCA Manual J 8th Edition
- ENERGY STAR Version 7.0 Requirements

This module consolidates:
- Climate zone configurations (R-values, infiltration, duct losses)
- ZIP code to climate zone mapping
- ASHRAE design temperature data
- Construction quality adjustments
"""

import csv
import os
from typing import Dict, Any, Optional
from functools import lru_cache
from .zip_climate_zones import get_climate_zone_fast


# Building Era-Based Insulation Defaults
# These override zone defaults when building age is known
ERA_INSULATION_DEFAULTS = {
    "1960s": {
        "wall_r": 11,      # 2x4 with R-11 batts
        "roof_r": 19,      # Minimal attic insulation
        "floor_r": 11,     # Often uninsulated crawlspace
        "window_u": 1.0,   # Single pane
        "infiltration_ach": 0.7,  # Very leaky
    },
    "1970s": {
        "wall_r": 11,      # 2x4 with R-11
        "roof_r": 19,      # R-19 attic
        "floor_r": 13,     # Some floor insulation
        "window_u": 0.8,   # Single or poor double
        "infiltration_ach": 0.6,
    },
    "1980s": {
        "wall_r": 13,      # 2x4 with R-13
        "roof_r": 30,      # R-30 attic (energy crisis era)
        "floor_r": 19,     # R-19 floor
        "window_u": 0.5,   # Double pane aluminum
        "infiltration_ach": 0.5,
    },
    "1990s": {
        "wall_r": 13,      # 2x4 with R-13 or early 2x6
        "roof_r": 30,      # R-30 standard
        "floor_r": 19,     # R-19 floor
        "window_u": 0.45,  # Double pane vinyl
        "infiltration_ach": 0.4,
    },
    "2000s": {
        "wall_r": 19,      # 2x6 with R-19
        "roof_r": 38,      # R-38 attic
        "floor_r": 25,     # R-25 floor
        "window_u": 0.35,  # Double pane low-E
        "infiltration_ach": 0.35,
    },
    "2010s": {
        "wall_r": 20,      # 2x6 with R-20 or better
        "roof_r": 49,      # R-49 energy code
        "floor_r": 30,     # R-30 floor
        "window_u": 0.30,  # Low-E with argon
        "infiltration_ach": 0.25,
    },
    "2020s": {
        "wall_r": 21,      # Advanced framing
        "roof_r": 60,      # R-60 high performance
        "floor_r": 30,     # R-30 floor
        "window_u": 0.25,  # Triple pane or high-performance double
        "infiltration_ach": 0.15,  # Very tight with HRV
    },
    "new": {  # NEW CONSTRUCTION - CODE MINIMUM (worst case for sizing)
        # IMPORTANT: Use these for ALL new construction regardless of year
        # Size for cheapest windows/insulation that meets code
        "wall_r": 20,       # 2021 IECC minimum (not high-performance)
        "roof_r": 49,       # 2021 IECC minimum (not R-60)
        "floor_r": 30,      # 2021 IECC minimum
        "window_u": 0.30,   # Code max U-value (not high-perf 0.25)
        "infiltration_ach": 0.20,  # Code max (3 ACH50 ÷ 15 = 0.20 worst case)
    }
}

# IECC Climate Zone 1-8 Configurations
# Using official standards from 2021 IECC and ACCA Manual J
CLIMATE_ZONE_CONFIGS = {
    "1": {  # Very Hot - Humid (Southern Florida, Hawaii)
        "name": "Very Hot - Humid",
        "description": "Cooling-only climate with high humidity",
        "heating_dominated": False,
        "cooling_dominated": True,
        "balanced_loads": False,
        
        # 2021 IECC Requirements (Table R402.1.3)
        "typical_wall_r": 13,  # IECC: R-13
        "typical_roof_r": 30,  # IECC: R-30 for zones 1-3
        "typical_floor_r": 13,  # IECC: R-13 for zones 1-3
        "typical_window_u": 0.40,  # No U-factor requirement
        "typical_window_shgc": 0.25,  # IECC: ≤0.25 for zones 1-3
        
        # Infiltration per 2021 IECC (≤5 ACH50 for zones 1-2)
        "typical_infiltration_ach": 0.25,  # 5 ACH50 ÷ 20 = 0.25 natural
        "tight_infiltration_ach": 0.15,
        "loose_infiltration_ach": 0.35,
        
        # ACCA Manual J factors for Zone 1
        "solar_gain_factor": 50,  # Peak BTU/sqft (high solar)
        "roof_solar_factor": 40,  # Intense roof heat gain
        
        # Duct losses per ACCA Manual J Table 7
        "duct_loss_heating": 1.05,  # 5% heating (minimal)
        "duct_loss_cooling": 1.15,  # 15% cooling (hot attic)
        "ventilation_factor": 1.2,  # High due to humidity
        "safety_factor_heating": 1.0,  # No oversizing needed
        "safety_factor_cooling": 1.05,  # ACCA: 95-115% for cooling
        
        # Humidity
        "indoor_humidity_ratio": 0.0095,  # 75°F @ 50% RH
        "outdoor_humidity_ratio_summer": 0.014,  # Very humid
        "outdoor_humidity_ratio_winter": 0.010,
    },
    
    "2": {  # Hot (Houston, Phoenix, Southern Texas)
        "name": "Hot",
        "description": "Cooling-dominated with minimal heating",
        "heating_dominated": False,
        "cooling_dominated": True,
        "balanced_loads": False,
        
        # 2021 IECC Requirements
        "typical_wall_r": 13,  # IECC: R-13
        "typical_roof_r": 30,  # IECC: R-30 for zones 1-3
        "typical_floor_r": 13,  # IECC: R-13
        "typical_window_u": 0.40,  # IECC: ≤0.40 (no U-factor req for zone 2)
        "typical_window_shgc": 0.25,  # IECC: ≤0.25
        
        # Infiltration per 2021 IECC (≤5 ACH50)
        "typical_infiltration_ach": 0.25,  # 5 ACH50 ÷ 20
        "tight_infiltration_ach": 0.15,
        "loose_infiltration_ach": 0.35,
        
        # ACCA Manual J factors
        "solar_gain_factor": 45,  # High solar gain
        "roof_solar_factor": 35,
        
        # Duct losses per ACCA Manual J
        "duct_loss_heating": 1.05,  # Minimal heating
        "duct_loss_cooling": 1.12,  # Significant cooling losses
        "ventilation_factor": 1.15,
        "safety_factor_heating": 1.0,
        "safety_factor_cooling": 1.05,  # ACCA: 95-115%
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.012,  # Varies (humid/dry)
        "outdoor_humidity_ratio_winter": 0.008,
    },
    
    "3": {  # Warm (Atlanta, Los Angeles, Charlotte)
        "name": "Warm",
        "description": "Mixed heating and cooling",
        "heating_dominated": False,
        "cooling_dominated": False,
        "balanced_loads": True,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20 or R-13+10
        "typical_roof_r": 30,  # IECC: R-30
        "typical_floor_r": 19,  # IECC: R-19
        "typical_window_u": 0.32,  # IECC: ≤0.32
        "typical_window_shgc": 0.25,  # IECC: ≤0.25
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20
        "tight_infiltration_ach": 0.10,
        "loose_infiltration_ach": 0.25,
        
        # ACCA Manual J factors
        "solar_gain_factor": 35,
        "roof_solar_factor": 30,
        
        # Duct losses
        "duct_loss_heating": 1.08,
        "duct_loss_cooling": 1.10,
        "ventilation_factor": 1.1,
        "safety_factor_heating": 1.05,
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.011,
        "outdoor_humidity_ratio_winter": 0.006,
    },
    
    "4": {  # Mixed (DC, Seattle, Kansas City)
        "name": "Mixed",
        "description": "Balanced heating and cooling needs",
        "heating_dominated": False,
        "cooling_dominated": False,
        "balanced_loads": True,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20 or R-13+10
        "typical_roof_r": 49,  # IECC: R-49 (increased from R-38)
        "typical_floor_r": 19,  # IECC: R-19
        "typical_window_u": 0.32,  # IECC: ≤0.32
        "typical_window_shgc": 0.40,  # IECC: ≤0.40 (or no requirement)
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20
        "tight_infiltration_ach": 0.10,
        "loose_infiltration_ach": 0.25,
        
        # ACCA Manual J factors
        "solar_gain_factor": 30,
        "roof_solar_factor": 25,
        
        # Duct losses
        "duct_loss_heating": 1.10,
        "duct_loss_cooling": 1.08,
        "ventilation_factor": 1.1,
        "safety_factor_heating": 1.08,
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.010,
        "outdoor_humidity_ratio_winter": 0.004,
    },
    
    "5": {  # Cool (Chicago, Denver, Boston, Spokane)
        "name": "Cool",
        "description": "Heating-dominated with significant cooling",
        "heating_dominated": True,
        "cooling_dominated": False,
        "balanced_loads": False,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20 or R-13+10
        "typical_roof_r": 49,  # IECC: R-49 (increased from R-38)
        "typical_floor_r": 30,  # IECC: R-30
        "typical_window_u": 0.30,  # IECC: ≤0.30
        "typical_window_shgc": 0.40,  # Any SHGC allowed
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20
        "tight_infiltration_ach": 0.10,
        "loose_infiltration_ach": 0.25,
        
        # ACCA Manual J factors
        "solar_gain_factor": 30,  # Moderate solar
        "roof_solar_factor": 25,
        
        # Duct losses (typically in unconditioned space)
        "duct_loss_heating": 1.12,  # 12% heating loss
        "duct_loss_cooling": 1.05,  # 5% cooling loss
        "ventilation_factor": 1.15,
        "safety_factor_heating": 1.10,  # ACCA allows up to 140%
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.009,
        "outdoor_humidity_ratio_winter": 0.002,
    },
    
    "6": {  # Cold (Minneapolis, Montana, Maine)
        "name": "Cold",
        "description": "Heating-dominated with minimal cooling",
        "heating_dominated": True,
        "cooling_dominated": False,
        "balanced_loads": False,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20+5 or R-13+10
        "typical_roof_r": 49,  # IECC: R-49
        "typical_floor_r": 30,  # IECC: R-30
        "typical_window_u": 0.30,  # IECC: ≤0.30
        "typical_window_shgc": 0.40,  # Any SHGC allowed
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20
        "tight_infiltration_ach": 0.10,
        "loose_infiltration_ach": 0.25,
        
        # ACCA Manual J factors
        "solar_gain_factor": 25,  # Limited solar in winter
        "roof_solar_factor": 20,
        
        # Duct losses (cold attics/crawlspaces)
        "duct_loss_heating": 1.15,  # 15% heating loss
        "duct_loss_cooling": 1.05,  # 5% cooling loss
        "ventilation_factor": 1.2,
        "safety_factor_heating": 1.15,  # ACCA allows up to 140%
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.008,
        "outdoor_humidity_ratio_winter": 0.001,
    },
    
    "7": {  # Very Cold (Northern Minnesota, Wisconsin)
        "name": "Very Cold",
        "description": "Extreme heating requirements",
        "heating_dominated": True,
        "cooling_dominated": False,
        "balanced_loads": False,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20+5 or R-13+10
        "typical_roof_r": 60,  # IECC: R-60 (increased from R-49)
        "typical_floor_r": 38,  # IECC: R-38
        "typical_window_u": 0.30,  # IECC: ≤0.30
        "typical_window_shgc": 0.45,  # Any SHGC (maximize solar gain)
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20
        "tight_infiltration_ach": 0.10,
        "loose_infiltration_ach": 0.25,
        
        # ACCA Manual J factors
        "solar_gain_factor": 20,  # Limited winter sun
        "roof_solar_factor": 15,
        
        # Duct losses (extreme cold)
        "duct_loss_heating": 1.18,  # 18% heating loss
        "duct_loss_cooling": 1.0,  # Minimal cooling
        "ventilation_factor": 1.25,
        "safety_factor_heating": 1.20,  # Higher safety margin
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.007,
        "outdoor_humidity_ratio_winter": 0.0005,
    },
    
    "8": {  # Subarctic (Alaska)
        "name": "Subarctic",
        "description": "Extreme cold climate",
        "heating_dominated": True,
        "cooling_dominated": False,
        "balanced_loads": False,
        
        # 2021 IECC Requirements
        "typical_wall_r": 20,  # IECC: R-20+5 or R-13+10 minimum
        "typical_roof_r": 60,  # IECC: R-60
        "typical_floor_r": 38,  # IECC: R-38
        "typical_window_u": 0.30,  # IECC: ≤0.30 (triple pane recommended)
        "typical_window_shgc": 0.50,  # Maximum solar gain critical
        
        # Infiltration per 2021 IECC (≤3 ACH50)
        "typical_infiltration_ach": 0.15,  # 3 ACH50 ÷ 20 (critical for extreme cold)
        "tight_infiltration_ach": 0.08,  # Super tight construction
        "loose_infiltration_ach": 0.20,  # Even "loose" must be tight in zone 8
        
        # ACCA Manual J factors
        "solar_gain_factor": 15,  # Very limited sun in winter
        "roof_solar_factor": 10,
        
        # Duct losses (extreme conditions)
        "duct_loss_heating": 1.20,  # 20% heating loss
        "duct_loss_cooling": 1.0,  # No cooling needed
        "ventilation_factor": 1.3,  # HRV/ERV critical
        "safety_factor_heating": 1.25,  # Maximum safety margin
        "safety_factor_cooling": 1.0,
        
        "indoor_humidity_ratio": 0.0095,
        "outdoor_humidity_ratio_summer": 0.006,
        "outdoor_humidity_ratio_winter": 0.0001,
    }
}


def get_zone_config(climate_zone: str) -> Dict[str, Any]:
    """
    Get configuration for a specific climate zone
    
    Args:
        climate_zone: IECC climate zone (e.g., "5B", "3A", "2A")
        
    Returns:
        Configuration dictionary for the zone
    """
    # Extract zone number from format like "5B"
    zone_number = climate_zone[0] if climate_zone else "4"
    
    # Return config, defaulting to zone 4 (mixed) if not found
    return CLIMATE_ZONE_CONFIGS.get(zone_number, CLIMATE_ZONE_CONFIGS["4"])


def get_era_based_factors(building_era: str, zone_config: dict) -> dict:
    """
    Get construction factors based on building era
    Era takes precedence over zone defaults
    
    CRITICAL FOR NEW CONSTRUCTION:
    - Always use CODE MINIMUM values, not high-performance
    - This ensures proper sizing for worst-case (cheapest legal) construction
    """
    if not building_era:
        return {}
    
    # Normalize era string
    era_key = building_era.lower().strip()
    
    # Check for new construction keywords
    if era_key in ['new', 'new construction', 'new build', 'proposed']:
        return ERA_INSULATION_DEFAULTS["new"]
    
    if era_key in ERA_INSULATION_DEFAULTS:
        return ERA_INSULATION_DEFAULTS[era_key]
    
    # Try to extract decade from year
    if era_key.isdigit() and len(era_key) == 4:
        year = int(era_key)
        
        # For recent years (2020+), assume new construction = code minimum
        # NOT high-performance values
        if year >= 2020:
            return ERA_INSULATION_DEFAULTS["new"]  # Use code minimum, not 2020s high-perf
        elif year < 1970:
            return ERA_INSULATION_DEFAULTS["1960s"]
        elif year < 1980:
            return ERA_INSULATION_DEFAULTS["1970s"]
        elif year < 1990:
            return ERA_INSULATION_DEFAULTS["1980s"]
        elif year < 2000:
            return ERA_INSULATION_DEFAULTS["1990s"]
        elif year < 2010:
            return ERA_INSULATION_DEFAULTS["2000s"]
        elif year < 2020:
            return ERA_INSULATION_DEFAULTS["2010s"]
    
    return {}

def get_construction_factors(zone_config: dict, construction_quality: str, building_era: str = None) -> dict:
    """
    Get construction-specific factors based on zone, quality, and era
    
    Args:
        zone_config: Climate zone configuration
        construction_quality: "tight", "average", or "loose"
        building_era: Optional building era (e.g., "1990s", "2010s")
        
    Returns:
        Dictionary with adjusted factors
    """
    # Check for era-based overrides first
    era_factors = get_era_based_factors(building_era, zone_config)
    if era_factors:
        # Era takes precedence - use era-based values
        factors = {
            "wall_r": era_factors.get("wall_r", zone_config["typical_wall_r"]),
            "roof_r": era_factors.get("roof_r", zone_config["typical_roof_r"]),
            "floor_r": era_factors.get("floor_r", zone_config["typical_floor_r"]),
            "window_u": era_factors.get("window_u", zone_config["typical_window_u"]),
            "infiltration_ach": era_factors.get("infiltration_ach", zone_config["typical_infiltration_ach"])
        }
        # Adjust slightly for construction quality within era
        if construction_quality == "tight":
            factors["infiltration_ach"] *= 0.8
        elif construction_quality == "loose":
            factors["infiltration_ach"] *= 1.2
    else:
        # No era specified - use zone defaults with quality adjustments
        factors = {}
        
        # Adjust R-values based on construction quality
        if construction_quality == "tight":
            # Better than typical for the zone
            factors["wall_r"] = zone_config["typical_wall_r"] * 1.2
            factors["roof_r"] = zone_config["typical_roof_r"] * 1.2
            factors["floor_r"] = zone_config["typical_floor_r"] * 1.2
            factors["window_u"] = zone_config["typical_window_u"] * 0.85
            factors["infiltration_ach"] = zone_config["tight_infiltration_ach"]
        elif construction_quality == "loose":
            # Worse than typical
            factors["wall_r"] = zone_config["typical_wall_r"] * 0.8
            factors["roof_r"] = zone_config["typical_roof_r"] * 0.8
            factors["floor_r"] = zone_config["typical_floor_r"] * 0.8
            factors["window_u"] = zone_config["typical_window_u"] * 1.2
            factors["infiltration_ach"] = zone_config["loose_infiltration_ach"]
        else:  # average
            factors["wall_r"] = zone_config["typical_wall_r"]
            factors["roof_r"] = zone_config["typical_roof_r"]
            factors["floor_r"] = zone_config["typical_floor_r"]
            factors["window_u"] = zone_config["typical_window_u"]
            factors["infiltration_ach"] = zone_config["typical_infiltration_ach"]
    
    # Copy other factors unchanged
    factors["window_shgc"] = zone_config["typical_window_shgc"]
    factors["solar_gain_factor"] = zone_config["solar_gain_factor"]
    factors["roof_solar_factor"] = zone_config["roof_solar_factor"]
    factors["duct_loss_heating"] = zone_config["duct_loss_heating"]
    factors["duct_loss_cooling"] = zone_config["duct_loss_cooling"]
    factors["ventilation_factor"] = zone_config["ventilation_factor"]
    factors["safety_factor_heating"] = zone_config["safety_factor_heating"]
    factors["safety_factor_cooling"] = zone_config["safety_factor_cooling"]
    
    return factors


# Data file paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
ASHRAE_TEMPS_FILE = os.path.join(DATA_DIR, 'ashrae_design_temps.csv')


@lru_cache(maxsize=128)
def get_climate_data_for_zip(zip_code: str) -> Dict[str, Any]:
    """
    Get comprehensive climate data for a ZIP code
    Combines climate zone lookup with ASHRAE design temperatures
    
    Args:
        zip_code: 5-digit US ZIP code
        
    Returns:
        Dict with climate zone, design temperatures, and location info
    """
    result = {
        'zip_code': zip_code,
        'found': False,
        'climate_zone': '4A',  # Default fallback
        'winter_99': 10,       # Default fallback
        'summer_1': 90,        # Default fallback
        'summer_wb': 75,       # Default fallback
    }
    
    # Get climate zone using fast dictionary lookup
    try:
        climate_zone = get_climate_zone_fast(zip_code)
        if climate_zone != '4A':  # Found in database (not fallback)
            result['climate_zone'] = climate_zone
            result['found'] = True
            # Set generic location info since we don't store it in the dict
            result['location'] = 'US'
            result['state'] = 'US'
        else:
            # Check if it's actually zone 4A or just fallback
            prefix = zip_code[:3] if zip_code else ''
            from .zip_climate_zones import ZIP_CLIMATE_ZONES
            if prefix in ZIP_CLIMATE_ZONES:
                result['climate_zone'] = ZIP_CLIMATE_ZONES[prefix]
                result['found'] = True
                result['location'] = 'US'
                result['state'] = 'US'
        
        # Then get ASHRAE design temps - try to match location first, then climate zone
        if result['found'] and os.path.exists(ASHRAE_TEMPS_FILE):
            with open(ASHRAE_TEMPS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # First try exact location match
                for row in rows:
                    if 'location' in result and row['location'] == result['location']:
                        result['winter_99'] = float(row['winter_99'])
                        result['summer_1'] = float(row['summer_1'])
                        result['summer_wb'] = float(row['summer_wb'])
                        result['daily_range'] = float(row['daily_range'])
                        break
                else:
                    # Fallback to climate zone match
                    for row in rows:
                        if row['climate_zone'] == result['climate_zone']:
                            result['winter_99'] = float(row['winter_99'])
                            result['summer_1'] = float(row['summer_1'])
                            result['summer_wb'] = float(row['summer_wb'])
                            result['daily_range'] = float(row['daily_range'])
                            break
        
        # Add zone-specific humidity ratios
        zone_config = get_zone_config(result['climate_zone'])
        result['summer_humidity'] = zone_config.get('outdoor_humidity_ratio_summer', 0.010)
        result['winter_humidity'] = zone_config.get('outdoor_humidity_ratio_winter', 0.003)
        
    except Exception as e:
        # Return defaults on error
        pass
    
    return result


def get_zone_for_zipcode(zip_code: str) -> str:
    """
    Get climate zone for a ZIP code.
    
    Args:
        zip_code: 5-digit US ZIP code
        
    Returns:
        Climate zone string (e.g., "5B")
    """
    climate_data = get_climate_data_for_zip(zip_code)
    return climate_data['climate_zone']


def get_climate_data_for_zone(climate_zone: str, zip_code: str) -> Dict[str, Any]:
    """
    Get climate data for a zone and location.
    
    Args:
        climate_zone: IECC climate zone (e.g., "5B")
        zip_code: ZIP code for design temperatures
        
    Returns:
        Dict with zone config and design temperatures
    """
    # Get full climate data for the ZIP code
    zip_data = get_climate_data_for_zip(zip_code)
    
    # Get zone configuration  
    zone_config = get_zone_config(climate_zone)
    
    # Combine data
    result = {
        'zone': climate_zone,
        'winter_99': zip_data['winter_99'],
        'summer_1': zip_data['summer_1'],
        'summer_wb': zip_data.get('summer_wb', 75),
        'daily_range': zip_data.get('daily_range', 20),
        'location': zip_data.get('location', 'Unknown'),
        'state': zip_data.get('state', 'Unknown'),
        
        # Zone-specific factors
        'typical_wall_r': zone_config['typical_wall_r'],
        'typical_roof_r': zone_config['typical_roof_r'], 
        'typical_floor_r': zone_config['typical_floor_r'],
        'typical_window_u': zone_config['typical_window_u'],
        'typical_infiltration_ach': zone_config['typical_infiltration_ach'],
        'solar_gain_factor': zone_config['solar_gain_factor'],
        'duct_loss_heating': zone_config['duct_loss_heating'],
        'duct_loss_cooling': zone_config['duct_loss_cooling']
    }
    
    return result