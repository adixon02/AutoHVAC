#!/usr/bin/env python3
"""
Test the processor with a really simple working version
"""

import sys
import time
from pathlib import Path

# Import the backup original version
sys.path.insert(0, '/Users/austindixon/Documents/AutoHVAC')
from enhanced_blueprint_processor import EnhancedBlueprintProcessor

def test_basic_functionality():
    """Test basic functionality works"""
    
    print("Testing basic processor functionality...")
    
    processor = EnhancedBlueprintProcessor()
    
    # Simple test data
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
        'total_pages': 1,
        'word_count': 50
    }
    
    start_time = time.time()
    
    try:
        # Test each component
        project_info = processor._extract_project_info(text_data)
        print(f"✓ Project info: {project_info.address}")
        
        building_chars = processor._extract_building_characteristics(text_data)
        print(f"✓ Building: {building_chars.total_area} SF")
        
        rooms = processor._extract_rooms(text_data)
        print(f"✓ Rooms: {len(rooms)} found")
        
        insulation = processor._extract_insulation_specs(text_data)
        print(f"✓ Insulation: R-{insulation.wall_r_value}")
        
        confidence, gaps = processor._assess_extraction_quality(project_info, building_chars, rooms, insulation)
        print(f"✓ Confidence: {confidence:.1%}")
        
        total_time = time.time() - start_time
        print(f"\nTotal time: {total_time:.3f}s")
        print(f"Status: {'✅ WORKING' if total_time < 5.0 else '❌ TOO SLOW'}")
        
        return total_time < 5.0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")