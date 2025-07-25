"""
Blueprint Data Extraction Service
Systematic regex-based extraction following o3-model approach
Designed for maximum accuracy in Manual J load calculations
"""
import re
import logging
import pdfplumber
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class BuildingData:
    """Structured building data extracted from blueprints"""
    floor_area_ft2: Optional[float] = None
    wall_insulation: Dict[str, float] = None  # {"cavity": 21, "continuous": 5}
    ceiling_insulation: float = None  # R-value
    window_schedule: Dict[str, Any] = None  # {"total_area": 150, "u_value": 0.30, "shgc": 0.65}
    air_tightness: float = None  # ACH50
    room_dimensions: List[Dict] = None  # [{"name": "Living", "area": 250, "perimeter": 64}]
    orientation: Optional[str] = None  # North arrow direction
    foundation_type: Optional[str] = None  # slab, crawl, basement
    confidence_scores: Dict[str, float] = None

class BlueprintExtractor:
    """
    Systematic blueprint data extraction using deterministic patterns
    Following o3-model methodology for maximum accuracy
    """
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        logger.info("Blueprint extractor initialized with systematic patterns")
    
    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for systematic extraction"""
        return {
            # Building insulation patterns
            "r_value": re.compile(r"R[-\s]?(\d{1,2})", re.IGNORECASE),
            "r_value_with_ci": re.compile(r"R[-\s]?(\d{1,2})\+(\d{1,2})ci", re.IGNORECASE),
            "u_value": re.compile(r"U[=\s]?(\d?\.\d{2})", re.IGNORECASE),
            
            # Area and dimension patterns
            "conditioned_area": re.compile(r"(\d{1,4},?\d{0,3})\s*(?:sq\.?\s*ft|sf|square\s+feet)", re.IGNORECASE),
            "room_dimensions": re.compile(r"(\d+)'\-?(\d+)\"?\s*[xX×]\s*(\d+)'\-?(\d+)\"?", re.IGNORECASE),
            "linear_dimension": re.compile(r"(\d+)'\-(\d+)\"", re.IGNORECASE),
            
            # Air tightness patterns
            "ach50": re.compile(r"(\d+\.?\d*)\s*ACH50", re.IGNORECASE),
            "blower_door": re.compile(r"(\d+\.?\d*)\s*cfm50", re.IGNORECASE),
            
            # Window schedule patterns
            "window_area": re.compile(r"glazing.*?(\d{1,3})\s*sf", re.IGNORECASE),
            "window_u_factor": re.compile(r"window.*?U[=\s]?(\d?\.\d{2})", re.IGNORECASE),
            "shgc": re.compile(r"SHGC[=\s]?(\d?\.\d{2})", re.IGNORECASE),
            
            # Foundation and structure
            "foundation": re.compile(r"(slab|crawl\s*space|basement|pier)", re.IGNORECASE),
            "ceiling_height": re.compile(r"ceiling.*?(\d+)'\-?(\d+)\"?", re.IGNORECASE),
            
            # Orientation
            "north_arrow": re.compile(r"north|N\s*↑|true\s*north", re.IGNORECASE)
        }
    
    async def extract_building_data(self, pdf_path: str) -> BuildingData:
        """
        Extract structured building data from PDF blueprint
        
        Args:
            pdf_path: Path to PDF blueprint file
            
        Returns:
            BuildingData with extracted information and confidence scores
        """
        try:
            logger.info(f"Starting systematic extraction from {pdf_path}")
            
            # Extract text from all pages
            raw_text = self._extract_pdf_text(pdf_path)
            
            # Apply extraction patterns
            building_data = BuildingData()
            confidence_scores = {}
            
            # 1. Extract conditioned floor area
            building_data.floor_area_ft2, confidence_scores["floor_area"] = self._extract_floor_area(raw_text)
            
            # 2. Extract envelope R-values
            building_data.wall_insulation, confidence_scores["wall_insulation"] = self._extract_wall_insulation(raw_text)
            building_data.ceiling_insulation, confidence_scores["ceiling_insulation"] = self._extract_ceiling_insulation(raw_text)
            
            # 3. Extract window schedule
            building_data.window_schedule, confidence_scores["windows"] = self._extract_window_data(raw_text)
            
            # 4. Extract air tightness
            building_data.air_tightness, confidence_scores["air_tightness"] = self._extract_air_tightness(raw_text)
            
            # 5. Extract room dimensions
            building_data.room_dimensions, confidence_scores["room_dimensions"] = self._extract_room_dimensions(raw_text)
            
            # 6. Extract building characteristics
            building_data.foundation_type, confidence_scores["foundation"] = self._extract_foundation_type(raw_text)
            building_data.orientation, confidence_scores["orientation"] = self._extract_orientation(raw_text)
            
            building_data.confidence_scores = confidence_scores
            
            # Log extraction summary
            self._log_extraction_summary(building_data)
            
            return building_data
            
        except Exception as e:
            logger.error(f"Blueprint extraction failed: {e}")
            raise
    
    def extract_building_data_sync(self, pdf_path: str) -> BuildingData:
        """
        Synchronous version of extract_building_data for Celery tasks
        
        Args:
            pdf_path: Path to PDF blueprint file
            
        Returns:
            BuildingData with extracted information and confidence scores
        """
        try:
            logger.info(f"Starting systematic extraction from {pdf_path}")
            
            # Extract text from all pages
            raw_text = self._extract_pdf_text(pdf_path)
            
            # Apply extraction patterns
            building_data = BuildingData()
            confidence_scores = {}
            
            # 1. Extract conditioned floor area
            building_data.floor_area_ft2, confidence_scores["floor_area"] = self._extract_floor_area(raw_text)
            
            # 2. Extract envelope R-values
            building_data.wall_insulation, confidence_scores["wall_insulation"] = self._extract_wall_insulation(raw_text)
            building_data.ceiling_insulation, confidence_scores["ceiling_insulation"] = self._extract_ceiling_insulation(raw_text)
            
            # 3. Extract window schedule
            building_data.window_schedule, confidence_scores["windows"] = self._extract_window_data(raw_text)
            
            # 4. Extract air tightness
            building_data.air_tightness, confidence_scores["air_tightness"] = self._extract_air_tightness(raw_text)
            
            # 5. Extract room dimensions
            building_data.room_dimensions, confidence_scores["room_dimensions"] = self._extract_room_dimensions(raw_text)
            
            # 6. Extract building characteristics
            building_data.foundation_type, confidence_scores["foundation"] = self._extract_foundation_type(raw_text)
            building_data.orientation, confidence_scores["orientation"] = self._extract_orientation(raw_text)
            
            building_data.confidence_scores = confidence_scores
            
            # Log extraction summary
            self._log_extraction_summary(building_data)
            
            return building_data
            
        except Exception as e:
            logger.error(f"Blueprint extraction failed: {e}")
            raise
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from all PDF pages"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_pages = []
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():  # Skip empty pages
                        text_pages.append(f"PAGE_{page_num + 1}:\n{page_text}\n")
                
                full_text = "\n".join(text_pages)
                logger.info(f"Extracted {len(full_text)} characters from {len(text_pages)} pages")
                return full_text
                
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise
    
    def _extract_floor_area(self, text: str) -> Tuple[Optional[float], float]:
        """Extract conditioned floor area with confidence scoring"""
        matches = self.patterns["conditioned_area"].findall(text)
        
        if matches:
            # Convert string numbers to float, handling commas
            areas = [float(match.replace(",", "")) for match in matches]
            
            # Use the largest reasonable area (likely the total)
            floor_area = max(area for area in areas if 500 <= area <= 10000)
            confidence = 0.9 if len(matches) == 1 else 0.7
            
            logger.info(f"Extracted floor area: {floor_area} sq ft (confidence: {confidence})")
            return floor_area, confidence
        
        logger.warning("No conditioned floor area found")
        return None, 0.0
    
    def _extract_wall_insulation(self, text: str) -> Tuple[Optional[Dict], float]:
        """Extract wall insulation R-values"""
        # Look for R-value + continuous insulation pattern first
        ci_matches = self.patterns["r_value_with_ci"].findall(text)
        if ci_matches:
            cavity_r = int(ci_matches[0][0])
            ci_r = int(ci_matches[0][1])
            effective_r = cavity_r + ci_r
            
            wall_insulation = {
                "cavity_r": cavity_r,
                "continuous_r": ci_r,
                "effective_r": effective_r
            }
            
            logger.info(f"Extracted wall insulation: R-{cavity_r}+{ci_r}ci = R-{effective_r} effective")
            return wall_insulation, 0.9
        
        # Fall back to simple R-value pattern
        r_matches = self.patterns["r_value"].findall(text)
        if r_matches:
            # Find wall-related R-values (typically 13-30 range)
            wall_r_values = [int(r) for r in r_matches if 10 <= int(r) <= 35]
            
            if wall_r_values:
                wall_r = max(wall_r_values)  # Use highest reasonable value
                wall_insulation = {"effective_r": wall_r}
                
                logger.info(f"Extracted wall insulation: R-{wall_r}")
                return wall_insulation, 0.6
        
        logger.warning("No wall insulation values found")
        return None, 0.0
    
    def _extract_ceiling_insulation(self, text: str) -> Tuple[Optional[float], float]:
        """Extract ceiling/attic insulation R-value"""
        r_matches = self.patterns["r_value"].findall(text)
        
        if r_matches:
            # Ceiling R-values are typically 30-60
            ceiling_r_values = [int(r) for r in r_matches if 25 <= int(r) <= 70]
            
            if ceiling_r_values:
                ceiling_r = max(ceiling_r_values)  # Use highest value (likely attic)
                
                logger.info(f"Extracted ceiling insulation: R-{ceiling_r}")
                return float(ceiling_r), 0.7
        
        logger.warning("No ceiling insulation values found")
        return None, 0.0
    
    def _extract_window_data(self, text: str) -> Tuple[Optional[Dict], float]:
        """Extract window schedule data"""
        window_data = {}
        confidence = 0.0
        
        # Extract window area
        area_matches = self.patterns["window_area"].findall(text)
        if area_matches:
            window_data["total_area"] = float(area_matches[0])
            confidence += 0.3
        
        # Extract U-factor
        u_matches = self.patterns["window_u_factor"].findall(text)
        if u_matches:
            window_data["u_value"] = float(u_matches[0])
            confidence += 0.35
        
        # Extract SHGC
        shgc_matches = self.patterns["shgc"].findall(text)
        if shgc_matches:
            window_data["shgc"] = float(shgc_matches[0])
            confidence += 0.35
        
        if window_data:
            logger.info(f"Extracted window data: {window_data}")
            return window_data, confidence
        
        logger.warning("No window schedule data found")
        return None, 0.0
    
    def _extract_air_tightness(self, text: str) -> Tuple[Optional[float], float]:
        """Extract air tightness values"""
        # Look for ACH50 first
        ach50_matches = self.patterns["ach50"].findall(text)
        if ach50_matches:
            ach50 = float(ach50_matches[0])
            logger.info(f"Extracted air tightness: {ach50} ACH50")
            return ach50, 0.9
        
        # Fall back to CFM50 and convert
        cfm50_matches = self.patterns["blower_door"].findall(text)
        if cfm50_matches:
            cfm50 = float(cfm50_matches[0])
            # Need building volume to convert, so mark as lower confidence
            logger.info(f"Found blower door result: {cfm50} CFM50 (needs volume for ACH50)")
            return cfm50, 0.5  # Lower confidence without volume
        
        logger.warning("No air tightness values found")
        return None, 0.0
    
    def _extract_room_dimensions(self, text: str) -> Tuple[Optional[List[Dict]], float]:
        """Extract room dimensions and calculate areas"""
        dimension_matches = self.patterns["room_dimensions"].findall(text)
        
        if dimension_matches:
            rooms = []
            for match in dimension_matches:
                length_ft = int(match[0]) + int(match[1]) / 12
                width_ft = int(match[2]) + int(match[3]) / 12
                area = length_ft * width_ft
                perimeter = 2 * (length_ft + width_ft)
                
                rooms.append({
                    "length_ft": length_ft,
                    "width_ft": width_ft,
                    "area_ft2": area,
                    "perimeter_ft": perimeter
                })
            
            logger.info(f"Extracted {len(rooms)} room dimensions")
            return rooms, 0.8
        
        logger.warning("No room dimensions found")
        return None, 0.0
    
    def _extract_foundation_type(self, text: str) -> Tuple[Optional[str], float]:
        """Extract foundation type"""
        foundation_matches = self.patterns["foundation"].findall(text)
        
        if foundation_matches:
            foundation_type = foundation_matches[0].lower().replace(" ", "_")
            logger.info(f"Extracted foundation type: {foundation_type}")
            return foundation_type, 0.8
        
        logger.warning("No foundation type found")
        return None, 0.0
    
    def _extract_orientation(self, text: str) -> Tuple[Optional[str], float]:
        """Extract building orientation from north arrow"""
        north_matches = self.patterns["north_arrow"].findall(text)
        
        if north_matches:
            logger.info("Found north arrow indicator")
            return "north_indicated", 0.6
        
        logger.warning("No orientation information found")
        return None, 0.0
    
    def _log_extraction_summary(self, data: BuildingData):
        """Log comprehensive extraction summary"""
        logger.info("=== BLUEPRINT EXTRACTION SUMMARY ===")
        logger.info(f"Floor Area: {data.floor_area_ft2} sq ft (confidence: {data.confidence_scores.get('floor_area', 0):.1f})")
        logger.info(f"Wall Insulation: {data.wall_insulation} (confidence: {data.confidence_scores.get('wall_insulation', 0):.1f})")
        logger.info(f"Ceiling Insulation: R-{data.ceiling_insulation} (confidence: {data.confidence_scores.get('ceiling_insulation', 0):.1f})")
        logger.info(f"Windows: {data.window_schedule} (confidence: {data.confidence_scores.get('windows', 0):.1f})")
        logger.info(f"Air Tightness: {data.air_tightness} (confidence: {data.confidence_scores.get('air_tightness', 0):.1f})")
        logger.info(f"Rooms: {len(data.room_dimensions) if data.room_dimensions else 0} rooms found")
        logger.info(f"Foundation: {data.foundation_type} (confidence: {data.confidence_scores.get('foundation', 0):.1f})")
        
        # Calculate overall confidence
        avg_confidence = sum(data.confidence_scores.values()) / len(data.confidence_scores) if data.confidence_scores else 0
        logger.info(f"Overall Extraction Confidence: {avg_confidence:.2f}")
        logger.info("=" * 40)