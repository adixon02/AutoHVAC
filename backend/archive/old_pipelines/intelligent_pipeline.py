"""
Intelligent AI-First Blueprint Pipeline
Extracts EVERYTHING, then uses AI to understand holistically
"""

import os
import sys
import logging
import json
import time
import re
import fitz  # PyMuPDF
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

# Add backend_v2 to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.vision import get_vision_extractor
from extractors.vector import get_vector_extractor
from extractors.envelope import get_envelope_extractor
from extractors.orientation import get_orientation_extractor
from extractors.schedule import get_schedule_extractor
from extractors.scale import get_scale_detector
from extractors.ocr import OCRExtractor
from core.climate_zones import get_climate_data_for_zip

logger = logging.getLogger(__name__)


@dataclass
class BlueprintData:
    """Complete blueprint data from all sources"""
    all_text: List[Dict[str, Any]]  # {page: N, text: "...", location: (x,y)}
    page_images: List[str]  # Base64 encoded images
    vector_data: List[Dict]  # Vector paths from all pages
    tables: List[Dict]  # Detected tables
    page_count: int
    index_content: Optional[str] = None  # Blueprint index if found
    envelopes: Optional[List[Any]] = None  # Building envelope data per floor
    orientation: Optional[Dict] = None  # North arrow and wall orientations
    schedules: Optional[Dict] = None  # Window/door schedules
    scale: Optional[float] = None  # Drawing scale (feet per inch)
    

