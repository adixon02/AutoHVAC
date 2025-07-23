#!/usr/bin/env python3
"""
Fast performance test without normalized text
"""

import time
from enhanced_blueprint_processor import EnhancedBlueprintProcessor

def test_fast_extraction():
    """Test each component without normalized text causing slowdowns"""
    
    processor = EnhancedBlueprintProcessor()
    
    # Simple test text without normalized_text field
    text_data = {
        'combined_text': """
        BROWN RESIDENCE + ADU
        25196 WYVERN LANE
        LIBERTY LAKE, WA 99019
        MAIN LEVEL: 1500 SF
        TOTAL: 3300 SF
        LIVING ROOM
        KITCHEN
        WALL: R-13
        """
    }
    
    print("🚀 FAST PERFORMANCE TEST")
    print("=" * 40)
    
    # Test 1: Project info
    start = time.time()
    project_info = processor._extract_project_info(text_data)
    t1 = time.time() - start
    print(f"1. Project info: {t1:.3f}s - Address: {project_info.address}")
    
    # Test 2: Building characteristics  
    start = time.time()
    building_chars = processor._extract_building_characteristics(text_data)
    t2 = time.time() - start
    print(f"2. Building chars: {t2:.3f}s - Total area: {building_chars.total_area}")
    
    # Test 3: Rooms
    start = time.time()
    rooms = processor._extract_rooms(text_data)
    t3 = time.time() - start
    print(f"3. Rooms: {t3:.3f}s - Found: {len(rooms)} rooms")
    
    # Test 4: Insulation
    start = time.time()
    insulation = processor._extract_insulation_specs(text_data)
    t4 = time.time() - start
    print(f"4. Insulation: {t4:.3f}s - Wall R-value: {insulation.wall_r_value}")
    
    # Test 5: Confidence assessment
    start = time.time()
    confidence, gaps = processor._assess_extraction_quality(project_info, building_chars, rooms, insulation)
    t5 = time.time() - start
    print(f"5. Confidence: {t5:.3f}s - Score: {confidence:.1%}")
    
    total_time = t1 + t2 + t3 + t4 + t5
    print(f"\n📊 RESULTS:")
    print(f"Total time: {total_time:.3f}s")
    print(f"Target (<1s): {'✅ ACHIEVED' if total_time < 1.0 else '❌ NEEDS WORK'}")  
    print(f"Confidence (>95%): {'✅ ACHIEVED' if confidence >= 0.95 else '📈 GOOD' if confidence >= 0.90 else '🎯 PROGRESS'}")
    
    return total_time < 1.0 and confidence >= 0.95

if __name__ == "__main__":
    success = test_fast_extraction()
    print(f"\n🏁 Overall: {'SUCCESS' if success else 'PARTIAL SUCCESS'}")