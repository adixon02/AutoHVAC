from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import sys
import os

# Import enhanced core systems
from ..core.logging_config import get_logger, performance_timer
from ..core.error_handling import (
    AutoHVACException, AutoHVACErrors, 
    validate_zip_code, handle_database_error
)
from ..services.climate_service import get_climate_service

logger = get_logger(__name__)
climate_service = get_climate_service()

router = APIRouter()

@router.get("/zone/{zip_code}")
async def get_climate_zone(zip_code: str) -> Dict[str, Any]:
    """
    Get climate zone data for a specific ZIP code
    Returns ASHRAE climate zone, design temperatures, and humidity data
    
    Args:
        zip_code: 5-digit ZIP code
    
    Returns:
        Dict containing comprehensive climate data
        
    Raises:
        AutoHVACException: If ZIP code is invalid or data not found
    """
    with performance_timer(f"climate_zone_lookup_{zip_code}", logger):
        # Validate ZIP code format
        normalized_zip = validate_zip_code(zip_code)
        
        try:
            # Get climate data using the optimized service
            climate_data = await climate_service.get_climate_data(normalized_zip)
            
            if not climate_data:
                logger.warning(f"Climate data not found for ZIP code: {normalized_zip}")
                raise AutoHVACException(
                    AutoHVACErrors.CLIMATE_DATA_UNAVAILABLE,
                    details={"zip_code": normalized_zip}
                )
            
            logger.debug(
                f"Climate data retrieved for ZIP {normalized_zip}",
                extra={
                    'extra_data': {
                        'zip_code': normalized_zip,
                        'zone': climate_data.zone,
                        'state': climate_data.state,
                        'cached': hasattr(climate_data, 'cached_at') and climate_data.cached_at is not None
                    }
                }
            )
            
            return climate_data.to_dict()
            
        except AutoHVACException:
            raise
        except Exception as e:
            logger.error(f"Climate zone lookup failed for {normalized_zip}: {str(e)}", exc_info=True)
            handle_database_error(e, f"climate_zone_lookup for {normalized_zip}")

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
async def get_climate_service_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics about the climate service including cache performance
    """
    with performance_timer("climate_service_stats", logger):
        try:
            # Get cache statistics from the optimized service
            cache_stats = climate_service.get_cache_stats()
            
            logger.debug("Climate service stats retrieved", extra={'extra_data': cache_stats})
            
            return {
                "service_status": "healthy",
                "performance": {
                    "cache_hit_rate": f"{cache_stats.get('cache_hit_rate', 0) * 100:.1f}%",
                    "total_requests": cache_stats.get('total_requests', 0),
                    "cache_hits": cache_stats.get('cache_hits', 0),
                    "cache_misses": cache_stats.get('cache_misses', 0),
                    "database_queries": cache_stats.get('database_queries', 0),
                    "avg_response_time_ms": f"{cache_stats.get('avg_response_time_ms', 0):.2f}"
                },
                "cache_info": {
                    "current_size": cache_stats.get('cache_size', 0),
                    "max_size": cache_stats.get('cache_max_size', 0),
                    "ttl_hours": cache_stats.get('cache_ttl_hours', 0)
                },
                "recommendations": {
                    "performance": "Excellent" if cache_stats.get('cache_hit_rate', 0) > 0.8 else "Good" if cache_stats.get('cache_hit_rate', 0) > 0.6 else "Consider preloading common ZIP codes",
                    "memory_usage": "Optimal" if cache_stats.get('cache_size', 0) < cache_stats.get('cache_max_size', 1) * 0.9 else "Consider increasing cache size"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve climate service stats: {str(e)}", exc_info=True)
            raise AutoHVACException(
                AutoHVACErrors.INTERNAL_SERVER_ERROR,
                details={
                    "operation": "climate_service_stats",
                    "original_error": str(e)
                },
                cause=e
            )

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