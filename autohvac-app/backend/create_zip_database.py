#!/usr/bin/env python3
"""
ZIP Code Database Migration Script
Creates a comprehensive SQLite database combining:
- ZIP code geographic data (from GitHub dataset)
- County mapping data
- CBECS/ASHRAE climate zones
- Existing climate zone data from JSON
"""

import sqlite3
import pandas as pd
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZipDatabaseMigrator:
    def __init__(self, data_dir="data", db_path="zip_climate_database.db"):
        self.data_dir = Path(data_dir)
        self.db_path = db_path
        self.conn = None
        
    def create_database_schema(self):
        """Create the SQLite database schema"""
        logger.info("Creating database schema...")
        
        # Main ZIP codes table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS zip_codes (
            zip_code TEXT PRIMARY KEY,
            city TEXT,
            state TEXT,
            state_abbr TEXT,
            county TEXT,
            latitude REAL,
            longitude REAL,
            population INTEGER,
            area_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Climate zones table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS climate_zones (
            zip_code TEXT PRIMARY KEY,
            ashrae_zone TEXT,
            cbecs_zone TEXT,
            description TEXT,
            summer_db REAL,
            winter_db REAL,
            summer_wb REAL,
            winter_wb REAL,
            summer_humidity REAL,
            winter_humidity REAL, 
            source TEXT,
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (zip_code) REFERENCES zip_codes(zip_code)
        )
        """)
        
        # County climate zones lookup table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS county_climate_zones (
            state TEXT,
            county TEXT,
            cbecs_zone TEXT,
            noaa_division_name TEXT,
            PRIMARY KEY (state, county)
        )
        """)
        
        # API cache table for external lookups
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            zip_code TEXT PRIMARY KEY,
            api_source TEXT,
            response_data TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_zip_state ON zip_codes(state)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_zip_county ON zip_codes(county)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_climate_zone ON climate_zones(ashrae_zone)")
        
        self.conn.commit()
        logger.info("Database schema created successfully")
    
    def load_existing_climate_data(self):
        """Load existing climate zone data from JSON file"""
        logger.info("Loading existing climate zone data...")
        
        json_file = Path("climate_zones.json")
        if not json_file.exists():
            logger.warning("climate_zones.json not found, skipping existing data")
            return {}
            
        with open(json_file, 'r') as f:
            existing_data = json.load(f)
            
        logger.info(f"Loaded {len(existing_data)} existing climate zone records")
        return existing_data
    
    def process_zip_codes_data(self):
        """Process the comprehensive ZIP codes dataset"""
        logger.info("Processing ZIP codes data...")
        
        csv_file = self.data_dir / "full_dataset_csv.csv"
        if not csv_file.exists():
            logger.error(f"ZIP codes file {csv_file} not found")
            return
            
        # Read CSV data
        df = pd.read_csv(csv_file)
        
        # Filter for US ZIP codes only
        us_data = df[df['country'] == 'United States'].copy()
        
        # Clean and prepare data
        us_data['zipCode'] = us_data['zipCode'].astype(str).str.zfill(5)
        us_data = us_data[us_data['zipCode'].str.match(r'^\d{5}$')]  # Valid 5-digit ZIP codes only
        
        # Insert into database
        zip_data = []
        for _, row in us_data.iterrows():
            zip_data.append((
                row['zipCode'],
                row['city'],
                row['state'],
                row['stateISO'],
                None,  # county - will be filled from county mapping
                float(row['latitude']),
                float(row['longitude']),
                None,  # population - not in this dataset
                row['npa']  # area code
            ))
        
        # Batch insert
        self.conn.executemany("""
        INSERT OR REPLACE INTO zip_codes 
        (zip_code, city, state, state_abbr, county, latitude, longitude, population, area_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, zip_data)
        
        self.conn.commit()
        logger.info(f"Inserted {len(zip_data)} ZIP code records")
    
    def process_county_mapping(self):
        """Process ZIP code to county mapping"""
        logger.info("Processing county mapping data...")
        
        csv_file = self.data_dir / "zip_county_mapping.csv"
        if not csv_file.exists():
            logger.warning(f"County mapping file {csv_file} not found, skipping")
            return
            
        df = pd.read_csv(csv_file)
        
        # Update ZIP codes with county information
        for _, row in df.iterrows():
            self.conn.execute("""
            UPDATE zip_codes 
            SET county = ?
            WHERE zip_code = ? AND state_abbr = ?
            """, (row['county'], str(row['zipcode']).zfill(5), row['state_abbr']))
        
        self.conn.commit()
        logger.info("Updated ZIP codes with county information")
    
    def process_climate_zones(self):
        """Process county-level climate zone data"""
        logger.info("Processing climate zone data...")
        
        csv_file = self.data_dir / "cbecs_climate_zones.csv"
        if not csv_file.exists():
            logger.warning(f"Climate zones file {csv_file} not found, skipping")
            return
            
        df = pd.read_csv(csv_file)
        
        # Insert county climate zone data
        county_data = []
        for _, row in df.iterrows():
            county_data.append((
                row['State'],
                row['County'],
                str(row['CBECS Climate Zone']),
                row['NOAA Climate Division (Name)']
            ))
        
        self.conn.executemany("""
        INSERT OR REPLACE INTO county_climate_zones 
        (state, county, cbecs_zone, noaa_division_name)
        VALUES (?, ?, ?, ?)
        """, county_data)
        
        self.conn.commit()
        logger.info(f"Inserted {len(county_data)} county climate zone records")
    
    def map_zip_to_climate_zones(self):
        """Map ZIP codes to climate zones using county data"""
        logger.info("Mapping ZIP codes to climate zones...")
        
        # Query to join ZIP codes with county climate zones
        query = """
        INSERT OR REPLACE INTO climate_zones 
        (zip_code, cbecs_zone, source, confidence_score)
        SELECT 
            z.zip_code,
            c.cbecs_zone,
            'county_mapping',
            0.8
        FROM zip_codes z
        JOIN county_climate_zones c ON 
            z.state_abbr = c.state AND 
            UPPER(z.county) = UPPER(c.county)
        WHERE z.county IS NOT NULL
        """
        
        cursor = self.conn.execute(query)
        mapped_count = cursor.rowcount
        self.conn.commit()
        logger.info(f"Mapped {mapped_count} ZIP codes to climate zones via county data")
    
    def import_existing_climate_data(self):
        """Import existing high-quality climate data from JSON"""
        logger.info("Importing existing climate data...")
        
        existing_data = self.load_existing_climate_data()
        
        climate_data = []
        for zip_code, data in existing_data.items():
            climate_data.append((
                zip_code,
                data.get('zone'),
                None,  # cbecs_zone
                data.get('description'),
                data.get('design_temperatures', {}).get('summer_db'),
                data.get('design_temperatures', {}).get('winter_db'),
                data.get('design_temperatures', {}).get('summer_wb'),
                data.get('design_temperatures', {}).get('winter_wb'),
                data.get('humidity', {}).get('summer'),
                data.get('humidity', {}).get('winter'),
                'existing_data',
                1.0  # High confidence for existing data
            ))
        
        self.conn.executemany("""
        INSERT OR REPLACE INTO climate_zones 
        (zip_code, ashrae_zone, cbecs_zone, description, summer_db, winter_db, 
         summer_wb, winter_wb, summer_humidity, winter_humidity, source, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, climate_data)
        
        self.conn.commit()
        logger.info(f"Imported {len(climate_data)} existing climate records")
    
    def generate_statistics(self):
        """Generate statistics about the database"""
        logger.info("Generating database statistics...")
        
        stats = {}
        
        # Total ZIP codes
        cursor = self.conn.execute("SELECT COUNT(*) FROM zip_codes")
        stats['total_zip_codes'] = cursor.fetchone()[0]
        
        # ZIP codes with county info
        cursor = self.conn.execute("SELECT COUNT(*) FROM zip_codes WHERE county IS NOT NULL")
        stats['zip_codes_with_county'] = cursor.fetchone()[0]
        
        # ZIP codes with climate data
        cursor = self.conn.execute("SELECT COUNT(*) FROM climate_zones")
        stats['zip_codes_with_climate'] = cursor.fetchone()[0]
        
        # Climate zones by source
        cursor = self.conn.execute("SELECT source, COUNT(*) FROM climate_zones GROUP BY source")
        stats['climate_data_by_source'] = dict(cursor.fetchall())
        
        # Coverage by state
        cursor = self.conn.execute("""
        SELECT z.state_abbr, 
               COUNT(*) as total_zips,
               COUNT(c.zip_code) as zips_with_climate
        FROM zip_codes z
        LEFT JOIN climate_zones c ON z.zip_code = c.zip_code
        GROUP BY z.state_abbr
        ORDER BY total_zips DESC
        LIMIT 10
        """)
        stats['top_states_coverage'] = cursor.fetchall()
        
        logger.info("Database Statistics:")
        logger.info(f"Total ZIP codes: {stats['total_zip_codes']}")
        logger.info(f"ZIP codes with county: {stats['zip_codes_with_county']}")
        logger.info(f"ZIP codes with climate data: {stats['zip_codes_with_climate']}")
        logger.info(f"Climate data sources: {stats['climate_data_by_source']}")
        
        return stats
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("Starting ZIP code database migration...")
        
        try:
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            
            # Run migration steps
            self.create_database_schema()
            self.process_zip_codes_data()
            self.process_county_mapping()
            self.process_climate_zones()
            self.map_zip_to_climate_zones()
            self.import_existing_climate_data()
            
            # Generate statistics
            stats = self.generate_statistics()
            
            logger.info("Migration completed successfully!")
            return stats
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    migrator = ZipDatabaseMigrator()
    stats = migrator.run_migration()
    
    print("\n" + "="*50)
    print("MIGRATION COMPLETE!")
    print("="*50)
    print(f"Total ZIP codes processed: {stats['total_zip_codes']}")
    print(f"ZIP codes with climate data: {stats['zip_codes_with_climate']}")
    coverage_pct = (stats['zip_codes_with_climate'] / stats['total_zip_codes']) * 100
    print(f"Climate data coverage: {coverage_pct:.1f}%")