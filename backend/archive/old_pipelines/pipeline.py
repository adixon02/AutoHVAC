"""
AutoHVAC v2 Pipeline - Clean, Fast, Accurate
70% less code, 100% more reliable
"""

import os
import sys
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend_v2 to path
sys.path.insert(0, str(Path(__file__).parent))

from stages.classify import identify_floor_plans, PageInfo
from stages.validate import validate_building, ValidationError
from stages.extract import combine_extractions
from stages.calculate import run_manual_j
from stages.synthesize import synthesize_building_data

from extractors.vision import get_vision_extractor
from extractors.vector import get_vector_extractor
from extractors.scale import get_scale_detector
from extractors.ocr import OCRExtractor
from extractors.schedule import get_schedule_extractor
from extractors.orientation import get_orientation_extractor

from core.models import Floor, Room, Building, HVACLoads

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Pipeline:
    """
    Main pipeline orchestrator
    Simple, clear, no hidden complexity
    """
    
    def __init__(self):
        # Check for OpenAI API key and enable vision if available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            logger.info("✅ Vision extraction ENABLED (OpenAI API key found)")
            try:
                self.vision = get_vision_extractor()
            except Exception as e:
                logger.warning(f"Vision extractor failed to initialize: {e}")
                self.vision = None
        else:
            logger.warning("⚠️  Vision extraction DISABLED (no OPENAI_API_KEY)")
            self.vision = None
        
        self.vector = get_vector_extractor()
        self.scale = get_scale_detector()
        self.ocr = OCRExtractor()
        self.schedule = get_schedule_extractor()
        self.orientation = get_orientation_extractor()
    
    async def process_blueprint(self, pdf_path: str, zip_code: str, construction_quality: str = "average", building_era: str = None) -> Dict[str, Any]:
        """
        Main entry point - process a blueprint PDF
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Building location
            construction_quality: "tight", "average", or "loose"
            
        Returns:
            {
                "success": True/False,
                "building": {...},
                "loads": {...},
                "metadata": {...}
            }
        """
        start_time = time.time()
        logger.info(f"Processing {pdf_path} for ZIP {zip_code}")
        
        try:
            # 1. Classify ALL pages by type
            logger.info("Stage 1: Page classification (ALL pages)")
            page_classifications = self._classify_all_pages(pdf_path)
            
            floor_pages = page_classifications['floor_plans']
            if not floor_pages:
                raise ValidationError("No floor plans found in PDF")
            
            logger.info(f"Page breakdown: {len(floor_pages)} floor plans, "
                       f"{len(page_classifications['elevations'])} elevations, "
                       f"{len(page_classifications['sections'])} sections, "
                       f"{len(page_classifications['schedules'])} schedules")
            
            # 2. Extract building-wide data from ALL pages (not just schedules)
            logger.info("Stage 2: Comprehensive data extraction from all page types")
            building_data = self._extract_building_data(pdf_path)
            
            # NEW: Extract construction details from non-floor pages
            if self.vision:
                construction_data = await self._extract_construction_details(
                    pdf_path, page_classifications, building_era
                )
                building_data.update(construction_data)
            
            # 3. Extract data from each floor plan page (parallel)
            logger.info("Stage 3: Floor-specific extraction")
            floors, extraction_results = await self._extract_all_floors(pdf_path, floor_pages)
            extraction_results["building_data"] = building_data
            
            # 4. Validate aggressively
            logger.info("Stage 4: Validation")
            building = validate_building(floors)
            building.zip_code = zip_code
            
            # 5. AI Synthesis - combine all data for comprehensive analysis
            logger.info("Stage 5: AI synthesis for comprehensive Manual J factors")
            synthesis_data = synthesize_building_data(
                building,
                extraction_results,
                {"pdf_path": pdf_path, "page_count": len(floor_pages)}
            )
            
            # Log any missing factors identified
            if synthesis_data.get("synthesis", {}).get("missing_factors"):
                logger.warning(f"Missing Manual J factors: {synthesis_data['synthesis']['missing_factors']}")
            
            # 6. Calculate HVAC loads with synthesis enhancements
            logger.info(f"Stage 6: Manual J calculations (construction: {construction_quality})")
            # CRITICAL: Pass extraction_results too so envelope data is available!
            combined_data = {**synthesis_data, **extraction_results}
            loads = run_manual_j(building, construction_quality, combined_data)
            
            # Success!
            processing_time = time.time() - start_time
            logger.info(f"✅ Pipeline complete in {processing_time:.1f}s")
            logger.info(f"   {building.floor_count} floors, {building.room_count} rooms, "
                       f"{building.total_sqft:.0f} sqft")
            logger.info(f"   Heating: {loads.heating_btu_hr:,.0f} BTU/hr ({loads.heating_tons:.1f} tons)")
            logger.info(f"   Cooling: {loads.cooling_btu_hr:,.0f} BTU/hr ({loads.cooling_tons:.1f} tons)")
            
            return {
                "success": True,
                "building": building.to_json(),
                "loads": loads.to_json(),
                "synthesis": synthesis_data.get("synthesis", {}),
                "metadata": {
                    "processing_time": processing_time,
                    "floors_detected": building.floor_count,
                    "rooms_detected": building.room_count,
                    "total_sqft": building.total_sqft,
                    "synthesis_confidence": synthesis_data.get("synthesis", {}).get("confidence", "unknown")
                }
            }
            
        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation"
            }
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "processing"
            }
    
    async def _extract_all_floors(self, pdf_path: str, floor_pages: List[PageInfo]) -> tuple[List[Floor], Dict[str, Any]]:
        """Extract data from all floor pages in parallel"""
        floors = []
        all_extraction_results = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit extraction tasks for each floor
            future_to_floor = {}
            
            for page_info in floor_pages:
                future = executor.submit(
                    self._extract_single_floor,
                    pdf_path,
                    page_info
                )
                future_to_floor[future] = page_info
            
            # Collect results as they complete
            for future in as_completed(future_to_floor):
                page_info = future_to_floor[future]
                try:
                    floor, extraction_results = future.result(timeout=90)
                    if floor and floor.room_count > 0:
                        floors.append(floor)
                        logger.info(f"Extracted {floor.name}: {floor.room_count} rooms, "
                                   f"{floor.total_sqft:.0f} sqft")
                        # Store extraction results for synthesis
                        all_extraction_results[f"floor_{floor.number}"] = extraction_results
                except Exception as e:
                    logger.error(f"Failed to extract page {page_info.page_num}: {e}")
        
        return floors, all_extraction_results
    
    def _extract_building_data(self, pdf_path: str) -> Dict[str, Any]:
        """Extract building-wide data like schedules and orientation"""
        building_data = {}
        
        # Extract orientation data (north arrow, wall orientations)
        try:
            logger.info("Extracting building orientation...")
            orientation_data = self.orientation.extract_orientation(pdf_path)
            building_data['orientation'] = orientation_data
            
            if orientation_data['has_north_arrow']:
                logger.info(f"Found north arrow at {orientation_data['north_direction']}° "
                           f"(confidence: {orientation_data['confidence']:.0%})")
            else:
                logger.info("No north arrow found, using default orientation")
                
        except Exception as e:
            logger.warning(f"Orientation extraction failed: {e}")
            building_data['orientation'] = {
                "has_north_arrow": False,
                "north_direction": 0,
                "confidence": 0.3,
                "orientation_notes": ["Failed to extract orientation"]
            }
        
        # Extract window/door schedules
        try:
            logger.info("Extracting window and door schedules...")
            schedule_data = self.schedule.extract_schedules(pdf_path)
            building_data['schedules'] = schedule_data
            
            if schedule_data['has_schedules']:
                logger.info(f"Found {len(schedule_data['windows'])} window types, "
                           f"{len(schedule_data['doors'])} door types")
                logger.info(f"Total window area: {schedule_data['total_window_area']:.0f} sq ft, "
                           f"Avg U-value: {schedule_data['average_u_value']:.2f}")
            else:
                logger.info("No schedules found, will use defaults")
                
        except Exception as e:
            logger.warning(f"Schedule extraction failed: {e}")
            building_data['schedules'] = {
                "windows": [],
                "doors": [],
                "has_schedules": False,
                "total_window_area": 0,
                "average_u_value": 0.30,
                "average_shgc": 0.30
            }
        
        return building_data
    
    def _extract_single_floor(self, pdf_path: str, page_info: PageInfo) -> tuple[Optional[Floor], Dict[str, Any]]:
        """Extract data from a single floor page using parallel extractors"""
        logger.info(f"Extracting page {page_info.page_num + 1}: {page_info.floor_name}")
        
        results = {}
        
        # Run vision extraction first (if available) - it's the slowest
        if self.vision:
            try:
                context = {
                    'floor_name': page_info.floor_name,
                    'floor_number': page_info.floor_number
                }
                logger.info("Running vision extraction...")
                results['vision'] = self.vision.extract(pdf_path, page_info.page_num, context)
                logger.info(f"Vision found {len(results['vision'].get('rooms', []))} rooms")
            except Exception as e:
                logger.warning(f"Vision extraction failed: {e}")
                results['vision'] = None
        
        # Run other extractors in parallel (they're faster)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            
            futures['vector'] = executor.submit(
                self.vector.extract_vectors, pdf_path, page_info.page_num
            )
            
            futures['scale'] = executor.submit(
                self.scale.detect_scale, pdf_path, page_info.page_num
            )
            
            # Collect results
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=15)
                except Exception as e:
                    logger.warning(f"{name} extraction failed: {e}")
                    results[name] = None
        
        # Combine extraction results intelligently
        # NOW returns both floor and envelope!
        floor_data, envelope_data = combine_extractions(
            results,
            page_info.floor_number or 1,
            page_info.floor_name or "Unknown Floor",
            pdf_path,
            page_info.page_num
        )
        
        # Store envelope in results for later use
        if envelope_data:
            results['envelope'] = envelope_data
        
        return floor_data, results
    
    def _classify_all_pages(self, pdf_path: str) -> Dict[str, List[PageInfo]]:
        """
        Classify ALL pages in the PDF by type
        Returns dict with keys: floor_plans, elevations, sections, schedules, title
        """
        import fitz
        doc = fitz.open(pdf_path)
        
        classifications = {
            'floor_plans': [],
            'elevations': [],
            'sections': [],
            'schedules': [],
            'title': [],
            'other': []
        }
        
        # First get floor plans using existing method
        floor_pages = identify_floor_plans(pdf_path)
        classifications['floor_plans'] = floor_pages
        floor_page_nums = {p.page_num for p in floor_pages}
        
        # Now classify remaining pages
        for page_num in range(len(doc)):
            if page_num in floor_page_nums:
                continue  # Already classified as floor plan
            
            page = doc[page_num]
            text = page.get_text().upper()
            
            # Simple heuristic classification
            page_info = PageInfo(
                page_num=page_num,
                page_type='other',  # Will be updated below
                floor_number=None,
                floor_name=None,
                score=0.0,
                confidence=0.5,
                keywords_found=[]
            )
            
            if page_num == 0 or 'PROJECT' in text or 'CLIENT' in text or 'DRAWN BY' in text:
                page_info.page_type = 'title'
                classifications['title'].append(page_info)
            elif 'ELEVATION' in text or 'NORTH ELEVATION' in text or 'SOUTH ELEVATION' in text:
                page_info.page_type = 'elevation'
                classifications['elevations'].append(page_info)
            elif 'SECTION' in text or 'DETAIL' in text or 'WALL SECTION' in text:
                page_info.page_type = 'section'
                classifications['sections'].append(page_info)
            elif 'SCHEDULE' in text or 'WINDOW SCHEDULE' in text or 'DOOR SCHEDULE' in text:
                page_info.page_type = 'schedule'
                classifications['schedules'].append(page_info)
            else:
                page_info.page_type = 'other'
                classifications['other'].append(page_info)
        
        doc.close()
        return classifications
    
    async def _extract_construction_details(
        self, 
        pdf_path: str, 
        page_classifications: Dict[str, List], 
        building_era: str = None
    ) -> Dict[str, Any]:
        """
        Extract construction details from non-floor-plan pages using Vision
        """
        construction_data = {
            'wall_r_value': None,
            'roof_r_value': None,
            'floor_r_value': None,
            'window_type': None,
            'foundation_type': None,
            'building_era_detected': building_era,
            'construction_notes': []
        }
        
        if not self.vision:
            return construction_data
        
        # Extract from title pages (building year, project info)
        for page_info in page_classifications.get('title', []):
            try:
                logger.info(f"Extracting building info from title page {page_info.page_num + 1}")
                title_prompt = """Extract building information from this title/cover page:
                - Year designed or built
                - Project location
                - Building type
                - Any code references (tells us era)
                Return as JSON: {"year": "YYYY", "location": "...", "codes": "..."}"""
                
                result = self.vision.extract_with_prompt(pdf_path, page_info.page_num, title_prompt)
                if result and 'year' in result:
                    construction_data['building_era_detected'] = result['year']
                    construction_data['construction_notes'].append(f"Built/designed in {result['year']}")
            except Exception as e:
                logger.warning(f"Failed to extract from title page: {e}")
        
        # Extract from elevation pages (wall construction, window types)
        for page_info in page_classifications.get('elevations', [])[:2]:  # Limit to first 2 elevations
            try:
                logger.info(f"Extracting construction from elevation page {page_info.page_num + 1}")
                elevation_prompt = """Analyze this elevation drawing for construction details:
                - Wall material (siding type, brick, etc.)
                - Window type (single/double pane, sliding, casement)
                - Foundation type if visible
                - Any insulation callouts
                Return as JSON: {"wall_material": "...", "window_type": "...", "foundation": "..."}"""
                
                result = self.vision.extract_with_prompt(pdf_path, page_info.page_num, elevation_prompt)
                if result:
                    if 'window_type' in result and not construction_data['window_type']:
                        construction_data['window_type'] = result['window_type']
                    construction_data['construction_notes'].append(f"Elevation shows: {result}")
            except Exception as e:
                logger.warning(f"Failed to extract from elevation: {e}")
        
        # Extract from section/detail pages (R-values, wall thickness)
        for page_info in page_classifications.get('sections', [])[:2]:  # Limit to first 2 sections
            try:
                logger.info(f"Extracting R-values from section page {page_info.page_num + 1}")
                section_prompt = """Extract insulation and construction details from this section/detail:
                - Wall R-value or insulation type (e.g., "R-13", "R-19")
                - Wall thickness (2x4 or 2x6)
                - Roof/ceiling R-value
                - Floor R-value
                - Foundation insulation
                Return as JSON: {"wall_r": N, "wall_thickness": "2x4/2x6", "roof_r": N, "floor_r": N}"""
                
                result = self.vision.extract_with_prompt(pdf_path, page_info.page_num, section_prompt)
                if result:
                    if 'wall_r' in result and not construction_data['wall_r_value']:
                        construction_data['wall_r_value'] = result['wall_r']
                    if 'roof_r' in result and not construction_data['roof_r_value']:
                        construction_data['roof_r_value'] = result['roof_r']
                    if 'floor_r' in result and not construction_data['floor_r_value']:
                        construction_data['floor_r_value'] = result['floor_r']
                    construction_data['construction_notes'].append(f"Section shows: {result}")
            except Exception as e:
                logger.warning(f"Failed to extract from section: {e}")
        
        logger.info(f"Construction details extracted: R-{construction_data['wall_r_value']} walls, "
                   f"R-{construction_data['roof_r_value']} roof, {construction_data['window_type']} windows")
        
        return construction_data


async def process_blueprint(pdf_path: str, zip_code: str, construction_quality: str = "average", building_era: str = None) -> Dict[str, Any]:
    """Main entry point"""
    pipeline = Pipeline()
    return await pipeline.process_blueprint(pdf_path, zip_code, construction_quality, building_era)


if __name__ == "__main__":
    # Test with command line args
    if len(sys.argv) < 3:
        print("Usage: python pipeline.py <pdf_path> <zip_code>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    zip_code = sys.argv[2]
    
    # Run pipeline
    result = asyncio.run(process_blueprint(pdf_path, zip_code))
    
    # Print results
    if result["success"]:
        print("\n✅ SUCCESS!")
        print(f"Building: {result['metadata']['floors_detected']} floors, "
              f"{result['metadata']['rooms_detected']} rooms, "
              f"{result['metadata']['total_sqft']:.0f} sqft")
        print(f"Heating Load: {result['loads']['heating_btu_hr']:,} BTU/hr "
              f"({result['loads']['heating_tons']:.1f} tons)")
        print(f"Cooling Load: {result['loads']['cooling_btu_hr']:,} BTU/hr "
              f"({result['loads']['cooling_tons']:.1f} tons)")
    else:
        print(f"\n❌ FAILED: {result['error']}")
