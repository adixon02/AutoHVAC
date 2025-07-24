#!/usr/bin/env python3
"""
Quick test of climate service
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from models.climate import ClimateData
from services.climate_service import ClimateService

async def test_climate_service():
    """Test climate service with sample ZIP codes"""
    service = ClimateService()
    
    test_zips = ["30336", "99019", "10001", "90210", "00000"]
    
    for zip_code in test_zips:
        print(f"\n🔍 Testing ZIP code: {zip_code}")
        
        try:
            climate_data = await service.get_climate_data(zip_code)
            
            if climate_data:
                print(f"✅ Success:")
                print(f"   Zone: {climate_data.zone}")
                print(f"   Summer: {climate_data.summer_design_temp}°F")
                print(f"   Winter: {climate_data.winter_design_temp}°F")
                print(f"   Cooling DD: {climate_data.cooling_degree_days}")
                print(f"   Heating DD: {climate_data.heating_degree_days}")
            else:
                print(f"❌ No data found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🔧 Testing default climate data:")
    default_data = await service.get_default_climate_data()
    print(f"   Zone: {default_data.zone}")
    print(f"   Summer: {default_data.summer_design_temp}°F")
    print(f"   Winter: {default_data.winter_design_temp}°F")

if __name__ == "__main__":
    asyncio.run(test_climate_service())