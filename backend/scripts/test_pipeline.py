#!/usr/bin/env python3
"""
AutoHVAC Blueprint Parsing Pipeline Test
=========================================

This script tests the complete parsing pipeline from PDF blueprint to Manual J calculations:
1. Load and parse blueprint PDF (geometry + text)
2. AI cleanup to structured room data  
3. Manual J load calculations
4. Enhanced output with all required fields

Test file: backend/tests/sample_blueprints/blueprint-example-99206.pdf
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser  
from app.parser.ai_cleanup import cleanup, AICleanupError
from app.parser.schema import BlueprintSchema, Room
from services.manualj import calculate_manualj


class PipelineTestRunner:
    """Orchestrates the complete AutoHVAC parsing pipeline for testing"""
    
    def __init__(self, pdf_path: str, zip_code: str = "99206"):
        self.pdf_path = pdf_path
        self.zip_code = zip_code
        self.project_name = Path(pdf_path).stem
        self.analysis_date = datetime.now().isoformat()
        
        # Initialize parsers
        self.geometry_parser = GeometryParser()
        self.text_parser = TextParser()
        
        # Track parsing stages and results
        self.stages = {}
        self.data_gaps = []
        
    async def run_pipeline(self) -> Dict[str, Any]:
        """Execute the complete parsing pipeline"""
        print(f"🏗️  Starting AutoHVAC Pipeline Test")
        print(f"📄 PDF: {self.pdf_path}")
        print(f"📍 Zip Code: {self.zip_code}")
        print(f"⏰ Analysis Date: {self.analysis_date}")
        print("-" * 60)
        
        try:
            # Stage 1: Geometry parsing
            print("🔍 Stage 1: Extracting geometry...")
            raw_geometry = self._extract_geometry()
            self.stages["geometry"] = "completed"
            
            # Stage 2: Text parsing  
            print("📝 Stage 2: Extracting text...")
            raw_text = self._extract_text()
            self.stages["text"] = "completed"
            
            # Stage 3: AI cleanup
            print("🤖 Stage 3: AI cleanup and structuring...")
            blueprint_schema = await self._ai_cleanup(raw_geometry, raw_text)
            self.stages["ai_cleanup"] = "completed"
            
            # Stage 4: Manual J calculations
            print("🧮 Stage 4: Manual J load calculations...")
            hvac_analysis = self._calculate_loads(blueprint_schema)
            self.stages["manual_j"] = "completed"
            
            # Stage 5: Enhanced output generation
            print("📊 Stage 5: Generating enhanced output...")
            enhanced_output = self._generate_enhanced_output(
                blueprint_schema, hvac_analysis, raw_geometry, raw_text
            )
            self.stages["output"] = "completed"
            
            print("✅ Pipeline completed successfully!")
            return enhanced_output
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            raise
    
    def _extract_geometry(self) -> Any:
        """Extract geometry using GeometryParser"""
        if not Path(self.pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
            
        raw_geometry = self.geometry_parser.parse(self.pdf_path)
        
        print(f"   📐 Page size: {raw_geometry.page_width} × {raw_geometry.page_height}")
        print(f"   📏 Scale factor: {raw_geometry.scale_factor}")
        print(f"   📋 Lines found: {len(raw_geometry.lines)}")
        print(f"   🔲 Rectangles found: {len(raw_geometry.rectangles)}")
        print(f"   🖇️  Polylines found: {len(raw_geometry.polylines)}")
        
        return raw_geometry
    
    def _extract_text(self) -> Any:
        """Extract text using TextParser"""
        raw_text = self.text_parser.parse(self.pdf_path)
        
        print(f"   💬 Words found: {len(raw_text.words)}")
        print(f"   🏠 Room labels: {len(raw_text.room_labels)}")
        print(f"   📏 Dimensions: {len(raw_text.dimensions)}")
        print(f"   📝 Notes: {len(raw_text.notes)}")
        
        return raw_text
    
    async def _ai_cleanup(self, raw_geometry: Any, raw_text: Any) -> BlueprintSchema:
        """AI cleanup with fallback handling"""
        try:
            # Check for OpenAI API key
            if not os.getenv("OPENAI_API_KEY"):
                print("   ⚠️  OPENAI_API_KEY not found, using fallback parser...")
                return self._fallback_cleanup(raw_geometry, raw_text)
            
            # Use AI cleanup
            blueprint_schema = await cleanup(raw_geometry, raw_text)
            print(f"   🎯 AI successfully parsed {len(blueprint_schema.rooms)} rooms")
            return blueprint_schema
            
        except AICleanupError as e:
            print(f"   ⚠️  AI cleanup failed: {e}")
            print("   🔄 Falling back to rule-based parser...")
            return self._fallback_cleanup(raw_geometry, raw_text)
    
    def _fallback_cleanup(self, raw_geometry: Any, raw_text: Any) -> BlueprintSchema:
        """Fallback rule-based parsing when AI is unavailable"""
        from uuid import uuid4
        
        rooms = []
        
        # Match rectangles with text labels
        for i, rect in enumerate(raw_geometry.rectangles[:10]):  # Limit to top 10 rectangles
            # Find nearby room labels
            room_name = f"Room {i + 1}"
            for label in raw_text.room_labels:
                # Check if label is within rectangle bounds
                if (rect["x0"] <= label["x0"] <= rect["x1"] and 
                    rect["y0"] <= label["top"] <= rect["y1"]):
                    room_name = label["text"]
                    break
            
            # Convert pixel dimensions to feet (assume 1 inch = 72 pixels, 1/4" scale)
            scale_factor = raw_geometry.scale_factor or 48.0  # Default to 1/4" scale
            width_ft = rect["width"] / (72 / scale_factor)
            length_ft = rect["height"] / (72 / scale_factor)
            area_ft2 = width_ft * length_ft
            
            # Ensure reasonable dimensions
            if area_ft2 < 20:  # Skip very small rectangles
                continue
                
            # Estimate windows based on room type and size
            windows = self._estimate_windows(room_name, area_ft2)
            
            # Estimate orientation based on position
            orientation = self._estimate_orientation(rect, raw_geometry)
            
            rooms.append(Room(
                name=room_name,
                dimensions_ft=(round(width_ft, 1), round(length_ft, 1)),
                floor=1,  # Assume single story
                windows=windows,
                orientation=orientation,
                area=round(area_ft2, 1)
            ))
        
        # If no rooms found, create a default room
        if not rooms:
            self.data_gaps.append("No rooms detected - created default room")
            rooms.append(Room(
                name="Main Room",
                dimensions_ft=(20.0, 15.0),
                floor=1,
                windows=2,
                orientation="S",
                area=300.0
            ))
        
        total_sqft = sum(room.area for room in rooms)
        
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code=self.zip_code,
            sqft_total=total_sqft,
            stories=1,
            rooms=rooms
        )
    
    def _estimate_windows(self, room_name: str, area: float) -> int:
        """Estimate window count based on room type and size"""
        room_lower = room_name.lower()
        
        if any(word in room_lower for word in ["living", "family", "great"]):
            return max(2, int(area / 150))  # Living rooms: more windows
        elif any(word in room_lower for word in ["bed", "master", "guest"]):
            return max(1, int(area / 200))  # Bedrooms: moderate windows
        elif any(word in room_lower for word in ["bath", "powder"]):
            return 1 if area > 50 else 0   # Bathrooms: small window or none
        elif "kitchen" in room_lower:
            return max(1, int(area / 150))  # Kitchens: moderate windows
        else:
            return max(1, int(area / 200))  # Default
    
    def _estimate_orientation(self, rect: Dict, geometry: Any) -> str:
        """Estimate room orientation based on position in floor plan"""
        # Simple heuristic based on position relative to center
        center_x = geometry.page_width / 2
        center_y = geometry.page_height / 2
        room_center_x = (rect["x0"] + rect["x1"]) / 2
        room_center_y = (rect["y0"] + rect["y1"]) / 2
        
        # Determine primary orientation
        dx = room_center_x - center_x
        dy = room_center_y - center_y
        
        if abs(dx) > abs(dy):
            return "E" if dx > 0 else "W"
        else:
            return "S" if dy > 0 else "N"
    
    def _calculate_loads(self, blueprint_schema: BlueprintSchema) -> Dict[str, Any]:
        """Calculate Manual J loads"""
        hvac_analysis = calculate_manualj(blueprint_schema)
        
        print(f"   🔥 Total heating load: {hvac_analysis['heating_total']:,} BTU/hr")
        print(f"   ❄️  Total cooling load: {hvac_analysis['cooling_total']:,} BTU/hr")
        print(f"   🏠 Climate zone: {hvac_analysis['climate_zone']}")
        print(f"   🔧 Recommended system: {hvac_analysis['equipment_recommendations']['system_type']}")
        
        return hvac_analysis
    
    def _generate_enhanced_output(
        self, 
        blueprint_schema: BlueprintSchema, 
        hvac_analysis: Dict[str, Any],
        raw_geometry: Any,
        raw_text: Any
    ) -> Dict[str, Any]:
        """Generate the complete enhanced output"""
        
        # Enhanced room data with volumes and additional fields
        enhanced_rooms = []
        for i, room in enumerate(blueprint_schema.rooms):
            zone_data = hvac_analysis["zones"][i] if i < len(hvac_analysis["zones"]) else {}
            
            # Calculate volume (assume 8ft ceiling height)
            ceiling_height_ft = 8.0
            volume_ft3 = room.area * ceiling_height_ft
            
            enhanced_room = {
                "name": room.name,
                "area_ft2": room.area,
                "ceiling_height_ft": ceiling_height_ft,
                "volume_ft3": volume_ft3,
                "dimensions_ft": room.dimensions_ft,
                "floor": room.floor,
                "windows": room.windows,
                "doors": 1,  # Assume 1 door per room
                "orientation": room.orientation,
                "wall_orientations": self._get_wall_orientations(room.orientation),
                
                # HVAC load data
                "heating_btu_hr": zone_data.get("heating_btu", 0),
                "cooling_btu_hr": zone_data.get("cooling_btu", 0),
                "cfm_required": zone_data.get("cfm_required", 0),
                "duct_size": zone_data.get("duct_size", "6 inch"),
                
                # Default building envelope values
                "r_values": {
                    "walls": 13,      # R-13 typical wall insulation
                    "ceiling": 30,    # R-30 typical ceiling insulation  
                    "floor": 19,      # R-19 typical floor insulation
                    "windows": 3.1    # R-3.1 typical double-pane windows
                },
                "infiltration_cfm": round(room.area * 0.1, 1),  # 0.1 CFM/sqft
                "internal_gains": {
                    "people_btu": 250 * max(1, int(room.area / 200)),  # 250 BTU/person
                    "lighting_btu": round(room.area * 1.5),           # 1.5 BTU/sqft lighting
                    "equipment_btu": round(room.area * 0.5)           # 0.5 BTU/sqft equipment
                }
            }
            enhanced_rooms.append(enhanced_room)
        
        # Compile complete output
        output = {
            "project_name": self.project_name,
            "zip_code": self.zip_code,
            "analysis_date": self.analysis_date,
            
            # Building summary
            "building_summary": {
                "total_area_ft2": blueprint_schema.sqft_total,
                "stories": blueprint_schema.stories,
                "room_count": len(blueprint_schema.rooms),
                "total_volume_ft3": sum(room["volume_ft3"] for room in enhanced_rooms)
            },
            
            # Room details
            "rooms": enhanced_rooms,
            
            # HVAC analysis
            "hvac_analysis": hvac_analysis,
            
            # Parsing metadata
            "parsing_metadata": {
                "stages_completed": self.stages,
                "geometry_summary": {
                    "page_size": [raw_geometry.page_width, raw_geometry.page_height],
                    "scale_factor": raw_geometry.scale_factor,
                    "lines_found": len(raw_geometry.lines),
                    "rectangles_found": len(raw_geometry.rectangles),
                    "polylines_found": len(raw_geometry.polylines)
                },
                "text_summary": {
                    "words_found": len(raw_text.words),
                    "room_labels_found": len(raw_text.room_labels),
                    "dimensions_found": len(raw_text.dimensions),
                    "notes_found": len(raw_text.notes)
                },
                "data_gaps": self.data_gaps
            }
        }
        
        return output
    
    def _get_wall_orientations(self, primary_orientation: str) -> Dict[str, bool]:
        """Generate wall orientations based on primary room orientation"""
        orientations = {"N": False, "S": False, "E": False, "W": False}
        
        if primary_orientation in orientations:
            orientations[primary_orientation] = True
            
        return orientations


async def main():
    """Main test function"""
    
    # Configuration
    pdf_path = "backend/tests/sample_blueprints/blueprint-example-99206.pdf"
    zip_code = "99206"
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        print("Please ensure the test file exists before running the pipeline.")
        return
    
    try:
        # Run the pipeline
        runner = PipelineTestRunner(pdf_path, zip_code)
        result = await runner.run_pipeline()
        
        # Output results
        print("\n" + "=" * 60)
        print("📋 PIPELINE RESULTS")
        print("=" * 60)
        
        # Save results to file
        output_file = f"pipeline_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"💾 Complete results saved to: {output_file}")
        
        # Print summary
        building = result["building_summary"]
        print(f"🏠 Building: {building['total_area_ft2']:.0f} sqft, {building['room_count']} rooms")
        print(f"🔥 Heating load: {result['hvac_analysis']['heating_total']:,} BTU/hr")
        print(f"❄️  Cooling load: {result['hvac_analysis']['cooling_total']:,} BTU/hr")
        
        # Show data gaps if any
        gaps = result["parsing_metadata"]["data_gaps"]
        if gaps:
            print(f"\n⚠️  Data gaps identified:")
            for gap in gaps:
                print(f"   • {gap}")
        else:
            print(f"\n✅ No significant data gaps identified")
        
        print(f"\n🎉 AutoHVAC pipeline test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async pipeline
    asyncio.run(main())