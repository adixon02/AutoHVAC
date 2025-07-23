#!/usr/bin/env python3
"""
Enhanced Climate Database - Professional HVAC Climate Zone & Design Temperature Lookup
Now with comprehensive SQLite database and 27,789+ ZIP codes coverage
"""

import sqlite3
import logging
import requests
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
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
    Enhanced professional climate database with SQLite storage + API fallback
    Provides comprehensive coverage for 27,789+ ZIP codes across the US
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "zip_climate_database.db"
        
        self.db_path = db_path
        self.connection = None
        self.nrel_api_key = os.getenv('NREL_API_KEY')
        
        # Initialize database connection
        self._init_connection()
        
        # Get coverage stats
        stats = self.get_coverage_stats()
        logger.info(f"Climate database loaded: {stats['total_zip_codes']} ZIP codes, "
                   f"{stats['zip_codes_with_climate']} with climate data "
                   f"({stats['climate_coverage_pct']:.1f}% coverage)")
    
    def _init_connection(self):
        """Initialize SQLite database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
            # Verify database exists and has data
            cursor = self.connection.execute("SELECT COUNT(*) as count FROM zip_codes")
            count = cursor.fetchone()['count']
            
            if count == 0:
                logger.error(f"Database at {self.db_path} is empty. Run create_zip_database.py first.")
                raise Exception("Empty database")
                
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_climate_data(self, zip_code: str) -> Dict[str, Any]:
        """
        Get climate data with intelligent fallback strategy:
        1. Local SQLite database (instant, 27,789+ ZIP codes)
        2. API cache (recent external lookups)  
        3. NREL API (live lookup for new ZIP codes)
        4. Regional fallback (safe default based on ZIP patterns)
        """
        
        if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
            logger.warning(f"Invalid ZIP code format: {zip_code}")
            return self._get_regional_fallback(zip_code)
        
        # 1. Try local SQLite database first (comprehensive coverage)
        local_data = self._get_from_local_db(zip_code)
        if local_data:
            logger.info(f"🌡️ Climate data from SQLite DB: {zip_code} -> Zone {local_data.get('zone', 'N/A')}")
            return local_data
        
        # 2. Check API cache for recent external lookups
        cached_data = self._get_from_api_cache(zip_code)
        if cached_data:
            logger.info(f"🌡️ Climate data from API cache: {zip_code}")
            return cached_data
        
        # 3. Try NREL API for new ZIP codes
        if self.nrel_api_key:
            logger.info(f"🌡️ Fetching climate data from NREL API: {zip_code}")
            api_data = self._fetch_from_nrel_api(zip_code)
            if api_data:
                self._save_to_api_cache(zip_code, api_data)
                return api_data
        else:
            logger.info("🌡️ NREL API key not configured, skipping API lookup")
        
        # 4. Fallback to regional default based on ZIP code patterns
        logger.warning(f"🌡️ Using regional fallback for unknown ZIP: {zip_code}")
        return self._get_regional_fallback(zip_code)
    
    def _get_from_local_db(self, zip_code: str) -> Optional[Dict[str, Any]]:
        """Get climate data from local SQLite database"""
        try:
            # First try to get ZIP with complete climate data
            query = """
            SELECT 
                z.zip_code,
                z.city,
                z.state,
                z.state_abbr,
                z.county,
                z.latitude,
                z.longitude,
                c.ashrae_zone,
                c.cbecs_zone,
                c.description,
                c.summer_db,
                c.winter_db,
                c.summer_wb,
                c.winter_wb,
                c.summer_humidity,
                c.winter_humidity,
                c.source,
                c.confidence_score
            FROM zip_codes z
            LEFT JOIN climate_zones c ON z.zip_code = c.zip_code
            WHERE z.zip_code = ?
            """
            
            cursor = self.connection.execute(query, (zip_code,))
            row = cursor.fetchone()
            
            if row:
                # Check if we have climate data
                if row['ashrae_zone'] or row['cbecs_zone']:
                    return {
                        'zone': row['ashrae_zone'] or self._cbecs_to_ashrae(row['cbecs_zone']),
                        'description': row['description'] or f"{row['city']}, {row['state_abbr']} - Climate Zone",
                        'design_temperatures': {
                            'summer_db': row['summer_db'] or self._estimate_summer_db(row['cbecs_zone']),
                            'winter_db': row['winter_db'] or self._estimate_winter_db(row['cbecs_zone']),
                            'summer_wb': row['summer_wb'] or (row['summer_db'] - 15 if row['summer_db'] else 70),
                            'winter_wb': row['winter_wb'] or (row['winter_db'] - 5 if row['winter_db'] else 0)
                        },
                        'humidity': {
                            'summer': row['summer_humidity'] or 50,
                            'winter': row['winter_humidity'] or 60
                        },
                        'county': row['county'] or 'Unknown',
                        'state': row['state_abbr'] or 'Unknown',
                        'city': row['city'],
                        'latitude': row['latitude'],
                        'longitude': row['longitude'],
                        'source': row['source'] or 'Database',
                        'confidence_score': row['confidence_score'] or 0.8
                    }
                else:
                    # We have ZIP info but no climate data - use geographic estimation
                    if row['latitude'] and row['longitude']:
                        estimated_zone = self._estimate_climate_zone_from_lat(row['latitude'])
                        estimated_temps = self._estimate_design_temps_from_location(row['latitude'], row['longitude'])
                        
                        return {
                            'zone': estimated_zone,
                            'description': f"{row['city']}, {row['state_abbr']} - Estimated from coordinates",
                            'design_temperatures': estimated_temps,
                            'humidity': {'summer': 50, 'winter': 60},
                            'county': row['county'] or 'Unknown',
                            'state': row['state_abbr'] or 'Unknown', 
                            'city': row['city'],
                            'latitude': row['latitude'],
                            'longitude': row['longitude'],
                            'source': 'Geographic_Estimation',
                            'confidence_score': 0.6
                        }
                        
        except Exception as e:
            logger.error(f"Database lookup error for {zip_code}: {e}")
        
        return None
    
    def _cbecs_to_ashrae(self, cbecs_zone: str) -> str:
        """Convert CBECS climate zone to approximate ASHRAE zone"""
        if not cbecs_zone:
            return '4A'
            
        # CBECS zones are simplified, map to common ASHRAE zones
        cbecs_mapping = {
            '1': '1A',  # Very Hot
            '2': '2A',  # Hot-Humid  
            '3': '3A',  # Warm-Humid
            '4': '4A',  # Mixed-Humid
            '5': '5A',  # Cool-Humid
            '6': '6A',  # Cold-Humid
            '7': '7A',  # Very Cold
            '8': '8A'   # Subarctic
        }
        
        return cbecs_mapping.get(str(cbecs_zone), '4A')
    
    def _estimate_summer_db(self, cbecs_zone: str) -> int:
        """Estimate summer design temperature from CBECS zone"""
        zone_temps = {
            '1': 96, '2': 95, '3': 92, '4': 90, 
            '5': 88, '6': 85, '7': 82, '8': 78
        }
        return zone_temps.get(str(cbecs_zone), 90)
    
    def _estimate_winter_db(self, cbecs_zone: str) -> int:
        """Estimate winter design temperature from CBECS zone"""
        zone_temps = {
            '1': 40, '2': 30, '3': 25, '4': 15,
            '5': 5, '6': -5, '7': -15, '8': -25
        }
        return zone_temps.get(str(cbecs_zone), 15)
    
    def _get_from_api_cache(self, zip_code: str) -> Optional[Dict[str, Any]]:
        """Get cached API response from database"""
        try:
            cursor = self.connection.execute("""
            SELECT response_data, last_updated 
            FROM api_cache 
            WHERE zip_code = ? 
            AND datetime(last_updated, '+30 days') > datetime('now')
            """, (zip_code,))
            
            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row['response_data'])
                
        except Exception as e:
            logger.error(f"API cache lookup error for {zip_code}: {e}")
        
        return None
    
    def _save_to_api_cache(self, zip_code: str, data: Dict[str, Any]):
        """Save API response to database cache"""
        try:
            import json
            self.connection.execute("""
            INSERT OR REPLACE INTO api_cache (zip_code, api_source, response_data)
            VALUES (?, ?, ?)
            """, (zip_code, 'NREL_API', json.dumps(data)))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to cache API response for {zip_code}: {e}")
    
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
        
        # Estimate climate zone based on latitude
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
            'longitude': lon,
            'confidence_score': 0.7
        }
    
    def _estimate_climate_zone_from_lat(self, lat: float) -> str:
        """Estimate climate zone from latitude (rough approximation)"""
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
        
        # Refined estimates considering both latitude and longitude
        if lat >= 48:  # Northern tier
            summer_db = 85 if lon > -100 else 82  # Drier west vs humid east
            winter_db = -5 if lon > -100 else -10
        elif lat >= 45:  # North
            summer_db = 88 if lon > -100 else 85
            winter_db = 5 if lon > -100 else 0
        elif lat >= 40:  # Middle
            summer_db = 92 if lon > -100 else 89
            winter_db = 15 if lon > -100 else 10
        elif lat >= 35:  # South
            summer_db = 95 if lon > -100 else 92
            winter_db = 25 if lon > -100 else 20
        else:  # Deep South
            summer_db = 96
            winter_db = 35
            
        return {
            'summer_db': summer_db,
            'winter_db': winter_db,
            'summer_wb': summer_db - 15,  # Rough wet bulb estimate
            'winter_wb': winter_db - 5
        }
    
    def _get_regional_fallback(self, zip_code: str) -> Dict[str, Any]:
        """Provide safe regional fallback based on ZIP code patterns"""
        
        if not zip_code or not zip_code.isdigit():
            zip_prefix = "99"  # Default to WA
        else:
            zip_prefix = zip_code[:2]
        
        # Enhanced regional fallbacks based on ZIP code prefixes
        regional_data = {
            # Washington State (98xxx, 99xxx)
            '98': {'zone': '4C', 'design_temperatures': {'summer_db': 83, 'winter_db': 28}, 'state': 'WA'},
            '99': {'zone': '6B', 'design_temperatures': {'summer_db': 89, 'winter_db': 5}, 'state': 'WA'},
            
            # California (90xxx-96xxx)
            '90': {'zone': '3B', 'design_temperatures': {'summer_db': 92, 'winter_db': 45}, 'state': 'CA'},
            '91': {'zone': '3B', 'design_temperatures': {'summer_db': 95, 'winter_db': 40}, 'state': 'CA'},
            '92': {'zone': '3B', 'design_temperatures': {'summer_db': 88, 'winter_db': 45}, 'state': 'CA'},
            '93': {'zone': '3B', 'design_temperatures': {'summer_db': 95, 'winter_db': 35}, 'state': 'CA'},
            '94': {'zone': '3C', 'design_temperatures': {'summer_db': 80, 'winter_db': 38}, 'state': 'CA'},
            '95': {'zone': '3B', 'design_temperatures': {'summer_db': 98, 'winter_db': 32}, 'state': 'CA'},
            '96': {'zone': '5B', 'design_temperatures': {'summer_db': 85, 'winter_db': 15}, 'state': 'CA'},
            
            # Texas (75xxx-79xxx)
            '75': {'zone': '3A', 'design_temperatures': {'summer_db': 100, 'winter_db': 22}, 'state': 'TX'},
            '76': {'zone': '3A', 'design_temperatures': {'summer_db': 102, 'winter_db': 20}, 'state': 'TX'},
            '77': {'zone': '2A', 'design_temperatures': {'summer_db': 96, 'winter_db': 32}, 'state': 'TX'},
            '78': {'zone': '2A', 'design_temperatures': {'summer_db': 98, 'winter_db': 28}, 'state': 'TX'},
            '79': {'zone': '3B', 'design_temperatures': {'summer_db': 105, 'winter_db': 18}, 'state': 'TX'},
            
            # Florida (32xxx-34xxx)
            '32': {'zone': '2A', 'design_temperatures': {'summer_db': 92, 'winter_db': 35}, 'state': 'FL'},
            '33': {'zone': '1A', 'design_temperatures': {'summer_db': 91, 'winter_db': 45}, 'state': 'FL'},
            '34': {'zone': '1A', 'design_temperatures': {'summer_db': 92, 'winter_db': 50}, 'state': 'FL'},
            
            # New York (10xxx-14xxx)
            '10': {'zone': '4A', 'design_temperatures': {'summer_db': 85, 'winter_db': 15}, 'state': 'NY'},
            '11': {'zone': '4A', 'design_temperatures': {'summer_db': 85, 'winter_db': 15}, 'state': 'NY'},
            '12': {'zone': '5A', 'design_temperatures': {'summer_db': 83, 'winter_db': 5}, 'state': 'NY'},
            '13': {'zone': '5A', 'design_temperatures': {'summer_db': 83, 'winter_db': 0}, 'state': 'NY'},
            '14': {'zone': '6A', 'design_temperatures': {'summer_db': 80, 'winter_db': -5}, 'state': 'NY'},
            
            # Idaho (83xxx)
            '83': {'zone': '6B', 'design_temperatures': {'summer_db': 89, 'winter_db': 3}, 'state': 'ID'},
            
            # Oregon (97xxx)
            '97': {'zone': '4C', 'design_temperatures': {'summer_db': 85, 'winter_db': 25}, 'state': 'OR'},
            
            # Montana (59xxx)
            '59': {'zone': '6B', 'design_temperatures': {'summer_db': 87, 'winter_db': -15}, 'state': 'MT'},
            
            # Colorado (80xxx-81xxx)
            '80': {'zone': '5B', 'design_temperatures': {'summer_db': 91, 'winter_db': -2}, 'state': 'CO'},
            '81': {'zone': '6B', 'design_temperatures': {'summer_db': 82, 'winter_db': -8}, 'state': 'CO'},
        }
        
        fallback = regional_data.get(zip_prefix, {
            'zone': '4A',
            'design_temperatures': {'summer_db': 90, 'winter_db': 20},
            'state': 'Unknown'
        })
        
        # Add wet bulb estimates
        design_temps = fallback['design_temperatures'].copy()
        design_temps['summer_wb'] = design_temps['summer_db'] - 15
        design_temps['winter_wb'] = design_temps['winter_db'] - 5
        
        return {
            'zone': fallback['zone'],
            'description': f"Regional fallback for {fallback['state']}",
            'design_temperatures': design_temps,
            'humidity': {'summer': 50, 'winter': 60},
            'county': 'Unknown',
            'state': fallback['state'],
            'source': 'Regional_Fallback',
            'confidence_score': 0.5
        }
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get comprehensive database coverage statistics"""
        try:
            stats = {}
            
            # Total ZIP codes
            cursor = self.connection.execute("SELECT COUNT(*) as count FROM zip_codes")
            stats['total_zip_codes'] = cursor.fetchone()['count']
            
            # ZIP codes with county info
            cursor = self.connection.execute("SELECT COUNT(*) as count FROM zip_codes WHERE county IS NOT NULL")
            stats['zip_codes_with_county'] = cursor.fetchone()['count']
            
            # ZIP codes with climate data
            cursor = self.connection.execute("SELECT COUNT(*) as count FROM climate_zones")
            stats['zip_codes_with_climate'] = cursor.fetchone()['count']
            
            # Calculate coverage percentage
            if stats['total_zip_codes'] > 0:
                stats['climate_coverage_pct'] = (stats['zip_codes_with_climate'] / stats['total_zip_codes']) * 100
            else:
                stats['climate_coverage_pct'] = 0
            
            # Climate zones by source
            cursor = self.connection.execute("SELECT source, COUNT(*) as count FROM climate_zones GROUP BY source")
            stats['climate_data_by_source'] = dict(cursor.fetchall())
            
            # Top states by coverage
            cursor = self.connection.execute("""
            SELECT z.state_abbr, 
                   COUNT(*) as total_zips,
                   COUNT(c.zip_code) as zips_with_climate,
                   ROUND(COUNT(c.zip_code) * 100.0 / COUNT(*), 1) as coverage_pct
            FROM zip_codes z
            LEFT JOIN climate_zones c ON z.zip_code = c.zip_code
            WHERE z.state_abbr IS NOT NULL
            GROUP BY z.state_abbr
            ORDER BY total_zips DESC
            LIMIT 15
            """)
            stats['top_states_coverage'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting coverage stats: {e}")
            return {'error': str(e)}
    
    def search_zip_codes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search ZIP codes by city, state, or ZIP code"""
        try:
            # Search by ZIP code, city, or state
            search_query = f"%{query}%"
            cursor = self.connection.execute("""
            SELECT z.zip_code, z.city, z.state_abbr, z.county, 
                   c.ashrae_zone as climate_zone
            FROM zip_codes z
            LEFT JOIN climate_zones c ON z.zip_code = c.zip_code
            WHERE z.zip_code LIKE ? 
               OR z.city LIKE ? 
               OR z.state_abbr LIKE ?
               OR z.county LIKE ?
            ORDER BY 
                CASE WHEN z.zip_code LIKE ? THEN 1 ELSE 2 END,
                z.city
            LIMIT ?
            """, (search_query, search_query, search_query, search_query, f"{query}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def add_zip_codes(self, new_data: Dict[str, Dict[str, Any]]):
        """Add new ZIP codes to the database (legacy compatibility)"""
        logger.info("add_zip_codes called - this method is deprecated in SQLite version")
        logger.info("Use the database migration script instead")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global instance for easy importing
climate_db = ClimateDatabase()

if __name__ == "__main__":
    # Test the enhanced climate database
    db = ClimateDatabase()
    
    test_zips = ["99019", "10001", "90210", "33101", "60601", "12345", "83814"]
    
    print("🌡️ Testing Enhanced Climate Database")
    print("=" * 50)
    
    for zip_code in test_zips:
        print(f"\n🔍 Testing ZIP: {zip_code}")
        result = db.get_climate_data(zip_code)
        print(f"  Zone: {result['zone']}")
        print(f"  City: {result.get('city', 'N/A')}")
        print(f"  State: {result['state']}")
        print(f"  Summer DB: {result['design_temperatures']['summer_db']}°F")
        print(f"  Winter DB: {result['design_temperatures']['winter_db']}°F")
        print(f"  Source: {result['source']}")
        print(f"  Confidence: {result.get('confidence_score', 'N/A')}")
    
    # Show coverage statistics
    print(f"\n📊 Database Coverage Statistics")
    print("=" * 50)
    stats = db.get_coverage_stats()
    print(f"Total ZIP codes: {stats['total_zip_codes']:,}")
    print(f"ZIP codes with climate data: {stats['zip_codes_with_climate']:,}")
    print(f"Climate coverage: {stats['climate_coverage_pct']:.1f}%")
    print(f"Data sources: {stats['climate_data_by_source']}")
    
    db.close()