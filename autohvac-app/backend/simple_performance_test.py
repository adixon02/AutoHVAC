#!/usr/bin/env python3
"""
Simple performance test to identify bottlenecks
"""

import time
from enhanced_blueprint_processor import EnhancedBlueprintProcessor

def test_individual_components():
    """Test each component individually to find bottlenecks"""
    
    processor = EnhancedBlueprintProcessor()
    
    # Simple test text
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
        """,
        'normalized_text': """
        BROWN RESIDENCE + ADU
        25196 WYVERN LN
        LIBERTY LAKE, WA 99019
        MAIN LEVEL: 1500 SF
        TOTAL: 3300 SF
        LIVING ROOM
        KITCHEN
        WALL: R-13
        """
    }
    
    print("Testing individual components...")
    
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
    print(f"\nTotal time: {total_time:.3f}s")
    print(f"Success: {total_time < 1.0 and confidence >= 0.90}")

if __name__ == "__main__":
    test_individual_components()