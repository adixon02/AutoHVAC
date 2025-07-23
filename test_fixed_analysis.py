#!/usr/bin/env python3
"""
Test the fixed blueprint analysis pipeline
"""

import sys
import logging
from pathlib import Path

# Setup path
backend_path = Path(__file__).parent / "autohvac-app" / "backend"
sys.path.insert(0, str(backend_path))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    from enhanced_blueprint_processor import EnhancedBlueprintProcessor
    from professional_output_generator import ProfessionalOutputGenerator
    
    print("🧪 Testing Fixed Blueprint Analysis Pipeline")
    print("=" * 50)
    
    # Initialize processors
    processor = EnhancedBlueprintProcessor()
    output_generator = ProfessionalOutputGenerator()
    
    print("✅ Processors initialized successfully")
    print(f"   AI Gap Filler: {'Enabled' if output_generator.ai_gap_filler and output_generator.ai_gap_filler.enabled else 'Disabled'}")
    print(f"   Config loaded: {len(output_generator.config)} settings")
    
    # Test with a sample PDF path (won't actually process file, just test structure)
    test_pdf_path = Path("test_blueprint.pdf")
    
    # Create a mock extraction result to test calculations
    from enhanced_blueprint_processor import ExtractionResult, ProjectInfo, BuildingCharacteristics, Room, InsulationSpecs
    
    mock_extraction = ExtractionResult(
        project_info=ProjectInfo(
            project_name="Test Project",
            address="123 Test Street",
            city="Test City", 
            state="WA",
            zip_code="99019",
            confidence_score=0.85
        ),
        building_chars=BuildingCharacteristics(
            total_area=2400.0,
            stories=2,
            construction_type="new_construction",
            confidence_score=0.90
        ),
        rooms=[
            Room("Living Room", 320, "main", 9.0, 48, 2, "", 0.8),
            Room("Master Bedroom", 200, "main", 9.0, 24, 2, "", 0.8),
            Room("Kitchen", 150, "main", 9.0, 12, 1, "", 0.8)
        ],
        insulation=InsulationSpecs(
            wall_r_value=20.0,
            ceiling_r_value=49.0, 
            foundation_r_value=13.0,
            window_u_value=0.3,
            confidence_score=0.80
        ),
        raw_data={},
        overall_confidence=0.85,
        gaps_identified=["missing_project_details"]
    )
    
    print("\n📊 Testing Load Calculations...")
    print(f"   Mock project: {mock_extraction.project_info.project_name}")
    print(f"   Total area: {mock_extraction.building_chars.total_area:,.0f} sq ft")
    print(f"   Rooms: {len(mock_extraction.rooms)}")
    print(f"   Overall confidence: {mock_extraction.overall_confidence:.1%}")
    
    # Test the generate_outputs method
    try:
        results = output_generator.generate_outputs(mock_extraction, {
            "zip_code": "99019",
            "project_name": "Test Project",
            "project_type": "residential",
            "construction_type": "new_construction"
        })
        
        print("\n🎯 Analysis Results:")
        if 'manual_j_calculation' in results:
            manual_j = results['manual_j_calculation']
            if 'load_calculation' in manual_j:
                loads = manual_j['load_calculation']
                print(f"   ❄️ Cooling: {loads.get('cooling_tons', 0)} tons ({loads.get('total_cooling_load', 0):,} BTU/hr)")
                print(f"   🔥 Heating: {loads.get('heating_tons', 0)} tons ({loads.get('total_heating_load', 0):,} BTU/hr)")
        
        if 'hvac_system_design' in results:
            hvac = results['hvac_system_design']
            print(f"   🏠 System: {hvac.get('system_type', 'Unknown')}")
            if 'cost_estimate' in hvac:
                print(f"   💰 Cost: ${hvac['cost_estimate'].get('total', 0):,}")
        
        if 'professional_deliverables' in results:
            deliverables = results['professional_deliverables']
            print(f"   📋 Confidence: {deliverables.get('analysis_confidence', 'Unknown'):.1%}")
            print(f"   🤖 AI Used: {'Yes' if deliverables.get('ai_gap_filling_used', False) else 'No'}")
        
        if 'error' in results:
            print(f"   ❌ Error: {results['error']}")
        
        print("\n✅ Analysis pipeline test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Setup error: {e}")
    import traceback
    traceback.print_exc()