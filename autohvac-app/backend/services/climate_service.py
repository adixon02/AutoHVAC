#!/usr/bin/env python3
"""
Climate Data Service with High-Performance Caching
Optimized climate zone lookup with Redis-like caching behavior
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import hashlib
from dataclasses import dataclass, asdict
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class ClimateData:
    """Climate data structure"""
    zip_code: str
    zone: str
    heating_degree_days: int
    cooling_degree_days: int
    design_temperatures: Dict[str, float]
    humidity: Dict[str, float]
    county: str = ""
    state: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    elevation: int = 0
    cached_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.cached_at:
            data['cached_at'] = self.cached_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClimateData':
        if 'cached_at' in data and isinstance(data['cached_at'], str):
            data['cached_at'] = datetime.fromisoformat(data['cached_at'])
        return cls(**data)

class ClimateService:
    """
    High-performance climate data service with intelligent caching
    """
    
    def __init__(self, 
                 db_path: str = "zip_climate_database.db",
                 cache_ttl_hours: int = 168,  # 7 days
                 max_cache_size: int = 10000):
        
        self.db_path = Path(db_path)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.max_cache_size = max_cache_size
        
        # In-memory cache with LRU behavior
        self._memory_cache: Dict[str, ClimateData] = {}
        self._cache_access_times: Dict[str, datetime] = {}
        
        # Database connection pool (SQLite doesn't support true pooling, but we can optimize)
        self._db_connections: Dict[str, sqlite3.Connection] = {}
        
        # Performance statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'database_queries': 0,
            'total_requests': 0,
            'avg_response_time_ms': 0.0
        }
        
        # Initialize database connection
        self._init_database()
        
        logger.info(f"ClimateService initialized with cache TTL: {cache_ttl_hours}h, max size: {max_cache_size}")
    
    def _init_database(self):
        """Initialize database connection and create indexes for performance"""
        try:
            if not self.db_path.exists():
                logger.warning(f"Climate database not found at {self.db_path}")
                return
            
            # Test connection and create performance indexes
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_zip_code ON climate_data(zip_code)",
                "CREATE INDEX IF NOT EXISTS idx_zone ON climate_data(zone)",
                "CREATE INDEX IF NOT EXISTS idx_state_county ON climate_data(state, county)"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                except sqlite3.Error:
                    pass  # Index might already exist
            
            conn.commit()
            self._db_connections['main'] = conn
            
            logger.info("Climate database initialized with performance indexes")
            
        except Exception as e:
            logger.error(f"Failed to initialize climate database: {str(e)}")
    
    async def get_climate_data(self, zip_code: str) -> Optional[ClimateData]:
        """
        Get climate data for a ZIP code with intelligent caching
        
        Args:
            zip_code: 5-digit ZIP code
            
        Returns:
            ClimateData object or None if not found
        """
        import time
        start_time = time.time()
        
        try:
            self.stats['total_requests'] += 1
            
            # Normalize ZIP code
            zip_code = str(zip_code).zfill(5)
            
            # Check memory cache first
            cached_data = self._get_from_cache(zip_code)
            if cached_data:
                self.stats['cache_hits'] += 1
                self._update_response_time(start_time)
                return cached_data
            
            # Cache miss - query database
            self.stats['cache_misses'] += 1
            self.stats['database_queries'] += 1
            
            climate_data = await self._query_database(zip_code)
            
            if climate_data:
                # Cache the result
                self._add_to_cache(zip_code, climate_data)
                
            self._update_response_time(start_time)
            return climate_data
            
        except Exception as e:
            logger.error(f"Climate data lookup failed for ZIP {zip_code}: {str(e)}")
            return None
    
    async def get_climate_data_batch(self, zip_codes: List[str]) -> Dict[str, Optional[ClimateData]]:
        """
        Get climate data for multiple ZIP codes efficiently
        
        Args:
            zip_codes: List of ZIP codes
            
        Returns:
            Dict mapping ZIP codes to ClimateData objects
        """
        results = {}
        
        # Normalize ZIP codes
        zip_codes = [str(zip_code).zfill(5) for zip_code in zip_codes]
        
        # Check cache for all ZIP codes
        uncached_zips = []
        for zip_code in zip_codes:
            cached_data = self._get_from_cache(zip_code)
            if cached_data:
                results[zip_code] = cached_data
                self.stats['cache_hits'] += 1
            else:
                uncached_zips.append(zip_code)
                self.stats['cache_misses'] += 1
        
        # Batch query for uncached ZIP codes
        if uncached_zips:
            batch_results = await self._query_database_batch(uncached_zips)
            
            for zip_code, climate_data in batch_results.items():
                if climate_data:
                    self._add_to_cache(zip_code, climate_data)
                results[zip_code] = climate_data
        
        self.stats['total_requests'] += len(zip_codes)
        return results
    
    async def search_by_location(self, state: str, county: str = None) -> List[ClimateData]:
        """
        Search for climate data by geographic location
        
        Args:
            state: State abbreviation (e.g., 'CA')
            county: County name (optional)
            
        Returns:
            List of ClimateData objects
        """
        try:
            conn = self._get_db_connection()
            
            if county:
                query = """
                SELECT * FROM climate_data 
                WHERE state = ? AND county LIKE ?
                ORDER BY zip_code
                LIMIT 100
                """
                params = (state.upper(), f"%{county}%")
            else:
                query = """
                SELECT * FROM climate_data 
                WHERE state = ?
                ORDER BY zip_code
                LIMIT 100
                """
                params = (state.upper(),)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                climate_data = self._row_to_climate_data(row)
                if climate_data:
                    results.append(climate_data)
            
            self.stats['database_queries'] += 1
            return results
            
        except Exception as e:
            logger.error(f"Location search failed for {state}/{county}: {str(e)}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        cache_hit_rate = 0.0
        if self.stats['total_requests'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / self.stats['total_requests']
        
        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self._memory_cache),
            'cache_max_size': self.max_cache_size,
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self._memory_cache.clear()
        self._cache_access_times.clear()
        logger.info("Climate data cache cleared")
    
    def preload_common_zips(self, zip_codes: List[str]):
        """Preload commonly used ZIP codes into cache"""
        async def _preload():
            await self.get_climate_data_batch(zip_codes)
        
        asyncio.create_task(_preload())
        logger.info(f"Preloading {len(zip_codes)} ZIP codes into cache")
    
    # Private methods
    
    def _get_from_cache(self, zip_code: str) -> Optional[ClimateData]:
        """Get data from memory cache if valid"""
        if zip_code not in self._memory_cache:
            return None
        
        # Check if cache entry is still valid
        cached_data = self._memory_cache[zip_code]
        if cached_data.cached_at and datetime.now() - cached_data.cached_at > self.cache_ttl:
            # Remove expired entry
            del self._memory_cache[zip_code]
            if zip_code in self._cache_access_times:
                del self._cache_access_times[zip_code]
            return None
        
        # Update access time for LRU
        self._cache_access_times[zip_code] = datetime.now()
        return cached_data
    
    def _add_to_cache(self, zip_code: str, climate_data: ClimateData):
        """Add data to memory cache with LRU eviction"""
        # Check if cache is full
        if len(self._memory_cache) >= self.max_cache_size:
            self._evict_lru_entries()
        
        # Add new entry
        climate_data.cached_at = datetime.now()
        self._memory_cache[zip_code] = climate_data
        self._cache_access_times[zip_code] = datetime.now()
    
    def _evict_lru_entries(self, evict_count: int = None):
        """Evict least recently used entries"""
        if not evict_count:
            evict_count = max(1, self.max_cache_size // 10)  # Evict 10% of cache
        
        # Sort by access time and remove oldest entries
        sorted_items = sorted(
            self._cache_access_times.items(),
            key=lambda x: x[1]
        )
        
        for zip_code, _ in sorted_items[:evict_count]:
            if zip_code in self._memory_cache:
                del self._memory_cache[zip_code]
            if zip_code in self._cache_access_times:
                del self._cache_access_times[zip_code]
    
    async def _query_database(self, zip_code: str) -> Optional[ClimateData]:
        """Query database for single ZIP code"""
        try:
            # Run database query in thread pool to avoid blocking
            return await asyncio.to_thread(self._query_database_sync, zip_code)
        except Exception as e:
            logger.error(f"Database query failed for ZIP {zip_code}: {str(e)}")
            return None
    
    def _query_database_sync(self, zip_code: str) -> Optional[ClimateData]:
        """Synchronous database query"""
        try:
            conn = self._get_db_connection()
            
            query = """
            SELECT * FROM climate_data 
            WHERE zip_code = ?
            LIMIT 1
            """
            
            cursor = conn.execute(query, (zip_code,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_climate_data(row)
            
            return None
            
        except Exception as e:
            logger.error(f"Sync database query failed for ZIP {zip_code}: {str(e)}")
            return None
    
    async def _query_database_batch(self, zip_codes: List[str]) -> Dict[str, Optional[ClimateData]]:
        """Query database for multiple ZIP codes"""
        try:
            return await asyncio.to_thread(self._query_database_batch_sync, zip_codes)
        except Exception as e:
            logger.error(f"Batch database query failed: {str(e)}")
            return {zip_code: None for zip_code in zip_codes}
    
    def _query_database_batch_sync(self, zip_codes: List[str]) -> Dict[str, Optional[ClimateData]]:
        """Synchronous batch database query"""
        results = {}
        
        try:
            conn = self._get_db_connection()
            
            # Use IN clause for batch query
            placeholders = ','.join('?' * len(zip_codes))
            query = f"""
            SELECT * FROM climate_data 
            WHERE zip_code IN ({placeholders})
            """
            
            cursor = conn.execute(query, zip_codes)
            rows = cursor.fetchall()
            
            # Create results dict
            found_zips = set()
            for row in rows:
                climate_data = self._row_to_climate_data(row)
                if climate_data:
                    results[climate_data.zip_code] = climate_data
                    found_zips.add(climate_data.zip_code)
            
            # Add None for not found ZIP codes
            for zip_code in zip_codes:
                if zip_code not in found_zips:
                    results[zip_code] = None
            
            self.stats['database_queries'] += 1
            return results
            
        except Exception as e:
            logger.error(f"Sync batch database query failed: {str(e)}")
            return {zip_code: None for zip_code in zip_codes}
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection (reuse existing or create new)"""
        if 'main' in self._db_connections:
            return self._db_connections['main']
        
        # Create new connection if needed
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self._db_connections['main'] = conn
        return conn
    
    def _row_to_climate_data(self, row) -> Optional[ClimateData]:
        """Convert database row to ClimateData object"""
        try:
            # Parse design temperatures and humidity from JSON or individual columns
            design_temps = {}
            humidity = {}
            
            if 'design_temperatures' in row.keys():
                design_temps = json.loads(row['design_temperatures'] or '{}')
            else:
                # Fallback to individual columns
                design_temps = {
                    'summer_dry': row.get('summer_dry_bulb', 95.0),
                    'winter_dry': row.get('winter_dry_bulb', 10.0)
                }
            
            if 'humidity' in row.keys():
                humidity = json.loads(row['humidity'] or '{}')
            else:
                # Fallback values
                humidity = {
                    'summer': row.get('summer_humidity', 60.0),
                    'winter': row.get('winter_humidity', 30.0)
                }
            
            return ClimateData(
                zip_code=row['zip_code'],
                zone=row.get('zone', 'Unknown'),
                heating_degree_days=row.get('heating_degree_days', 3000),
                cooling_degree_days=row.get('cooling_degree_days', 1000),
                design_temperatures=design_temps,
                humidity=humidity,
                county=row.get('county', ''),
                state=row.get('state', ''),
                latitude=row.get('latitude', 0.0),
                longitude=row.get('longitude', 0.0),
                elevation=row.get('elevation', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to convert database row: {str(e)}")
            return None
    
    def _update_response_time(self, start_time: float):
        """Update average response time statistics"""
        import time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Update running average
        prev_avg = self.stats['avg_response_time_ms']
        n = self.stats['total_requests']
        self.stats['avg_response_time_ms'] = (prev_avg * (n - 1) + response_time_ms) / n

# Global service instance
_global_climate_service: Optional[ClimateService] = None

def get_climate_service() -> ClimateService:
    """Get global climate service instance (singleton)"""
    global _global_climate_service
    if _global_climate_service is None:
        _global_climate_service = ClimateService()
    return _global_climate_service

# Convenience functions for backward compatibility
@lru_cache(maxsize=1000)
def get_climate_zone_sync(zip_code: str) -> Optional[Dict[str, Any]]:
    """Synchronous climate zone lookup with LRU cache"""
    service = get_climate_service()
    # For sync compatibility, we need to run async function in thread
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        climate_data = loop.run_until_complete(service.get_climate_data(zip_code))
        return climate_data.to_dict() if climate_data else None
    except:
        # Fallback for when no event loop is running
        return asyncio.run(service.get_climate_data(zip_code))

async def get_climate_zone(zip_code: str) -> Optional[Dict[str, Any]]:
    """Async climate zone lookup"""
    service = get_climate_service()
    climate_data = await service.get_climate_data(zip_code)
    return climate_data.to_dict() if climate_data else None

# Default climate zone for fallback
default_climate_zone = {
    "zip_code": "00000",
    "zone": "4A",
    "heating_degree_days": 4000,
    "cooling_degree_days": 1200,
    "design_temperatures": {
        "summer_dry": 92.0,
        "winter_dry": 15.0
    },
    "humidity": {
        "summer": 60.0,
        "winter": 30.0
    }
}