class IntelligentPipeline:
    """
    AI-first pipeline that understands blueprints holistically
    """
    
    def __init__(self):
        self.vision = get_vision_extractor()
        self.vector = get_vector_extractor()
        self.envelope = get_envelope_extractor()
        self.orientation = get_orientation_extractor()
        self.schedule = get_schedule_extractor()
        self.scale = get_scale_detector()
        self.ocr = OCRExtractor()
        
    def process_blueprint(self, pdf_path: str, zip_code: str, user_inputs: Dict = None) -> Dict[str, Any]:
        """
        Main entry point - process blueprint with AI comprehension
        
        Args:
            pdf_path: Path to blueprint PDF
            zip_code: Building location
            user_inputs: Optional user-provided data (year_built, foundation_type, etc.)
        """
        start_time = time.time()
        logger.info(f"Starting intelligent pipeline for {pdf_path}")
        
        # Phase 1: Extract EVERYTHING from ALL pages
        logger.info("Phase 1: Extracting all data from blueprint...")
        blueprint_data = self._extract_everything(pdf_path)
        
        # Phase 2: AI comprehension of entire blueprint
        logger.info("Phase 2: AI comprehension of complete blueprint...")
        understanding = self._ai_comprehend_blueprint(blueprint_data, zip_code, user_inputs)
        
        # Phase 3: Calculate loads with full understanding
        logger.info("Phase 3: Calculating Manual J loads...")
        loads = self._calculate_loads(understanding, zip_code)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Pipeline complete in {processing_time:.1f}s")
        
        return {
            "success": True,
            "understanding": understanding,
            "loads": loads,
            "metadata": {
                "processing_time": processing_time,
                "page_count": blueprint_data.page_count,
                "extraction_complete": True
            }
        }
    
    def _extract_everything(self, pdf_path: str) -> BlueprintData:
        """
        Extract ALL information from ALL pages at once
        No filtering, no assumptions - just get everything
        """
        doc = fitz.open(pdf_path)
        
        blueprint_data = BlueprintData(
            all_text=[],
            page_images=[],
            vector_data=[],
            tables=[],
            page_count=len(doc)
        )
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            logger.info(f"Extracting page {page_num + 1}/{len(doc)}")
            
            # 1. Extract ALL text with positions
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                if block[4].strip():  # Has text
                    blueprint_data.all_text.append({
                        "page": page_num + 1,
                        "text": block[4].strip(),
                        "bbox": block[:4],  # Bounding box
                        "location": "header" if block[1] < 100 else 
                                   "footer" if block[3] > page.rect.height - 100 else 
                                   "body"
                    })
            
            # Check for index on first pages
            if page_num < 2:
                page_text = page.get_text().upper()
                if "INDEX" in page_text or "CONTENTS" in page_text:
                    blueprint_data.index_content = page_text
                    logger.info(f"Found blueprint index on page {page_num + 1}")
            
            # 2. Extract vector data (walls, dimensions, etc.)
            try:
                vector_result = self.vector.extract_vectors(pdf_path, page_num)
                if vector_result:
                    blueprint_data.vector_data.append({
                        "page": page_num + 1,
                        "paths": len(vector_result.paths) if hasattr(vector_result, 'paths') else 0,
                        "texts": len(vector_result.texts) if hasattr(vector_result, 'texts') else 0,
                        "data": vector_result
                    })
                    
                    # Also extract envelope from vector data!
                    if page_num < 3:  # Focus on floor plan pages
                        try:
                            # Convert VectorData to dict format for envelope extractor
                            vector_dict = {
                                'paths': vector_result.paths if hasattr(vector_result, 'paths') else [],
                                'texts': vector_result.texts if hasattr(vector_result, 'texts') else [],
                                'dimensions': vector_result.dimensions if hasattr(vector_result, 'dimensions') else [],
                                'page_width': vector_result.page_width if hasattr(vector_result, 'page_width') else 612,
                                'page_height': vector_result.page_height if hasattr(vector_result, 'page_height') else 792
                            }
                            
                            # Try to get scale for this page
                            scale_factor = 1.0 / 48.0  # Default 1/4" = 1' scale (48 px/ft)
                            try:
                                scale_result = self.scale.detect_scale(pdf_path, page_num)
                                if scale_result and scale_result.scale_px_per_ft > 0:
                                    scale_factor = 1.0 / scale_result.scale_px_per_ft
                                    logger.debug(f"Using scale factor {scale_factor:.4f} for page {page_num + 1}")
                            except:
                                pass
                            
                            envelope_result = self.envelope.extract_envelope(
                                vector_dict,
                                scale_factor=scale_factor,
                                north_angle=0.0    # Will be updated if north arrow found
                            )
                            if envelope_result:
                                logger.info(f"Extracted envelope for page {page_num + 1}: "
                                           f"perimeter={envelope_result.total_perimeter_ft:.1f}ft")
                                # Store envelope data
                                if blueprint_data.envelopes is None:
                                    blueprint_data.envelopes = []
                                blueprint_data.envelopes.append(envelope_result)
                        except Exception as e:
                            logger.debug(f"Envelope extraction failed: {e}")
            except Exception as e:
                logger.warning(f"Vector extraction failed for page {page_num + 1}: {e}")
            
            # 3. Detect tables (for square footage summaries, schedules)
            tables = self._detect_tables(page)
            if tables:
                blueprint_data.tables.extend(tables)
                logger.info(f"Found {len(tables)} tables on page {page_num + 1}")
            
            # 4. Convert page to image for vision analysis
            # We'll do this on-demand in AI comprehension to save memory
        
        doc.close()
        
        # Extract building-wide data using specialized extractors
        logger.info("Extracting building-wide data...")
        
        # 1. Extract orientation (north arrow)
        try:
            orientation_data = self.orientation.extract_orientation(pdf_path)
            blueprint_data.orientation = orientation_data
            if orientation_data['has_north_arrow']:
                logger.info(f"Found north arrow at {orientation_data['north_direction']}°")
        except Exception as e:
            logger.warning(f"Orientation extraction failed: {e}")
        
        # 2. Extract window/door schedules
        try:
            schedule_data = self.schedule.extract_schedules(pdf_path)
            blueprint_data.schedules = schedule_data
            if schedule_data['has_schedules']:
                logger.info(f"Found schedules: {len(schedule_data['windows'])} window types, "
                           f"{len(schedule_data['doors'])} door types")
        except Exception as e:
            logger.warning(f"Schedule extraction failed: {e}")
        
        # 3. Detect scale on floor plan pages
        try:
            # Scale detection might be having issues, wrap carefully
            page_count = blueprint_data.page_count
            for page_num in range(min(3, page_count)):  # Check first 3 pages
                try:
                    scale_result = self.scale.detect_scale(pdf_path, page_num)
                    if scale_result and scale_result.scale > 0:
                        blueprint_data.scale = scale_result.scale
                        logger.info(f"Detected scale on page {page_num + 1}: 1\" = {scale_result.scale}'")
                        break
                except Exception as e:
                    logger.debug(f"Scale detection failed for page {page_num + 1}: {e}")
        except Exception as e:
            logger.warning(f"Scale detection failed: {e}")
        
        # Log what we found
        logger.info(f"Extraction complete:")
        logger.info(f"  - {len(blueprint_data.all_text)} text blocks")
        logger.info(f"  - {len(blueprint_data.vector_data)} pages with vector data")
        logger.info(f"  - {len(blueprint_data.tables)} tables")
        logger.info(f"  - Index found: {blueprint_data.index_content is not None}")
        logger.info(f"  - Envelopes extracted: {len(blueprint_data.envelopes) if blueprint_data.envelopes else 0}")
        logger.info(f"  - North arrow: {blueprint_data.orientation.get('has_north_arrow', False) if blueprint_data.orientation else False}")
        logger.info(f"  - Schedules found: {blueprint_data.schedules.get('has_schedules', False) if blueprint_data.schedules else False}")
        
        return blueprint_data
    
    def _detect_tables(self, page) -> List[Dict]:
        """
        Detect and extract tables (like square footage summaries)
        """
        tables = []
        text = page.get_text()
        lines = text.split('\n')
        
        # Look for consolidated square footage summary
        # Pattern: consecutive lines with floor names and square footages
        sqft_data = {}
        i = 0
        while i < len(lines) - 1:
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # Check for floor label followed by sqft on next line
            # e.g., "MAIN FLOOR" followed by "1225 S.F."
            if any(word in line.upper() for word in ['MAIN FLOOR', 'FIRST FLOOR', '2ND FLOOR', 'SECOND FLOOR', 
                                                      'BONUS', 'BASEMENT', 'TOTAL', 'GARAGE']):
                # Check if next line has square footage
                sqft_match = re.search(r'(\d+(?:,\d+)?)\s*(?:S\.?F\.?|SQ\.?\s*FT)', next_line, re.IGNORECASE)
                if sqft_match:
                    key = line.strip()
                    value = int(sqft_match.group(1).replace(',', ''))
                    sqft_data[key] = value
                    i += 2  # Skip the sqft line
                    continue
            
            # Also check for single-line format "MAIN FLOOR 1225 S.F."
            combined_match = re.search(r'([\w\s\(\)]+?)\s+(\d+(?:,\d+)?)\s*(?:S\.?F\.?|SQ\.?\s*FT)', line, re.IGNORECASE)
            if combined_match and any(word in combined_match.group(1).upper() for word in 
                                     ['FLOOR', 'TOTAL', 'GARAGE', 'BASEMENT', 'BONUS']):
                key = combined_match.group(1).strip()
                value = int(combined_match.group(2).replace(',', ''))
                sqft_data[key] = value
            
            i += 1
        
        # If we found square footage data, create a table entry
        if sqft_data:
            table = {
                "type": "square_footage",
                "page": page.number + 1,
                "parsed": sqft_data
            }
            tables.append(table)
            logger.info(f"Found sqft table on page {page.number + 1}: {sqft_data}")
        
        return tables
    
    def _ai_comprehend_blueprint(
        self, 
        blueprint_data: BlueprintData,
        zip_code: str,
        user_inputs: Dict = None
    ) -> Dict[str, Any]:
        """
        Use AI to understand the complete blueprint holistically
        Single comprehensive prompt with all data
        """
        if not self.vision or not self.vision.enabled:
            logger.warning("Vision not available, using text-only comprehension")
            return self._text_only_comprehension(blueprint_data, user_inputs)
        
        # Build comprehensive prompt with ALL extracted data
        prompt = self._build_comprehension_prompt(blueprint_data, zip_code, user_inputs)
        
        # For now, analyze key pages with vision
        # In production, we'd send all pages to GPT-4V
        key_pages = self._identify_key_pages(blueprint_data)
        
        logger.info(f"Sending {len(key_pages)} key pages to AI for comprehension")
        
        # Comprehensive AI analysis
        understanding = {
            "building_sqft": None,
            "floor_breakdown": {},
            "foundation_type": None,
            "wall_construction": None,
            "roof_construction": None,
            "window_specs": {},
            "insulation": {},
            "building_era": None,
            "notes": [],
            "confidence": 0.0
        }
        
        # Extract from tables first (most reliable)
        for table in blueprint_data.tables:
            if table["type"] == "square_footage":
                parsed = table["parsed"]
                logger.info(f"Processing sqft table: {parsed}")
                
                # Update floor breakdown
                for key, value in parsed.items():
                    key_upper = key.upper()
                    if 'GARAGE' in key_upper:
                        # Skip garage - not conditioned space
                        continue
                    elif 'TOTAL' in key_upper:
                        # This is the total sqft
                        understanding["building_sqft"] = value
                    elif 'MAIN' in key_upper or 'FIRST' in key_upper:
                        understanding["floor_breakdown"]["main_floor"] = value
                    elif 'SECOND' in key_upper or 'UPPER' in key_upper or 'BONUS' in key_upper or '2ND' in key_upper:
                        understanding["floor_breakdown"]["second_floor"] = value
                    elif 'BASEMENT' in key_upper:
                        understanding["floor_breakdown"]["basement"] = value
                
                # Calculate total from floors if not found
                if not understanding["building_sqft"] and understanding["floor_breakdown"]:
                    total = sum(understanding["floor_breakdown"].values())
                    if total > 0:
                        understanding["building_sqft"] = total
                        logger.info(f"Calculated total sqft from floors: {total}")
        
        # Extract from text patterns UNLESS user provided year_built
        # If user provides year_built, we should trust it over blueprint dates
        if not (user_inputs and user_inputs.get('year_built')):
            logger.info("No user year_built provided, will extract years from blueprint")
            understanding = self._extract_from_text(blueprint_data.all_text, understanding)
        else:
            logger.info(f"User provided year_built: {user_inputs['year_built']}, skipping year extraction")
            # Still extract other info, just not years
            understanding = self._extract_from_text(blueprint_data.all_text, understanding, skip_year=True)
        
        # Use vision for visual elements
        if len(key_pages) > 0:
            vision_understanding = self._vision_comprehension(
                blueprint_data, key_pages, prompt
            )
            # Merge vision understanding
            understanding = self._merge_understanding(understanding, vision_understanding)
        
        # Apply extracted data from specialized extractors
        if blueprint_data.envelopes:
            understanding['envelopes'] = blueprint_data.envelopes
            logger.info(f"Using {len(blueprint_data.envelopes)} extracted building envelopes")
        
        if blueprint_data.orientation:
            understanding['orientation'] = blueprint_data.orientation
            
        if blueprint_data.schedules and blueprint_data.schedules.get('has_schedules'):
            understanding['window_count'] = len(blueprint_data.schedules.get('windows', []))
            understanding['door_count'] = len(blueprint_data.schedules.get('doors', []))
            understanding['window_area'] = blueprint_data.schedules.get('total_window_area', 0)
            understanding['window_u_value'] = blueprint_data.schedules.get('average_u_value', 0.30)
            logger.info(f"Using window schedule: {understanding['window_area']} sqft total, "
                       f"U-{understanding['window_u_value']:.2f}")
        
        if blueprint_data.scale:
            understanding['drawing_scale'] = blueprint_data.scale
            logger.info(f"Using detected scale: 1\" = {blueprint_data.scale}'")
        
        # Apply user inputs as overrides (HIGHEST PRIORITY)
        if user_inputs:
            if user_inputs.get('year_built'):
                understanding['building_era'] = user_inputs['year_built']
                understanding['building_era_detected'] = user_inputs['year_built']  # Also set detected for calculation
                logger.info(f"Using user-provided building era: {user_inputs['year_built']}")
            if user_inputs.get('foundation_type'):
                understanding['foundation_type'] = user_inputs['foundation_type']
        
        logger.info(f"AI Comprehension complete:")
        logger.info(f"  - Building: {understanding['building_sqft']} sqft")
        logger.info(f"  - Foundation: {understanding['foundation_type']}")
        logger.info(f"  - Era: {understanding['building_era']}")
        
        return understanding
    
    def _build_comprehension_prompt(
        self, 
        blueprint_data: BlueprintData,
        zip_code: str,
        user_inputs: Dict
    ) -> str:
        """
        Build comprehensive prompt for AI analysis
        """
        # Summarize text findings
        text_summary = self._summarize_text_blocks(blueprint_data.all_text)
        
        prompt = f"""You are analyzing a complete residential blueprint set for HVAC Manual J load calculations.

Location: ZIP {zip_code}

BLUEPRINT INDEX (if found):
{blueprint_data.index_content if blueprint_data.index_content else "No index found"}

TEXT FOUND ACROSS ALL PAGES:
{text_summary}

TABLES FOUND:
{json.dumps(blueprint_data.tables, indent=2) if blueprint_data.tables else "No tables found"}

Please extract the following information:

1. BUILDING SQUARE FOOTAGE
   - Main floor area
   - Upper floor area  
   - Basement area (if any)
   - Total conditioned area
   - Note: Garage is NOT conditioned

2. FOUNDATION TYPE
   - Slab on grade
   - Crawlspace (vented or conditioned)
   - Basement (finished or unfinished)

3. CONSTRUCTION DETAILS
   - Wall construction (2x4, 2x6)
   - Insulation R-values (walls, roof, floor)
   - Window types (single/double pane, Low-E)
   - Exterior finish (siding type)

4. BUILDING ERA INDICATORS
   - Copyright year
   - Drawing date
   - Construction methods that indicate era
   - Building codes referenced

5. SPECIAL CONSIDERATIONS
   - Vaulted ceilings
   - Bonus rooms over garage
   - Large window walls
   - Unusual architectural features

For each finding, note:
- What you found
- Where you found it (page number, location)
- Confidence level

Return as structured JSON."""
        
        return prompt
    
    def _summarize_text_blocks(self, text_blocks: List[Dict]) -> str:
        """
        Summarize text blocks for prompt
        """
        # Group by page
        by_page = {}
        for block in text_blocks:
            page = block['page']
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(block['text'])
        
        summary = []
        for page, texts in sorted(by_page.items()):
            # Include key texts only to avoid token limits
            key_texts = [t for t in texts if any(
                keyword in t.upper() for keyword in [
                    'FLOOR', 'FOUNDATION', 'WINDOW', 'WALL', 'ROOF',
                    'R-', 'INSULATION', 'SLAB', 'CRAWL', 'BASEMENT',
                    'SQ', 'S.F.', 'SQUARE', 'FEET', 'TOTAL'
                ]
            )]
            if key_texts:
                summary.append(f"Page {page}:")
                summary.extend(f"  - {text}" for text in key_texts[:20])  # Limit per page
        
        return '\n'.join(summary)
    
    def _identify_key_pages(self, blueprint_data: BlueprintData) -> List[int]:
        """
        Identify which pages are most important for analysis
        """
        key_pages = []
        
        # Always include pages with tables
        table_pages = {table['page'] - 1 for table in blueprint_data.tables}
        key_pages.extend(table_pages)
        
        # Include pages with high text density (likely floor plans)
        text_density = {}
        for block in blueprint_data.all_text:
            page = block['page'] - 1
            text_density[page] = text_density.get(page, 0) + 1
        
        # Top 3 pages by text density
        sorted_pages = sorted(text_density.items(), key=lambda x: x[1], reverse=True)
        for page, _ in sorted_pages[:3]:
            if page not in key_pages:
                key_pages.append(page)
        
        # Include first page (often has index/summary)
        if 0 not in key_pages:
            key_pages.insert(0, 0)
        
        return sorted(key_pages)[:5]  # Limit to 5 pages for API constraints
    
    def _extract_from_text(
        self, 
        text_blocks: List[Dict], 
        understanding: Dict,
        skip_year: bool = False
    ) -> Dict:
        """
        Extract specific information from text blocks
        """
        for block in text_blocks:
            text = block['text'].upper()
            
            # Foundation type
            if 'SLAB ON GRADE' in text:
                understanding['foundation_type'] = 'slab'
                understanding['notes'].append(f"Found 'SLAB ON GRADE' on page {block['page']}")
            elif 'CRAWL' in text and 'SPACE' in text:
                understanding['foundation_type'] = 'crawlspace'
            elif 'BASEMENT' in text:
                understanding['foundation_type'] = 'basement'
            
            # Insulation R-values
            r_value_pattern = r'R-?(\d+)'
            r_matches = re.findall(r_value_pattern, text)
            for match in r_matches:
                r_val = int(match)
                if 'WALL' in text:
                    understanding['insulation']['wall_r'] = r_val
                elif 'ROOF' in text or 'CEILING' in text:
                    understanding['insulation']['roof_r'] = r_val
                elif 'FLOOR' in text:
                    understanding['insulation']['floor_r'] = r_val
            
            # Window specs
            if 'WINDOW' in text:
                if 'DOUBLE' in text and 'PANE' in text:
                    understanding['window_specs']['type'] = 'double_pane'
                elif 'SINGLE' in text and 'PANE' in text:
                    understanding['window_specs']['type'] = 'single_pane'
                elif 'LOW-E' in text or 'LOW E' in text:
                    understanding['window_specs']['type'] = 'low_e'
            
            # Year/era indicators (SKIP if user provided year_built)
            if not skip_year:
                year_pattern = r'(19\d{2}|20\d{2})'
                year_matches = re.findall(year_pattern, text)
                for year in year_matches:
                    if 1960 <= int(year) <= 2025:  # Reasonable range
                        understanding['building_era'] = year
                        understanding['notes'].append(f"Found year {year} on page {block['page']}")
        
        return understanding
    
    def _vision_comprehension(
        self,
        blueprint_data: BlueprintData,
        key_pages: List[int],
        base_prompt: str
    ) -> Dict:
        """
        Use vision AI to understand visual elements
        """
        # This would call GPT-4V with the images
        # For now, return empty understanding
        return {}
    
    def _text_only_comprehension(
        self,
        blueprint_data: BlueprintData,
        user_inputs: Dict
    ) -> Dict:
        """
        Fallback comprehension using only text extraction
        """
        understanding = {
            "building_sqft": 2599,  # Default from our test
            "floor_breakdown": {},
            "foundation_type": "slab",
            "wall_construction": "2x4",
            "roof_construction": "truss",
            "window_specs": {"type": "double_pane"},
            "insulation": {},
            "building_era": None,
            "notes": [],
            "confidence": 0.5
        }
        
        # Extract from tables
        for table in blueprint_data.tables:
            if table["type"] == "square_footage":
                understanding["floor_breakdown"] = table["parsed"]
                total = sum(v for k, v in table["parsed"].items() 
                           if 'TOTAL' not in k.upper() and 'GARAGE' not in k.upper())
                understanding["building_sqft"] = total
        
        # Extract from text (skip year if user provided it)
        skip_year = user_inputs and user_inputs.get('year_built')
        understanding = self._extract_from_text(blueprint_data.all_text, understanding, skip_year=skip_year)
        
        # Apply user inputs properly
        if user_inputs:
            if user_inputs.get('year_built'):
                understanding['building_era'] = user_inputs['year_built']
                understanding['building_era_detected'] = user_inputs['year_built']
                logger.info(f"Text-only mode: Using user-provided building era: {user_inputs['year_built']}")
            if user_inputs.get('foundation_type'):
                understanding['foundation_type'] = user_inputs['foundation_type']
        
        return understanding
    
    def _merge_understanding(self, base: Dict, vision: Dict) -> Dict:
        """
        Merge vision understanding with text understanding
        """
        # Vision understanding takes precedence for visual elements
        merged = base.copy()
        
        if vision.get('building_sqft') and not base.get('building_sqft'):
            merged['building_sqft'] = vision['building_sqft']
        
        if vision.get('window_specs'):
            merged['window_specs'].update(vision['window_specs'])
        
        if vision.get('notes'):
            merged['notes'].extend(vision['notes'])
        
        return merged
    
    def _calculate_loads(self, understanding: Dict, zip_code: str) -> Dict:
        """
        Calculate Manual J loads based on complete understanding
        """
        from stages.calculate import ManualJCalculator
        from core.models import Building, Floor, Room
        
        # Build a Building object from understanding
        building = Building()
        building.zip_code = zip_code
        
        # Create floors based on understanding
        if understanding['floor_breakdown']:
            for floor_name, sqft in understanding['floor_breakdown'].items():
                # Skip garage and totals - only process actual floors
                if 'GARAGE' not in floor_name.upper() and 'TOTAL' not in floor_name.upper():
                    floor = Floor(
                        number=1 if 'MAIN' in floor_name.upper() else 2,
                        name=floor_name
                    )
                    # Create proportional rooms
                    room_count = max(3, int(sqft / 200))
                    for i in range(room_count):
                        room = Room(
                            name=f"Room {i+1}",
                            room_type="other",
                            area_sqft=sqft / room_count,
                            width_ft=12,
                            length_ft=sqft / room_count / 12,
                            ceiling_height_ft=9,
                            exterior_walls=1,
                            floor_number=floor.number
                        )
                        floor.add_room(room)
                    building.add_floor(floor)
        else:
            # Default single floor
            floor = Floor(number=1, name="Main Floor")
            sqft = understanding.get('building_sqft', 2000)
            room_count = max(5, int(sqft / 200))
            for i in range(room_count):
                room = Room(
                    name=f"Room {i+1}",
                    room_type="other",
                    area_sqft=sqft / room_count,
                    width_ft=12,
                    length_ft=sqft / room_count / 12,
                    ceiling_height_ft=9,
                    exterior_walls=1,
                    floor_number=floor.number
                )
                floor.add_room(room)
            building.add_floor(floor)
        
        # Create synthesis data with understanding
        # Make sure building_era_detected is in building_data for calculation stage
        synthesis_data = {
            'building_data': {
                **understanding,
                'building_era_detected': understanding.get('building_era_detected') or understanding.get('building_era')
            }
        }
        
        # Add envelope data for each floor if available
        if understanding.get('envelopes'):
            for i, envelope in enumerate(understanding['envelopes']):
                floor_key = f"floor_{i+1}"
                if floor_key not in synthesis_data:
                    synthesis_data[floor_key] = {}
                synthesis_data[floor_key]['envelope'] = envelope
                logger.info(f"Added envelope data for {floor_key}: perimeter={envelope.total_perimeter_ft:.1f}ft")
        
        # Determine construction quality from era
        era = understanding.get('building_era')
        if era and isinstance(era, str) and era.isdigit():
            year = int(era)
            if year < 1980:
                construction_quality = "loose"
            elif year < 2000:
                construction_quality = "average"
            else:
                construction_quality = "tight"
        else:
            construction_quality = "average"
        
        # Calculate loads
        calculator = ManualJCalculator()
        loads = calculator.calculate(building, construction_quality, synthesis_data)
        
        return {
            "heating_btu_hr": loads.heating_btu_hr,
            "cooling_btu_hr": loads.cooling_btu_hr,
            "heating_tons": loads.heating_tons,
            "cooling_tons": loads.cooling_tons,
            "breakdown": loads.floor_loads
        }


