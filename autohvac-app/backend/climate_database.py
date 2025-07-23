#!/usr/bin/env python3
"""
Climate Database - Professional HVAC Climate Zone & Design Temperature Lookup
Provides accurate ASHRAE climate data for Manual J calculations
"""

import json
import logging
import requests
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ClimateData:
    """Climate data structure matching ASHRAE standards"""
    zip_code: str
    zone: str  # ASHRAE climate zone (1A, 2A, 3A, etc.)
    description: str  # Climate description
    design_temperatures: Dict[str, int]  # summer_db, winter_db
    humidity: Dict[str, int]  # summer, winter relative humidity
    county: str
    state: str
    source: str = "ASHRAE_90.1_2019"

class ClimateDatabase:
    """
    Professional climate database with local storage + API fallback
    Optimized for HVAC contractor workflows
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "climate_zones.json"
        
        self.db_path = db_path
        self.data = self._load_database()
        self.api_cache = {}  # Cache API responses to avoid repeated calls
        self.nrel_api_key = os.getenv('NREL_API_KEY')
        
        logger.info(f"Climate database loaded: {len(self.data)} ZIP codes")
    
    def _load_database(self) -> Dict[str, Dict[str, Any]]:
        """Load climate database from JSON file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading climate database: {e}")
                return {}
        else:
            logger.warning(f"Climate database not found at {self.db_path}, creating empty database")
            return {}
    
    def get_climate_data(self, zip_code: str) -> Dict[str, Any]:
        """
        Get climate data with intelligent fallback strategy:
        1. Local database (instant)
        2. API cache (recent lookups)
        3. NREL API (live lookup)
        4. Regional fallback (safe default)
        """
        
        if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
            logger.warning(f"Invalid ZIP code format: {zip_code}")
            return self._get_regional_fallback(zip_code)
        
        # 1. Try local database first (fastest)
        if zip_code in self.data:
            logger.info(f"🌡️ Climate data from local DB: {zip_code} -> Zone {self.data[zip_code]['zone']}")
            return self.data[zip_code]
        
        # 2. Check API cache for recent lookups
        if zip_code in self.api_cache:
            logger.info(f"🌡️ Climate data from cache: {zip_code}")
            return self.api_cache[zip_code]
        
        # 3. Try NREL API for new ZIP codes
        if self.nrel_api_key:
            logger.info(f"🌡️ Fetching climate data from NREL API: {zip_code}")
            api_data = self._fetch_from_nrel_api(zip_code)
            if api_data:
                self.api_cache[zip_code] = api_data
                # Consider adding to permanent database
                self._maybe_add_to_database(zip_code, api_data)
                return api_data
        else:
            logger.info("🌡️ NREL API key not configured, skipping API lookup")
        
        # 4. Fallback to regional default based on ZIP code patterns
        logger.warning(f"🌡️ Using regional fallback for unknown ZIP: {zip_code}")
        return self._get_regional_fallback(zip_code)
    
    def _fetch_from_nrel_api(self, zip_code: str) -> Optional[Dict[str, Any]]:
        """Fetch climate data from NREL API"""
        try:
            # NREL PVWatts API provides location data
            url = "https://developer.nrel.gov/api/pvwatts/v6.json"
            params = {
                'api_key': self.nrel_api_key,
                'address': zip_code,
                'system_capacity': 1,  # Dummy value
                'module_type': 1,
                'losses': 10,
                'array_type': 1,
                'tilt': 20,
                'azimuth': 180
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'outputs' in data and 'address' in data['inputs']:
                    return self._convert_nrel_to_climate_data(data, zip_code)
            else:
                logger.warning(f"NREL API error {response.status_code} for ZIP {zip_code}")
                
        except Exception as e:
            logger.error(f"NREL API call failed for {zip_code}: {e}")
        
        return None
    
    def _convert_nrel_to_climate_data(self, nrel_data: Dict[str, Any], zip_code: str) -> Dict[str, Any]:
        """Convert NREL API response to our climate data format"""
        
        # Extract location info
        lat = nrel_data['inputs'].get('lat', 0)
        lon = nrel_data['inputs'].get('lon', 0)
        address = nrel_data['inputs'].get('address', '')
        
        # Estimate climate zone based on latitude (rough approximation)
        climate_zone = self._estimate_climate_zone_from_lat(lat)
        
        # Estimate design temperatures based on location
        design_temps = self._estimate_design_temps_from_location(lat, lon)
        
        return {
            'zone': climate_zone,
            'description': f'Estimated from location ({lat:.2f}, {lon:.2f})',
            'design_temperatures': design_temps,
            'humidity': {'summer': 50, 'winter': 60},  # Conservative estimates
            'county': 'Unknown',
            'state': address.split(',')[-2].strip() if ',' in address else 'Unknown',
            'source': 'NREL_API_Estimated',
            'latitude': lat,
            'longitude': lon
        }
    
    def _estimate_climate_zone_from_lat(self, lat: float) -> str:
        """Rough climate zone estimation from latitude"""
        if lat >= 48:
            return '6B'  # Cold
        elif lat >= 43:
            return '5B'  # Cool
        elif lat >= 39:
            return '4A'  # Mixed-Humid
        elif lat >= 35:
            return '3A'  # Warm-Humid  
        elif lat >= 26:
            return '2A'  # Hot-Humid
        else:
            return '1A'  # Very Hot-Humid
    
    def _estimate_design_temps_from_location(self, lat: float, lon: float) -> Dict[str, int]:
        """Estimate design temperatures from geographic location"""
        
        # Very rough estimates - real implementation would use NOAA data
        if lat >= 48:  # Northern tier
            return {'summer_db': 85, 'winter_db': -5}
        elif lat >= 45:  # North
            return {'summer_db': 88, 'winter_db': 5}
        elif lat >= 40:  # Middle
            return {'summer_db': 92, 'winter_db': 15}
        elif lat >= 35:  # South
            return {'summer_db': 95, 'winter_db': 25}
        else:  # Deep South
            return {'summer_db': 96, 'winter_db': 35}
    
    def _get_regional_fallback(self, zip_code: str) -> Dict[str, Any]:
        """Provide safe regional fallback based on ZIP code patterns"""
        
        if not zip_code or not zip_code.isdigit():
            zip_prefix = "99"  # Default to WA
        else:
            zip_prefix = zip_code[:2]
        
        # Regional fallbacks based on ZIP code prefixes
        regional_data = {
            # Washington State (98xxx, 99xxx)
            '98': {'zone': '4C', 'design_temperatures': {'summer_db': 83, 'winter_db': 28}, 'state': 'WA'},
            '99': {'zone': '6B', 'design_temperatures': {'summer_db': 89, 'winter_db': 5}, 'state': 'WA'},
            
            # Idaho (83xxx)
            '83': {'zone': '6B', 'design_temperatures': {'summer_db': 89, 'winter_db': 3}, 'state': 'ID'},
            
            # Oregon (97xxx)
            '97': {'zone': '4C', 'design_temperatures': {'summer_db': 85, 'winter_db': 25}, 'state': 'OR'},
            
            # Montana (59xxx)
            '59': {'zone': '6B', 'design_temperatures': {'summer_db': 87, 'winter_db': -15}, 'state': 'MT'},
        }
        
        fallback = regional_data.get(zip_prefix, {
            'zone': '4A',
            'design_temperatures': {'summer_db': 90, 'winter_db': 20},
            'state': 'Unknown'
        })
        
        return {
            'zone': fallback['zone'],
            'description': f"Regional fallback for {fallback['state']}",
            'design_temperatures': fallback['design_temperatures'],
            'humidity': {'summer': 50, 'winter': 60},
            'county': 'Unknown',
            'state': fallback['state'],
            'source': 'Regional_Fallback'
        }
    
    def _maybe_add_to_database(self, zip_code: str, climate_data: Dict[str, Any]):
        """Consider adding API lookup to permanent database"""
        # Only add high-confidence data to permanent database
        if climate_data.get('source') == 'NREL_API_Estimated':
            # Don't add estimated data to permanent database
            return
        
        # Could implement logic to batch-save frequently requested ZIP codes
        logger.info(f"Consider adding {zip_code} to permanent database")
    
    def add_zip_codes(self, new_data: Dict[str, Dict[str, Any]]):
        """Add new ZIP codes to the database"""
        self.data.update(new_data)
        self._save_database()
        logger.info(f"Added {len(new_data)} ZIP codes to database")
    
    def _save_database(self):
        """Save database to JSON file"""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Climate database saved: {len(self.data)} ZIP codes")
        except Exception as e:
            logger.error(f"Error saving climate database: {e}")
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get database coverage statistics"""
        states = {}
        zones = {}
        
        for zip_code, data in self.data.items():
            state = data.get('state', 'Unknown')
            zone = data.get('zone', 'Unknown')
            
            states[state] = states.get(state, 0) + 1
            zones[zone] = zones.get(zone, 0) + 1
        
        return {
            'total_zip_codes': len(self.data),
            'states_covered': len(states),
            'climate_zones': zones,
            'state_breakdown': states
        }


# Global instance for easy importing
climate_db = ClimateDatabase()

if __name__ == "__main__":
    # Test the climate database
    db = ClimateDatabase()
    
    test_zips = ["99019", "83814", "98188", "12345"]  # Mix of known and unknown
    
    for zip_code in test_zips:
        print(f"\n🌡️ Testing ZIP: {zip_code}")
        result = db.get_climate_data(zip_code)
        print(f"Zone: {result['zone']}")
        print(f"Design Temps: {result['design_temperatures']}")
        print(f"Source: {result['source']}")
    
    print(f"\n📊 Coverage Stats:")
    stats = db.get_coverage_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")