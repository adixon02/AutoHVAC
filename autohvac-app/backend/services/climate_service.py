"""
Climate Data Service
Clean implementation using preserved climate database
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional
from models.climate import ClimateData

logger = logging.getLogger(__name__)

class ClimateService:
    """
    Service for looking up climate data by ZIP code
    Uses preserved climate.db from V1
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to data directory relative to project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "climate.db"
        
        self.db_path = str(db_path)
        
        # Load climate zones JSON for design temperature fallbacks
        self.climate_zones_data = {}
        try:
            json_path = Path(__file__).parent.parent.parent / "data" / "climate-zones.json"
            with open(json_path, 'r') as f:
                self.climate_zones_data = json.load(f)
            logger.info(f"Loaded climate zones data with {len(self.climate_zones_data)} entries")
        except Exception as e:
            logger.warning(f"Could not load climate zones JSON: {e}")
        
        logger.info(f"Initialized ClimateService with database: {self.db_path}")
    
    async def get_climate_data(self, zip_code: str) -> Optional[ClimateData]:
        """
        Get climate data for a ZIP code
        
        Args:
            zip_code: 5-digit ZIP code string
            
        Returns:
            ClimateData object or None if not found
        """
        try:
            # Validate ZIP code format
            if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
                logger.warning(f"Invalid ZIP code format: {zip_code}")
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query climate data by ZIP code
                cursor.execute("""
                    SELECT cz.zip_code, cz.ashrae_zone, cz.cbecs_zone,
                           cz.summer_db, cz.winter_db, cz.summer_wb, 
                           cz.summer_humidity, zc.city, zc.state
                    FROM climate_zones cz
                    LEFT JOIN zip_codes zc ON cz.zip_code = zc.zip_code
                    WHERE cz.zip_code = ?
                """, (zip_code,))
                
                row = cursor.fetchone()
                if not row:
                    logger.info(f"No climate data found for ZIP code: {zip_code}")
                    return None
                
                # Get design temperatures from JSON data if available
                json_data = self.climate_zones_data.get(zip_code, {})
                design_temps = json_data.get('design_temperatures', {})
                
                # Use database data first, then JSON fallback, then defaults
                zone_from_db = row['ashrae_zone'] or row['cbecs_zone']
                if zone_from_db and len(str(zone_from_db)) == 1:
                    # Convert single digit to climate zone format (e.g., "4" -> "4A")
                    climate_zone = f"{zone_from_db}A"
                else:
                    climate_zone = zone_from_db or json_data.get('zone', "4A")
                
                summer_temp = row['summer_db'] or design_temps.get('summer_db', 95)
                winter_temp = row['winter_db'] or design_temps.get('winter_db', 10)
                
                # Fix humidity calculation - ensure it's in the right range
                if row['summer_humidity']:
                    humidity = min(0.030, max(0.005, float(row['summer_humidity'])))
                else:
                    json_humidity = json_data.get('humidity', {}).get('summer', 50)
                    # Convert percentage to humidity ratio
                    humidity = min(0.030, max(0.005, json_humidity / 1000.0 + 0.008))
                
                # Estimate degree days based on design temperatures
                heating_dd = max(0, int((65 - winter_temp) * 365 / 5)) if winter_temp else 4500
                cooling_dd = max(0, int((summer_temp - 65) * 365 / 10)) if summer_temp else 1500
                
                climate_data = ClimateData(
                    zip_code=row['zip_code'],
                    zone=climate_zone,
                    heating_degree_days=heating_dd,
                    cooling_degree_days=cooling_dd,
                    winter_design_temp=int(winter_temp),
                    summer_design_temp=int(summer_temp),
                    humidity=float(humidity)
                )
                
                logger.info(f"Found climate data for {zip_code}: Zone {climate_data.zone}")
                return climate_data
                
        except sqlite3.Error as e:
            logger.error(f"Database error looking up ZIP {zip_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error looking up ZIP {zip_code}: {e}")
            return None
    
    async def get_default_climate_data(self) -> ClimateData:
        """
        Get default climate data for when ZIP lookup fails
        Uses conservative design temperatures
        """
        return ClimateData(
            zip_code="00000",
            zone="4A",
            heating_degree_days=4500,
            cooling_degree_days=1500,
            winter_design_temp=10,
            summer_design_temp=95,
            humidity=0.016
        )
    
    async def validate_zip_coverage(self, zip_code: str) -> bool:
        """
        Check if we have climate data coverage for a ZIP code
        """
        climate_data = await self.get_climate_data(zip_code)
        return climate_data is not None