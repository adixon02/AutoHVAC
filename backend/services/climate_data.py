"""
Climate Data Service for ACCA Manual J calculations
Provides accurate climate zone and design temperature lookups
"""

import csv
import os
import redis
import json
from typing import Dict, Optional, Tuple, List
from functools import lru_cache
import math

# Redis configuration for caching with fallback
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
    print(f"Climate data service: Redis connected at {redis_url}")
except Exception as e:
    REDIS_AVAILABLE = False
    redis_client = None
    print(f"Climate data service: Redis unavailable ({e}), using in-memory cache only")

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
    
    # Check Redis cache first for production performance
    cache_key = f"climate:{zip_code}"
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                result = json.loads(cached)
                result['cache_hit'] = True
                return result
        except Exception as e:
            print(f"Redis cache read error for {zip_code}: {e}")
    
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
    
    # Mark as cache miss and cache result for 24 hours
    result['cache_hit'] = False
    
    if REDIS_AVAILABLE:
        try:
            # Cache for 24 hours (86400 seconds)
            redis_client.setex(cache_key, 86400, json.dumps(result))
        except Exception as e:
            print(f"Redis cache write error for {zip_code}: {e}")
    
    # Also warm up nearby zip codes for better performance
    if result['found'] and result.get('state_abbr'):
        try:
            _warm_nearby_cache(zip_code, result)
        except Exception as e:
            print(f"Cache warming failed for {zip_code}: {e}")
    
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
            'infiltration_ach': 0.20, # Very tight construction (reduced from 0.25)
        }
    }
    
    return vintage_data.get(vintage, vintage_data['1980-2000'])  # Default to 1980-2000


