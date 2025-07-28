"""
Climate Data Service for ACCA Manual J calculations
Provides accurate climate zone and design temperature lookups
"""

import csv
import os
import redis
import json
from typing import Dict, Optional, Tuple
from functools import lru_cache
import math

# Redis configuration for caching
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    redis_client = None

# Data file paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
ZIP_COUNTY_FILE = os.path.join(DATA_DIR, 'zip_county_mapping.csv')
COUNTY_CLIMATE_FILE = os.path.join(DATA_DIR, 'county_climate_zones.csv')
ASHRAE_TEMPS_FILE = os.path.join(DATA_DIR, 'ashrae_design_temps.csv')

# Cache for data
_zip_county_cache = {}
_county_climate_cache = {}
_design_temp_cache = {}


@lru_cache(maxsize=1)
def load_zip_county_data() -> Dict[str, Dict]:
    """Load zip code to county mapping data"""
    global _zip_county_cache
    
    if _zip_county_cache:
        return _zip_county_cache
    
    try:
        with open(ZIP_COUNTY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                zip_code = row['zipcode'].zfill(5)  # Ensure 5-digit zip
                _zip_county_cache[zip_code] = {
                    'state': row['state'],
                    'state_abbr': row['state_abbr'],
                    'county': row['county'],
                    'city': row['city'],
                    'state_fips': row['state_fips']
                }
    except FileNotFoundError:
        print(f"Warning: {ZIP_COUNTY_FILE} not found")
    
    return _zip_county_cache


@lru_cache(maxsize=1) 
def load_county_climate_data() -> Dict[str, Dict]:
    """Load county to climate zone mapping data"""
    global _county_climate_cache
    
    if _county_climate_cache:
        return _county_climate_cache
    
    try:
        with open(COUNTY_CLIMATE_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Create key as "STATE_ABBR-COUNTY_NAME"
                key = f"{row['State']}-{row['County Name']}"
                _county_climate_cache[key] = {
                    'iecc_zone': row['IECC Climate Zone'],
                    'iecc_moisture': row['IECC Moisture Regime'],
                    'ba_zone': row['BA Climate Zone'],
                    'state_fips': row['State FIPS'],
                    'county_fips': row['County FIPS']
                }
    except FileNotFoundError:
        print(f"Warning: {COUNTY_CLIMATE_FILE} not found")
    
    return _county_climate_cache


@lru_cache(maxsize=1)
def load_design_temp_data() -> Dict[str, Dict]:
    """Load ASHRAE design temperature data"""
    global _design_temp_cache
    
    if _design_temp_cache:
        return _design_temp_cache
    
    try:
        with open(ASHRAE_TEMPS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                zip_code = row['zip_code'].zfill(5)
                _design_temp_cache[zip_code] = {
                    'city': row['city'],
                    'state': row['state'],
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'climate_zone': row['climate_zone'],
                    'heating_db_99': int(row['heating_db_99']),
                    'heating_db_97_5': int(row['heating_db_97_5']),
                    'cooling_db_0_4': int(row['cooling_db_0_4']),
                    'cooling_db_1': int(row['cooling_db_1']),
                    'cooling_db_2': int(row['cooling_db_2']),
                    'cooling_wb_0_4': int(row['cooling_wb_0_4']),
                    'cooling_wb_1': int(row['cooling_wb_1']),
                    'cooling_wb_2': int(row['cooling_wb_2']),
                    'elevation_ft': int(row['elevation_ft'])
                }
    except FileNotFoundError:
        print(f"Warning: {ASHRAE_TEMPS_FILE} not found")
    
    return _design_temp_cache


def get_climate_data(zip_code: str) -> Dict:
    """
    Get comprehensive climate data for a zip code
    
    Args:
        zip_code: 5-digit US zip code
        
    Returns:
        Dict with climate zone, design temperatures, and location info
    """
    zip_code = zip_code.zfill(5)
    
    # Check Redis cache first
    cache_key = f"climate:{zip_code}"
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
    
    # Load data if not cached
    zip_county_data = load_zip_county_data()
    county_climate_data = load_county_climate_data()
    design_temp_data = load_design_temp_data()
    
    result = {
        'zip_code': zip_code,
        'found': False,
        'climate_zone': '4A',  # Default fallback
        'heating_db_99': 10,   # Default fallback
        'cooling_db_1': 90,    # Default fallback
        'cooling_wb_1': 75,    # Default fallback
    }
    
    # Get county info from zip code
    if zip_code in zip_county_data:
        zip_info = zip_county_data[zip_code]
        result['city'] = zip_info['city']
        result['state'] = zip_info['state']
        result['state_abbr'] = zip_info['state_abbr']
        
        # Get climate zone from county
        county_key = f"{zip_info['state_abbr']}-{zip_info['county']}"
        if county_key in county_climate_data:
            climate_info = county_climate_data[county_key]
            result['climate_zone'] = climate_info['iecc_zone'] + climate_info['iecc_moisture']
            result['ba_climate_zone'] = climate_info['ba_zone']
            result['found'] = True
    
    # Get design temperatures - try exact match first, then find nearest
    if zip_code in design_temp_data:
        temp_data = design_temp_data[zip_code]
        result.update(temp_data)
    else:
        # Find nearest weather station by climate zone and state
        nearest_temps = find_nearest_design_temps(result.get('state_abbr'), result.get('climate_zone'))
        if nearest_temps:
            result.update(nearest_temps)
    
    # Cache result for 24 hours
    if REDIS_AVAILABLE:
        try:
            redis_client.setex(cache_key, 86400, json.dumps(result))
        except:
            pass
    
    return result


def find_nearest_design_temps(state_abbr: str, climate_zone: str) -> Optional[Dict]:
    """
    Find nearest design temperatures for a state and climate zone
    
    Args:
        state_abbr: Two-letter state abbreviation
        climate_zone: IECC climate zone (e.g., '4A')
        
    Returns:
        Dict with design temperature data or None
    """
    design_temp_data = load_design_temp_data()
    
    # First try to find exact state and climate zone match
    for zip_code, data in design_temp_data.items():
        if data['state'] == state_abbr and data['climate_zone'] == climate_zone:
            return {k: v for k, v in data.items() if k not in ['city', 'state', 'zip_code']}
    
    # Fallback to same climate zone in nearby states
    zone_matches = []
    for zip_code, data in design_temp_data.items():
        if data['climate_zone'] == climate_zone:
            zone_matches.append(data)
    
    if zone_matches:
        # Return the first match - could be improved with geographic distance
        return {k: v for k, v in zone_matches[0].items() if k not in ['city', 'state', 'zip_code']}
    
    return None


def get_construction_vintage_values(vintage: str) -> Dict[str, float]:
    """
    Get construction R-values and U-factors by vintage period
    
    Args:
        vintage: Construction vintage ('pre-1980', '1980-2000', '2000-2020', 'current-code')
        
    Returns:
        Dict with R-values and U-factors for different building components
    """
    vintage_data = {
        'pre-1980': {
            'wall_r_value': 7.0,      # R-7 (2x4 with minimal insulation)
            'roof_r_value': 19.0,     # R-19 (6" attic insulation)
            'floor_r_value': 11.0,    # R-11 (3.5" floor insulation)
            'window_u_factor': 0.80,  # Single pane windows
            'window_shgc': 0.70,      # Clear glass
            'infiltration_ach': 0.67, # Loose construction
        },
        '1980-2000': {
            'wall_r_value': 11.0,     # R-11 (2x4 with full insulation)
            'roof_r_value': 30.0,     # R-30 (10" attic insulation)
            'floor_r_value': 19.0,    # R-19 (6" floor insulation)
            'window_u_factor': 0.50,  # Double pane windows
            'window_shgc': 0.60,      # Standard double pane
            'infiltration_ach': 0.50, # Code construction
        },
        '2000-2020': {
            'wall_r_value': 13.0,     # R-13 (2x4 with high-density insulation)
            'roof_r_value': 38.0,     # R-38 (12" attic insulation)
            'floor_r_value': 25.0,    # R-25 (8" floor insulation)
            'window_u_factor': 0.35,  # Low-E double pane
            'window_shgc': 0.35,      # Low-E coatings
            'infiltration_ach': 0.35, # Better sealing
        },
        'current-code': {
            'wall_r_value': 20.0,     # R-20 (2x6 or continuous insulation)
            'roof_r_value': 49.0,     # R-49 (16" attic insulation)
            'floor_r_value': 30.0,    # R-30 (10" floor insulation)
            'window_u_factor': 0.30,  # High-performance windows
            'window_shgc': 0.25,      # High-performance coatings
            'infiltration_ach': 0.25, # Tight construction
        }
    }
    
    return vintage_data.get(vintage, vintage_data['1980-2000'])  # Default to 1980-2000


# Climate zone heating and cooling factors (BTU/hr/sqft base loads)
CLIMATE_ZONE_FACTORS = {
    '1A': {'heating_factor': 15, 'cooling_factor': 35},  # Very Hot-Humid
    '2A': {'heating_factor': 25, 'cooling_factor': 30},  # Hot-Humid
    '2B': {'heating_factor': 25, 'cooling_factor': 32},  # Hot-Dry
    '3A': {'heating_factor': 30, 'cooling_factor': 25},  # Warm-Humid
    '3B': {'heating_factor': 30, 'cooling_factor': 27},  # Warm-Dry
    '3C': {'heating_factor': 25, 'cooling_factor': 18},  # Warm-Marine
    '4A': {'heating_factor': 40, 'cooling_factor': 22},  # Mixed-Humid
    '4B': {'heating_factor': 40, 'cooling_factor': 24},  # Mixed-Dry
    '4C': {'heating_factor': 35, 'cooling_factor': 15},  # Mixed-Marine
    '5A': {'heating_factor': 50, 'cooling_factor': 20},  # Cool-Humid
    '5B': {'heating_factor': 50, 'cooling_factor': 22},  # Cool-Dry
    '6A': {'heating_factor': 60, 'cooling_factor': 18},  # Cold-Humid
    '6B': {'heating_factor': 60, 'cooling_factor': 20},  # Cold-Dry
    '7': {'heating_factor': 70, 'cooling_factor': 15},   # Very Cold
    '8': {'heating_factor': 85, 'cooling_factor': 12},   # Subarctic
}


def get_climate_zone_factors(climate_zone: str) -> Dict[str, float]:
    """Get heating and cooling factors for a climate zone"""
    # Handle zones with moisture regimes (e.g., '4A')
    if climate_zone in CLIMATE_ZONE_FACTORS:
        return CLIMATE_ZONE_FACTORS[climate_zone]
    
    # Try without moisture regime (e.g., '7', '8')
    zone_number = climate_zone.rstrip('ABC')
    if zone_number in CLIMATE_ZONE_FACTORS:
        return CLIMATE_ZONE_FACTORS[zone_number]
    
    # Default fallback
    return CLIMATE_ZONE_FACTORS['4A']