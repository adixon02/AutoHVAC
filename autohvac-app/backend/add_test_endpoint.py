#!/usr/bin/env python3
"""
Temporary script to add test data endpoint for demonstrating the JSON workflow
"""
# Add this to main.py or run as a separate service

from fastapi import APIRouter
from api.blueprint import job_storage, _combine_extraction_results
from test_data.test_extraction_library import ExtractionTestLibrary
from services.blueprint_extractor import BuildingData
from services.ai_blueprint_analyzer import AIExtractedData

def add_test_data():
    """Add test data to job storage"""
    library = ExtractionTestLibrary()
    
    test_cases = [
        ("residential_1480sqft_complete", "frontend-test-1480"),
        ("residential_900sqft_minimal", "frontend-test-900"),
        ("problematic_scanned_low_quality", "frontend-test-problematic")
    ]
    
    for test_name, job_id in test_cases:
        try:
            # Load test case
            extraction = library.load_test_case(test_name)
            
            # Convert to old format for backward compatibility
            building_data = None
            if extraction.regex_extraction:
                building_data = BuildingData(
                    floor_area_ft2=extraction.regex_extraction.floor_area_ft2,
                    wall_insulation=extraction.regex_extraction.wall_insulation,
                    ceiling_insulation=extraction.regex_extraction.ceiling_insulation,
                    window_schedule=extraction.regex_extraction.window_schedule,
                    air_tightness=extraction.regex_extraction.air_tightness,
                    foundation_type=extraction.regex_extraction.foundation_type,
                    orientation=extraction.regex_extraction.orientation,
                    room_dimensions=extraction.regex_extraction.room_dimensions,
                    confidence_scores=extraction.regex_extraction.confidence_scores
                )
            
            ai_data = None
            if extraction.ai_extraction:
                ai_data = AIExtractedData(
                    room_layouts=extraction.ai_extraction.room_layouts,
                    window_orientations=extraction.ai_extraction.window_orientations,
                    building_envelope=extraction.ai_extraction.building_envelope,
                    architectural_details=extraction.ai_extraction.architectural_details,
                    hvac_existing=extraction.ai_extraction.hvac_existing,
                    extraction_confidence=extraction.ai_extraction.ai_confidence
                )
            
            # Create combined results using the same function as the real API
            combined_results = _combine_extraction_results(building_data, ai_data)
            
            # Add to job storage exactly like the real upload endpoint does
            job_storage[job_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Blueprint analysis complete (test data)",
                "extraction_id": extraction.extraction_id,
                "project_info": {
                    "project_name": f"Test Project - {test_name}",
                    "zip_code": "99206",
                    "building_type": "residential",
                    "construction_type": "new"
                },
                "results": combined_results
            }
            
            print(f"✅ Added {test_name} as job_id: {job_id}")
            
        except Exception as e:
            print(f"❌ Failed to add {test_name}: {e}")
            import traceback
            traceback.print_exc()

# Add an endpoint to load test data
test_router = APIRouter(prefix="/api/test", tags=["testing"])

@test_router.post("/load-test-data")
async def load_test_data():
    """Load test extraction data for frontend testing"""
    add_test_data()
    return {
        "message": "Test data loaded",
        "jobs_available": list(job_storage.keys()),
        "total_jobs": len(job_storage)
    }

if __name__ == "__main__":
    add_test_data()