# Climate zone heating and cooling factors (BTU/hr/sqft base loads)
CLIMATE_ZONE_FACTORS = {
    '1A': {'heating_factor': 14, 'cooling_factor': 35},  # Very Hot-Humid (reduced 7%)
    '2A': {'heating_factor': 22, 'cooling_factor': 30},  # Hot-Humid (reduced 12%)
    '2B': {'heating_factor': 22, 'cooling_factor': 32},  # Hot-Dry (reduced 12%)
    '3A': {'heating_factor': 26, 'cooling_factor': 25},  # Warm-Humid (reduced 13%)
    '3B': {'heating_factor': 26, 'cooling_factor': 27},  # Warm-Dry (reduced 13%)
    '3C': {'heating_factor': 22, 'cooling_factor': 18},  # Warm-Marine (reduced 12%)
    '4A': {'heating_factor': 34, 'cooling_factor': 22},  # Mixed-Humid (reduced 15%)
    '4B': {'heating_factor': 34, 'cooling_factor': 24},  # Mixed-Dry (reduced 15%)
    '4C': {'heating_factor': 30, 'cooling_factor': 15},  # Mixed-Marine (reduced 14%)
    '5A': {'heating_factor': 32, 'cooling_factor': 20},  # Cool-Humid (reduced 20% from 40)
    '5B': {'heating_factor': 30, 'cooling_factor': 22},  # Cool-Dry (reduced 21% from 38)
    '6A': {'heating_factor': 36, 'cooling_factor': 18},  # Cold-Humid (reduced 20% from 45)
    '6B': {'heating_factor': 36, 'cooling_factor': 20},  # Cold-Dry (reduced 20% from 45)
    '7': {'heating_factor': 42, 'cooling_factor': 15},   # Very Cold (reduced 24% from 55)
    '8': {'heating_factor': 49, 'cooling_factor': 12},   # Subarctic (reduced 25% from 65)
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


def _warm_nearby_cache(center_zip: str, center_data: Dict) -> None:
    """
    Warm up cache for nearby zip codes in the same state and climate zone
    This improves performance for subsequent requests in the same area
    """
    if not REDIS_AVAILABLE or not center_data.get('state_abbr'):
        return
    
    state_abbr = center_data['state_abbr']
    climate_zone = center_data.get('climate_zone', '')
    
    # Load zip code data once
    zip_county_data = load_zip_county_data()
    county_climate_data = load_county_climate_data()
    design_temp_data = load_design_temp_data()
    
    # Find nearby zip codes in same state (simple approach - same first 3 digits)
    zip_prefix = center_zip[:3]
    warmed_count = 0
    
    for zip_code, zip_info in zip_county_data.items():
        if (zip_code.startswith(zip_prefix) and 
            zip_info['state_abbr'] == state_abbr and 
            zip_code != center_zip and
            warmed_count < 10):  # Limit warming to avoid overload
            
            cache_key = f"climate:{zip_code}"
            
            # Check if already cached
            try:
                if redis_client.exists(cache_key):
                    continue
            except Exception:
                continue
            
            # Build similar result for nearby zip code
            nearby_result = {
                'zip_code': zip_code,
                'found': True,
                'city': zip_info['city'],
                'state': zip_info['state'],
                'state_abbr': zip_info['state_abbr'],
                'climate_zone': climate_zone,  # Use same climate zone
                'cache_hit': False,
                'pre_warmed': True
            }
            
            # Use same design temps if in same climate zone, otherwise find nearest
            if zip_code in design_temp_data:
                nearby_result.update(design_temp_data[zip_code])
            else:
                # Use center_data temps as approximation for nearby locations
                for key in ['heating_db_99', 'cooling_db_1', 'cooling_wb_1']:
                    if key in center_data:
                        nearby_result[key] = center_data[key]
            
            # Cache the warmed data
            try:
                redis_client.setex(cache_key, 86400, json.dumps(nearby_result))
                warmed_count += 1
            except Exception:
                break


def get_bulk_climate_data(zip_codes: List[str]) -> Dict[str, Dict]:
    """
    Get climate data for multiple zip codes efficiently
    
    Args:
        zip_codes: List of 5-digit zip codes
        
    Returns:
        Dict mapping zip codes to their climate data
    """
    results = {}
    cache_misses = []
    
    # First pass: check cache for all zip codes
    if REDIS_AVAILABLE:
        try:
            pipe = redis_client.pipeline()
            for zip_code in zip_codes:
                cache_key = f"climate:{zip_code.zfill(5)}"
                pipe.get(cache_key)
            
            cached_results = pipe.execute()
            
            for i, cached in enumerate(cached_results):
                zip_code = zip_codes[i].zfill(5)
                if cached:
                    result = json.loads(cached)
                    result['cache_hit'] = True
                    results[zip_code] = result
                else:
                    cache_misses.append(zip_code)
                    
        except Exception as e:
            print(f"Bulk cache read error: {e}")
            cache_misses = [z.zfill(5) for z in zip_codes]
    else:
        cache_misses = [z.zfill(5) for z in zip_codes]
    
    # Second pass: load missing data efficiently
    if cache_misses:
        # Load all data sources once
        zip_county_data = load_zip_county_data()
        county_climate_data = load_county_climate_data()
        design_temp_data = load_design_temp_data()
        
        # Process each cache miss
        for zip_code in cache_misses:
            result = _build_climate_result(
                zip_code, zip_county_data, county_climate_data, design_temp_data
            )
            result['cache_hit'] = False
            results[zip_code] = result
            
            # Cache the result
            if REDIS_AVAILABLE:
                try:
                    cache_key = f"climate:{zip_code}"
                    redis_client.setex(cache_key, 86400, json.dumps(result))
                except Exception:
                    pass
    
    return results


def _build_climate_result(zip_code: str, zip_county_data: Dict, county_climate_data: Dict, design_temp_data: Dict) -> Dict:
    """Build climate result for a single zip code from loaded data sources"""
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
    
    # Get design temperatures
    if zip_code in design_temp_data:
        temp_data = design_temp_data[zip_code]
        result.update(temp_data)
    else:
        # Find nearest weather station by climate zone and state
        nearest_temps = find_nearest_design_temps(result.get('state_abbr'), result.get('climate_zone'))
        if nearest_temps:
            result.update(nearest_temps)
    
    return result