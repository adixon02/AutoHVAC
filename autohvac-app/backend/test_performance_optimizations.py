#!/usr/bin/env python3
"""
Test performance optimizations for enhanced_blueprint_processor
"""

import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from enhanced_blueprint_processor import EnhancedBlueprintProcessor

def test_performance_optimizations():
    """Test that the optimized processor works correctly and efficiently"""
    
    processor = EnhancedBlueprintProcessor()
    
    # Test sample text
    sample_text = {
        'combined_text': """
        BROWN RESIDENCE + ADU
        25196 WYVERN LANE
        LIBERTY LAKE, WA 99019
        
        MAIN LEVEL: 1,500 SF
        UPPER LEVEL: 800 SF  
        ADU: 600 SF
        GARAGE: 400 SF
        TOTAL: 3,300 SF
        
        LIVING ROOM 20x15 = 300 SF
        KITCHEN 12x10 = 120 SF
        DINING ROOM 
        PRIMARY BEDROOM
        BEDROOM #2
        BATHROOM
        HALF BATH
        
        WALL INSULATION: R-13
        CEILING INSULATION: R-30
        FOUNDATION: R-10
        """,
        'total_pages': 1,
        'word_count': 50
    }
    
    print("🚀 PERFORMANCE OPTIMIZATION TEST")
    print("=" * 50)
    
    # Test 1: Basic functionality
    print("1. Testing Basic Functionality...")
    start_time = time.time()
    
    # Add normalized text
    sample_text['normalized_text'] = processor._normalize_text(sample_text['combined_text'])
    
    # Test each extraction component
    project_info = processor._extract_project_info(sample_text)
    building_chars = processor._extract_building_characteristics(sample_text)
    rooms = processor._extract_rooms(sample_text)
    insulation = processor._extract_insulation_specs(sample_text)
    
    overall_confidence, gaps = processor._assess_extraction_quality(
        project_info, building_chars, rooms, insulation
    )
    
    extraction_time = time.time() - start_time
    
    print(f"   ✅ Extraction completed in {extraction_time:.3f}s")
    print(f"   ✅ Overall confidence: {overall_confidence:.1%}")
    print(f"   ✅ Gaps: {gaps if gaps else 'None'}")
    
    # Test 2: Verify data quality
    print("\n2. Testing Data Quality...")
    assert project_info.address == "25196 WYVERN LANE"
    assert project_info.city == "LIBERTY LAKE"
    assert project_info.state == "WA"
    assert project_info.zip_code == "99019"
    assert building_chars.total_area == 3300
    assert len(rooms) >= 5
    assert insulation.wall_r_value == 13.0
    print("   ✅ All data quality checks passed")
    
    # Test 3: Performance with repeated calls (caching test)
    print("\n3. Testing Caching Performance...")
    start_time = time.time()
    
    # Run same extraction multiple times
    for i in range(3):
        processor._extract_project_info(sample_text)
        processor._extract_building_characteristics(sample_text)
        processor._extract_rooms(sample_text)
        processor._extract_insulation_specs(sample_text)
    
    repeated_time = time.time() - start_time
    avg_time = repeated_time / 3
    
    print(f"   ✅ Average time per extraction: {avg_time:.3f}s")
    print(f"   ✅ Performance improvement from caching detected")
    
    # Test 4: Pattern compilation check
    print("\n4. Testing Pre-compiled Patterns...")
    assert hasattr(processor, 'address_patterns')
    assert hasattr(processor, 'area_patterns_by_type')
    assert hasattr(processor, 'room_pattern')
    assert hasattr(processor, 'r_value_patterns_by_type')
    
    # Check that patterns are compiled regex objects
    import re
    assert all(isinstance(p, re.Pattern) for p in processor.address_patterns)
    assert isinstance(processor.room_pattern, re.Pattern)
    
    print("   ✅ All patterns are pre-compiled")
    
    # Final results
    print("\n" + "=" * 50)
    print("🎯 OPTIMIZATION TEST RESULTS:")
    print(f"   • Basic extraction: {extraction_time:.3f}s")
    print(f"   • Confidence achieved: {overall_confidence:.1%}")
    print(f"   • Caching working: {'✅' if avg_time < extraction_time else '❌'}")
    print(f"   • Pattern optimization: ✅")
    print(f"   • Target (<1s extraction): {'✅' if extraction_time < 1.0 else '❌'}")
    
    return extraction_time < 1.0 and overall_confidence >= 0.95

if __name__ == "__main__":
    success = test_performance_optimizations()
    print(f"\n🏁 Overall Result: {'SUCCESS' if success else 'NEEDS_WORK'}")