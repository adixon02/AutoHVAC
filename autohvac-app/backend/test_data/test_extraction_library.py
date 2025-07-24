#!/usr/bin/env python3
"""
Test Extraction Library
Utilities for loading and validating test extraction JSON files
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.extraction_schema import CompleteExtractionResult, ExtractionTestCase
from services.extraction_storage import get_extraction_storage

logger = logging.getLogger(__name__)

class ExtractionTestLibrary:
    """Library for managing test extraction data"""
    
    def __init__(self, samples_dir: str = None):
        if samples_dir is None:
            samples_dir = Path(__file__).parent / "extraction_samples"
        self.samples_dir = Path(samples_dir)
        
        if not self.samples_dir.exists():
            raise ValueError(f"Samples directory not found: {self.samples_dir}")
    
    def list_test_cases(self) -> List[str]:
        """List available test case files"""
        json_files = list(self.samples_dir.glob("*.json"))
        return [f.stem for f in json_files]
    
    def load_test_case(self, test_name: str) -> CompleteExtractionResult:
        """Load a test case by name"""
        test_file = self.samples_dir / f"{test_name}.json"
        
        if not test_file.exists():
            raise FileNotFoundError(f"Test case not found: {test_name}")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Parse as CompleteExtractionResult
        return CompleteExtractionResult.model_validate(json_data)
    
    def validate_test_case(self, test_name: str) -> Dict[str, Any]:
        """Validate a test case and return validation results"""
        try:
            extraction_result = self.load_test_case(test_name)
            
            validation = {
                "test_name": test_name,
                "valid": True,
                "errors": [],
                "warnings": [],
                "summary": extraction_result.get_extraction_summary()
            }
            
            # Check for common issues
            if not extraction_result.regex_extraction and not extraction_result.ai_extraction:
                validation["errors"].append("No extraction data found")
            
            if extraction_result.regex_extraction:
                regex_confidence = extraction_result.regex_extraction.get_overall_confidence()
                if regex_confidence < 0.5:
                    validation["warnings"].append(f"Low regex confidence: {regex_confidence:.2f}")
            
            if extraction_result.ai_extraction and extraction_result.ai_extraction.ai_confidence < 0.5:
                validation["warnings"].append(f"Low AI confidence: {extraction_result.ai_extraction.ai_confidence:.2f}")
            
            if not extraction_result.final_building_data or not extraction_result.final_room_data:
                validation["errors"].append("Missing final data")
            
            return validation
            
        except Exception as e:
            return {
                "test_name": test_name,
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "summary": None
            }
    
    def validate_all_test_cases(self) -> Dict[str, Dict[str, Any]]:
        """Validate all test cases"""
        results = {}
        
        for test_name in self.list_test_cases():
            results[test_name] = self.validate_test_case(test_name)
        
        return results
    
    def load_test_case_into_storage(self, test_name: str, custom_job_id: str = None) -> str:
        """Load a test case into the extraction storage system"""
        extraction_result = self.load_test_case(test_name)
        
        # Override job_id if provided
        if custom_job_id:
            extraction_result.job_id = custom_job_id
            extraction_result.processing_metadata.job_id = custom_job_id
        
        # Save to storage
        storage_service = get_extraction_storage()
        storage_info = storage_service.save_extraction(extraction_result)
        
        logger.info(f"Loaded test case '{test_name}' into storage: {storage_info.storage_path}")
        return extraction_result.job_id
    
    def compare_extractions(self, test_name1: str, test_name2: str) -> Dict[str, Any]:
        """Compare two extraction results"""
        extraction1 = self.load_test_case(test_name1)
        extraction2 = self.load_test_case(test_name2)
        
        comparison = {
            "test1": test_name1,
            "test2": test_name2,
            "differences": [],
            "similarities": []
        }
        
        # Compare building data
        if extraction1.final_building_data and extraction2.final_building_data:
            for key in extraction1.final_building_data:
                val1 = extraction1.final_building_data.get(key)
                val2 = extraction2.final_building_data.get(key)
                
                if val1 != val2:
                    comparison["differences"].append({
                        "field": f"building.{key}",
                        "test1_value": val1,
                        "test2_value": val2
                    })
                else:
                    comparison["similarities"].append(f"building.{key}")
        
        # Compare room counts
        rooms1 = len(extraction1.final_room_data) if extraction1.final_room_data else 0
        rooms2 = len(extraction2.final_room_data) if extraction2.final_room_data else 0
        
        if rooms1 != rooms2:
            comparison["differences"].append({
                "field": "room_count",
                "test1_value": rooms1, 
                "test2_value": rooms2
            })
        
        return comparison
    
    def get_test_case_stats(self) -> Dict[str, Any]:
        """Get statistics about test cases"""
        test_cases = self.list_test_cases()
        
        stats = {
            "total_test_cases": len(test_cases),
            "extraction_methods": {},
            "confidence_ranges": {"high": 0, "medium": 0, "low": 0},
            "avg_building_size": 0,
            "room_count_distribution": {}
        }
        
        total_size = 0
        
        for test_name in test_cases:
            try:
                extraction = self.load_test_case(test_name)
                
                # Track extraction methods
                method = extraction.processing_metadata.extraction_method
                stats["extraction_methods"][method] = stats["extraction_methods"].get(method, 0) + 1
                
                # Track confidence ranges
                if extraction.regex_extraction:
                    confidence = extraction.regex_extraction.get_overall_confidence()
                    if confidence >= 0.8:
                        stats["confidence_ranges"]["high"] += 1
                    elif confidence >= 0.5:
                        stats["confidence_ranges"]["medium"] += 1
                    else:
                        stats["confidence_ranges"]["low"] += 1
                
                # Track building sizes
                if extraction.final_building_data and "floor_area_ft2" in extraction.final_building_data:
                    total_size += extraction.final_building_data["floor_area_ft2"]
                
                # Track room counts
                room_count = len(extraction.final_room_data) if extraction.final_room_data else 0
                stats["room_count_distribution"][room_count] = stats["room_count_distribution"].get(room_count, 0) + 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze test case {test_name}: {e}")
        
        if len(test_cases) > 0:
            stats["avg_building_size"] = total_size / len(test_cases)
        
        return stats

def main():
    """CLI interface for test library"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Extraction Library CLI")
    parser.add_argument("action", choices=["list", "validate", "load", "compare", "stats"], 
                       help="Action to perform")
    parser.add_argument("--test-name", help="Test case name")
    parser.add_argument("--test-name2", help="Second test case name for comparison")
    parser.add_argument("--job-id", help="Custom job ID when loading")
    
    args = parser.parse_args()
    
    library = ExtractionTestLibrary()
    
    if args.action == "list":
        print("Available test cases:")
        for test_name in library.list_test_cases():
            print(f"  - {test_name}")
    
    elif args.action == "validate":
        if args.test_name:
            result = library.validate_test_case(args.test_name)
            print(json.dumps(result, indent=2, default=str))
        else:
            results = library.validate_all_test_cases()
            print(json.dumps(results, indent=2, default=str))
    
    elif args.action == "load":
        if not args.test_name:
            print("--test-name required for load action")
            return
        
        job_id = library.load_test_case_into_storage(args.test_name, args.job_id)
        print(f"Loaded test case '{args.test_name}' with job_id: {job_id}")
    
    elif args.action == "compare":
        if not args.test_name or not args.test_name2:
            print("--test-name and --test-name2 required for compare action")
            return
        
        comparison = library.compare_extractions(args.test_name, args.test_name2)
        print(json.dumps(comparison, indent=2, default=str))
    
    elif args.action == "stats":
        stats = library.get_test_case_stats()
        print(json.dumps(stats, indent=2, default=str))

if __name__ == "__main__":
    main()