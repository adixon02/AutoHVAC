"""
OCR Extraction Module for Blueprint Analysis
Uses PaddleOCR for accurate text extraction from technical drawings
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logging.warning("PaddleOCR not available - OCR extraction will be limited")

logger = logging.getLogger(__name__)


@dataclass
class DimensionData:
    """Extracted dimension information"""
    text: str
    width_ft: float
    length_ft: float
    bbox: List[List[float]]
    confidence: float
    

@dataclass
class TextRegion:
    """Text region with location and content"""
    text: str
    bbox: List[List[float]]
    confidence: float
    region_type: str  # 'dimension', 'room_label', 'annotation', 'scale', 'other'


class OCRExtractor:
    """Extract text and dimensions from blueprint images using PaddleOCR"""
    
    def __init__(self, use_gpu: bool = False):
        """Initialize OCR extractor
        
        Args:
            use_gpu: Whether to use GPU acceleration (requires CUDA)
        """
        self.use_gpu = use_gpu
        self.ocr = None
        
        if PADDLEOCR_AVAILABLE:
            try:
                # Initialize PaddleOCR with English language
                self.ocr = PaddleOCR(
                    use_angle_cls=True,  # Enable text angle classification
                    lang='en',
                    use_gpu=use_gpu,
                    show_log=False,  # Reduce logging noise
                    drop_score=0.3,  # Filter low confidence text
                    det_db_score_mode='slow'  # Better accuracy for technical drawings
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
                self.ocr = None
    
    def extract_all_text(self, image: np.ndarray) -> List[TextRegion]:
        """Extract all text from blueprint image
        
        Args:
            image: OpenCV image array (BGR format)
            
        Returns:
            List of TextRegion objects
        """
        if not self.ocr:
            logger.warning("OCR not available - returning empty results")
            return []
        
        try:
            # Run OCR on the image
            result = self.ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                logger.warning("No text detected in image")
                return []
            
            text_regions = []
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]
                
                # Classify the text region type
                region_type = self._classify_text_region(text)
                
                text_regions.append(TextRegion(
                    text=text,
                    bbox=bbox,
                    confidence=confidence,
                    region_type=region_type
                ))
            
            logger.info(f"Extracted {len(text_regions)} text regions")
            return text_regions
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return []
    
    def extract_dimensions(self, image: np.ndarray) -> List[DimensionData]:
        """Extract room dimensions from blueprint
        
        Args:
            image: OpenCV image array
            
        Returns:
            List of DimensionData objects
        """
        text_regions = self.extract_all_text(image)
        dimensions = []
        
        # Common dimension patterns in blueprints
        patterns = [
            # Pattern 1: 15'-6" x 12'-0" or 15'6" x 12'0"
            r"(\d+)'[\s-]*(\d+)?\"?\s*[xX×]\s*(\d+)'[\s-]*(\d+)?\"?",
            # Pattern 2: 15.5' x 12.0'
            r"(\d+\.?\d*)'?\s*[xX×]\s*(\d+\.?\d*)'?",
            # Pattern 3: 15x12 (assumes feet)
            r"(\d+)\s*[xX×]\s*(\d+)(?!\s*['\"])",
            # Pattern 4: 15'-6" (single dimension)
            r"(\d+)'[\s-]*(\d+)?\"?(?!\s*[xX×])"
        ]
        
        for region in text_regions:
            if region.region_type != 'dimension':
                continue
                
            text = region.text.strip()
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    for match in matches:
                        try:
                            dimension = self._parse_dimension_match(match, pattern)
                            if dimension:
                                dimensions.append(DimensionData(
                                    text=text,
                                    width_ft=dimension[0],
                                    length_ft=dimension[1],
                                    bbox=region.bbox,
                                    confidence=region.confidence
                                ))
                                break
                        except ValueError:
                            continue
        
        logger.info(f"Extracted {len(dimensions)} dimensions")
        return dimensions
    
    def extract_dimensions_from_regions(self, text_regions: List[TextRegion]) -> List[DimensionData]:
        """Extract dimensions from already extracted text regions
        
        Args:
            text_regions: List of TextRegion objects
            
        Returns:
            List of DimensionData objects
        """
        dimensions = []
        
        # Common dimension patterns in blueprints
        patterns = [
            # Pattern 1: 15'-6" x 12'-0" or 15'6" x 12'0"
            r"(\d+)'[\s-]*(\d+)?\"?\s*[xX×]\s*(\d+)'[\s-]*(\d+)?\"?",
            # Pattern 2: 15.5' x 12.0'
            r"(\d+\.?\d*)'?\s*[xX×]\s*(\d+\.?\d*)'?",
            # Pattern 3: 15x12 (assumes feet)
            r"(\d+)\s*[xX×]\s*(\d+)(?!\s*['\"])",
            # Pattern 4: 15'-6" (single dimension)
            r"(\d+)'[\s-]*(\d+)?\"?(?!\s*[xX×])"
        ]
        
        for region in text_regions:
            text = region.text.strip()
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    for match in matches:
                        try:
                            dimension = self._parse_dimension_match(match, pattern)
                            if dimension:
                                dimensions.append(DimensionData(
                                    text=text,
                                    width_ft=dimension[0],
                                    length_ft=dimension[1],
                                    bbox=region.bbox,
                                    confidence=region.confidence
                                ))
                                break
                        except ValueError:
                            continue
        
        return dimensions
    
    def extract_room_labels(self, image: np.ndarray) -> List[TextRegion]:
        """Extract room labels and names
        
        Args:
            image: OpenCV image array
            
        Returns:
            List of TextRegion objects containing room labels
        """
        text_regions = self.extract_all_text(image)
        room_labels = []
        
        # Common room name patterns
        room_keywords = [
            'bedroom', 'bed', 'br', 'master',
            'bathroom', 'bath', 'ba',
            'kitchen', 'kit',
            'living', 'family', 'great room',
            'dining', 'den', 'office', 'study',
            'garage', 'laundry', 'utility',
            'closet', 'cl', 'wic',  # walk-in closet
            'hallway', 'hall', 'entry', 'foyer',
            'pantry', 'mudroom'
        ]
        
        for region in text_regions:
            text_lower = region.text.lower().strip()
            
            # Check if text contains room keywords
            for keyword in room_keywords:
                if keyword in text_lower:
                    room_labels.append(region)
                    break
        
        logger.info(f"Extracted {len(room_labels)} room labels")
        return room_labels
    
    def extract_scale_notation(self, image: np.ndarray) -> Optional[str]:
        """Extract scale notation from blueprint
        
        Args:
            image: OpenCV image array
            
        Returns:
            Scale notation string (e.g., "1/4\" = 1'-0\"") or None
        """
        text_regions = self.extract_all_text(image)
        
        # Scale notation patterns
        scale_patterns = [
            r"1/(\d+)[\"']?\s*=\s*1'[\s-]*0[\"']?",  # 1/4" = 1'-0"
            r"(\d+)[\"']?\s*=\s*(\d+)'",  # 1" = 8'
            r"scale[:]\s*1/(\d+)",  # Scale: 1/4
            r"1[:]\s*(\d+)"  # 1:48
        ]
        
        for region in text_regions:
            text = region.text.strip()
            
            for pattern in scale_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    logger.info(f"Found scale notation: {text}")
                    return text
        
        return None
    
    def extract_floor_label(self, image: np.ndarray) -> Optional[str]:
        """Extract floor level label from blueprint
        
        Args:
            image: OpenCV image array
            
        Returns:
            Floor label (e.g., "First Floor", "Second Floor") or None
        """
        text_regions = self.extract_all_text(image)
        
        # Floor level patterns
        floor_patterns = [
            r"(first|1st|ground)\s+floor",
            r"(second|2nd|upper)\s+floor",
            r"(basement|lower)\s+level",
            r"floor\s+(1|2|3)",
            r"level\s+(1|2|3)"
        ]
        
        for region in text_regions:
            text = region.text.strip()
            
            for pattern in floor_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    logger.info(f"Found floor label: {text}")
                    return text
        
        return None
    
    def _classify_text_region(self, text: str) -> str:
        """Classify the type of text region
        
        Args:
            text: Text content
            
        Returns:
            Region type: 'dimension', 'room_label', 'scale', 'annotation', 'other'
        """
        text_lower = text.lower().strip()
        
        # Check for dimensions
        if re.search(r"\d+['\"]|x\s*\d+|\d+\s*x", text):
            return 'dimension'
        
        # Check for scale notation
        if re.search(r"scale|1/\d+|\d+\s*=\s*\d+", text_lower):
            return 'scale'
        
        # Check for room labels
        room_keywords = ['room', 'bedroom', 'bath', 'kitchen', 'living', 'dining', 
                        'garage', 'closet', 'hall', 'entry', 'office', 'den']
        if any(keyword in text_lower for keyword in room_keywords):
            return 'room_label'
        
        # Check for annotations
        if len(text) > 20 or any(char in text for char in ['(', ')', 'note', 'typ']):
            return 'annotation'
        
        return 'other'
    
    def _parse_dimension_match(self, match: Tuple, pattern: str) -> Optional[Tuple[float, float]]:
        """Parse regex match into dimension values
        
        Args:
            match: Regex match groups
            pattern: Pattern that was matched
            
        Returns:
            Tuple of (width_ft, length_ft) or None
        """
        try:
            if "x 12'-0\"" in pattern or "×" in pattern and len(match) >= 4:
                # Pattern with feet and inches
                width_ft = float(match[0])
                width_in = float(match[1]) if match[1] else 0
                length_ft = float(match[2])
                length_in = float(match[3]) if match[3] else 0
                
                width_total = width_ft + width_in / 12
                length_total = length_ft + length_in / 12
                
            elif len(match) == 2:
                # Simple pattern (feet only)
                width_total = float(match[0])
                length_total = float(match[1])
                
            else:
                return None
            
            # Validate reasonable room dimensions (3-50 feet)
            if 3 <= width_total <= 50 and 3 <= length_total <= 50:
                return (width_total, length_total)
            
        except (ValueError, IndexError):
            pass
        
        return None


# Create singleton instance
ocr_extractor = OCRExtractor()