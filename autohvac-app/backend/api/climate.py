from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from climate_database import climate_db

router = APIRouter()

@router.get("/zone/{zip_code}")
async def get_climate_zone(zip_code: str) -> Dict[str, Any]:
    """
    Get climate zone data for a specific ZIP code
    Returns ASHRAE climate zone, design temperatures, and humidity data
    """
    # Validate ZIP code format
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP code format. Must be 5 digits."
        )
    
    # Get climate data from our comprehensive database
    climate_data = climate_db.get_climate_data(zip_code)
    
    return {
        "zip_code": zip_code,
        "climate_zone": climate_data.get("zone"),
        "description": climate_data.get("description"),
        "design_temperatures": climate_data.get("design_temperatures"),
        "humidity": climate_data.get("humidity"),
        "city": climate_data.get("city", "Unknown"),
        "state": climate_data.get("state"),
        "county": climate_data.get("county"),
        "latitude": climate_data.get("latitude"),
        "longitude": climate_data.get("longitude"),
        "source": climate_data.get("source"),
        "confidence_score": climate_data.get("confidence_score", 0.5)
    }

@router.get("/search")
async def search_climate_zones(
    query: str = Query(..., min_length=2, description="Search by ZIP, city, or state"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return")
) -> List[Dict[str, Any]]:
    """
    Search for ZIP codes by city, state, or partial ZIP code
    Returns list of matching locations with climate data
    """
    results = climate_db.search_zip_codes(query, limit)
    
    return [
        {
            "zip_code": result["zip_code"],
            "city": result["city"],
            "state": result["state_abbr"],
            "county": result["county"],
            "climate_zone": result["climate_zone"]
        }
        for result in results
    ]

@router.get("/stats")
async def get_climate_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the climate database coverage
    """
    stats = climate_db.get_coverage_stats()
    
    return {
        "total_zip_codes": stats.get("total_zip_codes", 0),
        "zip_codes_with_climate": stats.get("zip_codes_with_climate", 0),
        "coverage_percentage": stats.get("climate_coverage_pct", 0),
        "data_sources": stats.get("climate_data_by_source", {}),
        "top_states": stats.get("top_states_coverage", [])[:10]
    }

@router.get("/")
async def climate_info():
    """
    Get information about the climate data API
    """
    return {
        "service": "AutoHVAC Climate Data API",
        "version": "1.0.0",
        "description": "Comprehensive ASHRAE climate zone data for US ZIP codes",
        "coverage": {
            "total_zip_codes": 34748,
            "climate_data_coverage": "80%+ (27,789 ZIP codes)",
            "data_sources": ["CBECS/ASHRAE county mapping", "NREL API", "Geographic estimation"]
        },
        "endpoints": {
            "get_zone": "GET /zone/{zip_code} - Get climate data for a ZIP code",
            "search": "GET /search?query={query} - Search ZIP codes by city/state",
            "stats": "GET /stats - Get database coverage statistics"
        }
    }