#!/usr/bin/env python3
"""
Quick test to verify confidence improvements
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from enhanced_blueprint_processor import EnhancedBlueprintProcessor

def test_confidence_improvements():
    """Test the confidence improvements on a small sample"""
    
    processor = EnhancedBlueprintProcessor()
    
    # Test sample text that should trigger our improvements
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
        
        LIVING ROOM
        KITCHEN  
        DINING ROOM
        PRIMARY BEDROOM
        BEDROOM #2
        BATHROOM
        HALF BATH
        
        WALL INSULATION: R-13
        CEILING INSULATION: R-30
        FOUNDATION: R-10
        """,
        'normalized_text': """
        BROWN RESIDENCE + ADU
        25196 WYVERN LN
        LIBERTY LAKE, WA 99019
        
        MAIN LEVEL: 1500 SF
        UPPER LEVEL: 800 SF  
        ADU: 600 SF
        GARAGE: 400 SF
        TOTAL: 3300 SF
        
        LIVING ROOM
        KITCHEN  
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
    
    print("🧪 TESTING CONFIDENCE IMPROVEMENTS")
    print("=" * 50)
    
    # Test project info extraction
    print("📍 Testing Project Info Extraction...")
    project_info = processor._extract_project_info(sample_text)
    print(f"  Project Name: {project_info.project_name}")
    print(f"  Address: {project_info.address}")
    print(f"  City: {project_info.city}, {project_info.state} {project_info.zip_code}")
    print(f"  Confidence: {project_info.confidence_score:.1%}")
    
    # Test building characteristics
    print("\n🏠 Testing Building Characteristics...")
    building_chars = processor._extract_building_characteristics(sample_text)
    print(f"  Total Area: {building_chars.total_area:,.0f} SF")
    print(f"  Main Residence: {building_chars.main_residence_area:,.0f} SF")
    print(f"  ADU: {building_chars.adu_area:,.0f} SF")
    print(f"  Stories: {building_chars.stories}")
    print(f"  Confidence: {building_chars.confidence_score:.1%}")
    
    # Test room extraction
    print("\n🚪 Testing Room Extraction...")
    rooms = processor._extract_rooms(sample_text)
    print(f"  Rooms Found: {len(rooms)}")
    for room in rooms[:5]:  # Show first 5 rooms
        print(f"    • {room.name}: {room.area:.0f} SF ({room.confidence_score:.1%})")
    avg_room_confidence = sum(r.confidence_score for r in rooms) / len(rooms) if rooms else 0
    print(f"  Average Room Confidence: {avg_room_confidence:.1%}")
    
    # Test insulation specs
    print("\n🧱 Testing Insulation Specs...")
    insulation = processor._extract_insulation_specs(sample_text)
    print(f"  Wall: R-{insulation.wall_r_value}")
    print(f"  Ceiling: R-{insulation.ceiling_r_value}")
    print(f"  Foundation: R-{insulation.foundation_r_value}")
    print(f"  Confidence: {insulation.confidence_score:.1%}")
    
    # Test overall confidence assessment
    print("\n📊 Testing Overall Confidence Assessment...")
    overall_confidence, gaps = processor._assess_extraction_quality(
        project_info, building_chars, rooms, insulation
    )
    
    print(f"  Overall Confidence: {overall_confidence:.1%}")
    print(f"  Gaps Identified: {', '.join(gaps) if gaps else 'None'}")
    
    print("\n" + "=" * 50)
    print("✅ CONFIDENCE IMPROVEMENT TEST COMPLETE")
    
    # Summary
    component_scores = [
        project_info.confidence_score,
        building_chars.confidence_score, 
        avg_room_confidence,
        insulation.confidence_score
    ]
    
    print(f"\n📈 SUMMARY:")
    print(f"  Component Scores: {[f'{s:.1%}' for s in component_scores]}")
    print(f"  Overall Score: {overall_confidence:.1%}")
    print(f"  Target Achievement: {'✅ SUCCESS' if overall_confidence >= 0.95 else '🎯 PROGRESS'}")

if __name__ == "__main__":
    test_confidence_improvements()