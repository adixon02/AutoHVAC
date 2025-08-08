"""
OCR-based Room Estimator
Uses text extraction to find room labels and dimensions
A pragmatic approach when geometric detection fails
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import fitz  # PyMuPDF

from services.ocr_extractor import OCRExtractor
from services.scale_extractor import scale_extractor
from services.page_classifier import page_classifier

logger = logging.getLogger(__name__)


@dataclass
class OCRRoom:
    """Room detected from OCR text"""
    name: str
    dimensions: Optional[Tuple[float, float]]  # width, height in feet
    area_sqft: float
    confidence: float
    text_source: str  # The raw text that was parsed


class OCRRoomEstimator:
    """
    Extract rooms using OCR text analysis
    Finds room labels and dimensions in blueprint text
    """
    
    def __init__(self):
        self.ocr = OCRExtractor(use_gpu=False)
        
        # Common room types with typical size ranges (sq ft)
        self.room_size_ranges = {
            'master bedroom': (150, 400),
            'bedroom': (80, 200),
            'bathroom': (30, 100),
            'master bath': (50, 150),
            'kitchen': (100, 300),
            'living room': (150, 400),
            'family room': (150, 400),
            'dining room': (100, 250),
            'garage': (200, 600),
            'closet': (10, 50),
            'walk-in closet': (25, 100),
            'hallway': (20, 100),
            'entry': (30, 100),
            'foyer': (40, 150),
            'office': (80, 200),
            'den': (100, 200),
            'laundry': (30, 80),
            'pantry': (15, 50),
            'utility': (30, 100),
            'great room': (300, 600),
            'rec room': (200, 500),
            'basement': (400, 1500),
            'attic': (200, 1000)
        }
    
    def estimate_rooms_from_ocr(
        self,
        pdf_path: str,
        page_num: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Estimate rooms by extracting text and finding room labels/dimensions
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (None = auto-detect)
            
        Returns:
            Dictionary with room data
        """
        logger.info("Starting OCR-based room estimation...")
        
        # Find floor plan page
        if page_num is None:
            page_num = page_classifier.find_best_floor_plan_page(pdf_path) or 0
        
        # Extract all text from the page
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Get text with positions
        text_dict = page.get_text("dict")
        text_items = self._extract_text_items(text_dict)
        
        # Also get simple text for scale detection
        page_text = page.get_text()
        
        doc.close()
        
        # Extract scale
        scale_result = scale_extractor.extract_scale(page_text, page_num)
        logger.info(f"Scale: {scale_result.scale_notation} ({scale_result.confidence:.0%} confidence)")
        
        # Find room mentions in text
        rooms = self._find_rooms_in_text(text_items)
        logger.info(f"Found {len(rooms)} rooms from OCR text")
        
        # If we didn't find enough rooms, use typical layout estimation
        if len(rooms) < 5:
            logger.info("Few rooms found, adding estimated rooms based on typical layout")
            rooms = self._add_estimated_rooms(rooms)
        
        # Calculate total area
        total_area = sum(room.area_sqft for room in rooms)
        
        # Compile results
        return {
            'success': True,
            'rooms': [
                {
                    'name': room.name,
                    'area_sqft': room.area_sqft,
                    'dimensions': room.dimensions,
                    'confidence': room.confidence,
                    'source': 'OCR estimation'
                }
                for room in rooms
            ],
            'total_area': round(total_area, 0),
            'scale': {
                'notation': scale_result.scale_notation,
                'confidence': scale_result.confidence
            },
            'metadata': {
                'page_number': page_num + 1,
                'method': 'OCR-based estimation',
                'rooms_found': len(rooms)
            }
        }
    
    def _extract_text_items(self, text_dict: Dict) -> List[Dict[str, Any]]:
        """Extract individual text items with positions"""
        items = []
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            items.append({
                                'text': text,
                                'bbox': span.get("bbox", [0, 0, 0, 0]),
                                'font': span.get("font", ""),
                                'size': span.get("size", 0)
                            })
        
        return items
    
    def _find_rooms_in_text(self, text_items: List[Dict]) -> List[OCRRoom]:
        """Find room labels and dimensions in text"""
        rooms = []
        processed_texts = set()
        
        # Patterns for room labels with dimensions
        dimension_patterns = [
            # "BEDROOM 12'-0" x 10'-6""
            r"(\w+(?:\s+\w+)?)\s+(\d+)['\"][\s-]*(\d+)?[\"'\s]*[xX×]\s*(\d+)['\"][\s-]*(\d+)?[\"']*",
            # "LIVING ROOM (15x12)"
            r'(\w+(?:\s+\w+)?)\s*\((\d+)\s*[xX×]\s*(\d+)\)',
            # "Master Bath 8x10"
            r'(\w+(?:\s+\w+)?)\s+(\d+)\s*[xX×]\s*(\d+)',
            # Just room names
            r'(master\s+bedroom|bedroom|bathroom|master\s+bath|kitchen|living\s+room|dining\s+room|family\s+room|garage|closet|office|den)',
        ]
        
        for item in text_items:
            text = item['text']
            text_lower = text.lower()
            
            # Skip if already processed
            if text in processed_texts:
                continue
            
            # Try to match patterns
            for pattern in dimension_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    processed_texts.add(text)
                    
                    # Extract room name
                    room_name = match.group(1).strip()
                    
                    # Extract dimensions if available
                    dimensions = None
                    area = None
                    
                    if len(match.groups()) >= 3:
                        try:
                            # Simple dimensions (e.g., "12x10")
                            if len(match.groups()) == 3:
                                width = float(match.group(2))
                                height = float(match.group(3))
                                dimensions = (width, height)
                                area = width * height
                            # Feet and inches (e.g., "12'-6" x 10'-0"")
                            elif len(match.groups()) >= 5:
                                width_ft = float(match.group(2))
                                width_in = float(match.group(3)) if match.group(3) else 0
                                height_ft = float(match.group(4))
                                height_in = float(match.group(5)) if match.group(5) else 0
                                
                                width = width_ft + width_in / 12
                                height = height_ft + height_in / 12
                                dimensions = (width, height)
                                area = width * height
                        except (ValueError, TypeError):
                            pass
                    
                    # If no dimensions found, estimate based on room type
                    if area is None:
                        area = self._estimate_room_size(room_name)
                        confidence = 0.5  # Lower confidence for estimated sizes
                    else:
                        confidence = 0.8  # Higher confidence when dimensions are explicit
                    
                    rooms.append(OCRRoom(
                        name=room_name.title(),
                        dimensions=dimensions,
                        area_sqft=area,
                        confidence=confidence,
                        text_source=text
                    ))
                    break
        
        return rooms
    
    def _estimate_room_size(self, room_name: str) -> float:
        """Estimate room size based on typical dimensions"""
        room_name_lower = room_name.lower()
        
        # Check against known room types
        for room_type, (min_size, max_size) in self.room_size_ranges.items():
            if room_type in room_name_lower:
                # Return average of typical range
                return (min_size + max_size) / 2
        
        # Default size for unknown room types
        return 120  # Average room size
    
    def _add_estimated_rooms(self, existing_rooms: List[OCRRoom]) -> List[OCRRoom]:
        """Add estimated rooms for a typical residential layout"""
        rooms = list(existing_rooms)
        existing_types = {room.name.lower() for room in rooms}
        
        # Typical residential layout if not already found
        typical_rooms = [
            ('Living Room', 250),
            ('Kitchen', 150),
            ('Master Bedroom', 200),
            ('Bedroom 2', 120),
            ('Bedroom 3', 110),
            ('Master Bathroom', 80),
            ('Bathroom 2', 50),
            ('Dining Room', 140),
            ('Entry', 60),
            ('Hallway', 80),
            ('Garage', 400)
        ]
        
        for room_name, area in typical_rooms:
            if room_name.lower() not in existing_types:
                # Only add if we need more rooms
                if len(rooms) < 10:
                    rooms.append(OCRRoom(
                        name=room_name,
                        dimensions=None,
                        area_sqft=area,
                        confidence=0.3,  # Low confidence for fully estimated
                        text_source="Estimated based on typical layout"
                    ))
        
        return rooms


# Global instance
ocr_estimator = OCRRoomEstimator()