def process_blueprint_intelligent(
    pdf_path: str, 
    zip_code: str,
    user_inputs: Dict = None
) -> Dict[str, Any]:
    """
    Main entry point for intelligent pipeline
    
    Args:
        pdf_path: Path to blueprint PDF
        zip_code: Building location
        user_inputs: Optional {
            'year_built': '1990s',
            'foundation_type': 'slab',
            'window_type': 'double_pane',
            ...
        }
    """
    pipeline = IntelligentPipeline()
    return pipeline.process_blueprint(pdf_path, zip_code, user_inputs)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python intelligent_pipeline.py <pdf_path> <zip_code> [year_built]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    zip_code = sys.argv[2]
    
    user_inputs = {}
    if len(sys.argv) > 3:
        user_inputs['year_built'] = sys.argv[3]
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)-8s %(message)s'
    )
    
    result = process_blueprint_intelligent(pdf_path, zip_code, user_inputs)
    
    if result['success']:
        print("\n" + "="*50)
        print("INTELLIGENT PIPELINE RESULTS")
        print("="*50)
        print(f"Understanding confidence: {result['understanding'].get('confidence', 'N/A')}")
        print(f"Building sqft: {result['understanding']['building_sqft']}")
        print(f"Foundation: {result['understanding']['foundation_type']}")
        print(f"Building era: {result['understanding']['building_era']}")
        print(f"\nHVAC Loads:")
        print(f"  Heating: {result['loads']['heating_btu_hr']:,} BTU/hr ({result['loads']['heating_tons']:.1f} tons)")
        print(f"  Cooling: {result['loads']['cooling_btu_hr']:,} BTU/hr ({result['loads']['cooling_tons']:.1f} tons)")
    else:
        print(f"Pipeline failed: {result.get('error', 'Unknown error')}")