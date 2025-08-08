"""
Hybrid Blueprint Parser - Combines Drawing Extraction with OCR
Gets ALL available data for intelligent HVAC calculations
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import fitz  # PyMuPDF
import pdfplumber

# Import our optimized components
from services.ocr_extractor import OCRExtractor
from services.scale_extractor import scale_extractor
from services.page_classifier import page_classifier

logger = logging.getLogger(__name__)


@dataclass 
class RoomData:
    """Complete room data from all sources"""
    name: str
    rect: Tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF coords
    area_sqft: float
    width_ft: float
    height_ft: float
    source: str  # 'rectangle', 'ocr', 'combined'
    confidence: float
    ocr_labels: List[str]  # Any OCR text found inside


class HybridBlueprintParser:
    """
    THE WORLD'S SMARTEST PDF PARSER for HVAC calculations
    Extracts ALL available data - no sampling, no skipping
    """
    
    def __init__(self):
        self.ocr = OCRExtractor(use_gpu=False)
        
    def parse_blueprint(
        self,
        pdf_path: str,
        zip_code: str = "99006"
    ) -> Dict[str, Any]:
        """
        Extract ALL room data using every available method
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Location zip code
            
        Returns:
            Complete blueprint data with all rooms found
        """
        start_time = time.time()
        logger.info(f"Starting HYBRID parsing of {pdf_path}")
        
        # Step 1: Find the best floor plan page
        page_num = page_classifier.find_best_floor_plan_page(pdf_path)
        if page_num is None:
            page_num = 0
            logger.warning("No floor plan detected, using first page")
        else:
            logger.info(f"Found floor plan on page {page_num + 1}")
        
        # Step 2: Extract scale with high confidence
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                page_text = page.extract_text() or ""
            else:
                page_text = ""
        
        scale_result = scale_extractor.extract_scale(page_text, page_num)
        pixels_per_foot = scale_result.pixels_per_foot
        logger.info(f"Scale: {scale_result.scale_notation} = {pixels_per_foot:.1f} px/ft ({scale_result.confidence:.0%} confidence)")
        
        # Step 3: Get ALL rectangles using direct PyMuPDF extraction
        logger.info("Extracting ALL drawing rectangles (no sampling!)...")
        rectangles = []
        
        try:
            doc = fitz.open(pdf_path)
            if page_num < len(doc):
                page = doc[page_num]
                
                # Get all drawings from the page
                page_drawings = page.get_drawings()
                
                # Extract ALL rectangles - no sampling!
                for drawing in page_drawings:
                    rect_val = drawing.get('rect')
                    if rect_val is not None:
                        # Convert rect to list format
                        if hasattr(rect_val, 'x0'):
                            rect = [float(rect_val.x0), float(rect_val.y0), 
                                   float(rect_val.x1), float(rect_val.y1)]
                        else:
                            rect = list(rect_val)
                        
                        # Basic validation
                        if len(rect) >= 4 and rect[2] > rect[0] and rect[3] > rect[1]:
                            rectangles.append(rect)
                
                logger.info(f"Extracted {len(rectangles)} rectangles from PyMuPDF drawings")
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting drawings: {e}")
        
        logger.info(f"Found {len(rectangles)} rectangles from drawings")
        
        # Step 4: Get rectangles from pdfplumber too (different detection method)
        pdfplumber_rects = []
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                
                # Get explicit rectangles
                if hasattr(page, 'rects') and page.rects:
                    for rect in page.rects:
                        x0, y0, x1, y1 = rect['x0'], rect['y0'], rect['x1'], rect['y1']
                        pdfplumber_rects.append([x0, y0, x1, y1])
                
                # Also check for rect annotations (if available)
                if hasattr(page, 'annos') and page.annos:
                    for anno in page.annos:
                        if 'rect' in anno:
                            pdfplumber_rects.append(anno['rect'])
        
        logger.info(f"Found {len(pdfplumber_rects)} additional rectangles from pdfplumber")
        
        # Step 5: Combine all rectangles and filter for rooms
        all_rectangles = rectangles + pdfplumber_rects
        rooms = self._process_rectangles_to_rooms(
            all_rectangles,
            pixels_per_foot,
            pdf_path,
            page_num
        )
        
        # Step 6: Enhance with OCR data
        logger.info("Enhancing with OCR text extraction...")
        rooms = self._enhance_rooms_with_ocr(rooms, pdf_path, page_num, pixels_per_foot)
        
        # Step 7: Deduplicate overlapping rooms
        rooms = self._deduplicate_rooms(rooms)
        
        # Calculate totals
        total_area = sum(room.area_sqft for room in rooms)
        
        # Compile results
        result = {
            'success': True,
            'rooms': [
                {
                    'name': room.name,
                    'area_sqft': round(room.area_sqft, 1),
                    'width_ft': round(room.width_ft, 1),
                    'height_ft': round(room.height_ft, 1),
                    'source': room.source,
                    'confidence': room.confidence,
                    'ocr_labels': room.ocr_labels
                }
                for room in rooms
            ],
            'total_area': round(total_area, 0),
            'scale': {
                'notation': scale_result.scale_notation,
                'pixels_per_foot': pixels_per_foot,
                'confidence': scale_result.confidence
            },
            'metadata': {
                'page_number': page_num + 1,
                'processing_time': time.time() - start_time,
                'rectangles_found': len(all_rectangles),
                'rooms_detected': len(rooms),
                'zip_code': zip_code
            }
        }
        
        logger.info(f"Hybrid parsing complete: {len(rooms)} rooms, {total_area:.0f} sq ft total")
        return result
    
    def _process_rectangles_to_rooms(
        self,
        rectangles: List[List[float]],
        pixels_per_foot: float,
        pdf_path: str,
        page_num: int
    ) -> List[RoomData]:
        """Convert rectangles to room data"""
        rooms = []
        
        # Define reasonable room size limits
        min_room_width_ft = 4  # 4 feet minimum width
        min_room_area_sqft = 20  # 20 sq ft minimum (small closet)
        max_room_area_sqft = 1500  # 1500 sq ft maximum (large room)
        
        for rect in rectangles:
            if len(rect) < 4:
                continue
                
            x0, y0, x1, y1 = rect[:4]
            
            # Calculate dimensions
            width_pixels = abs(x1 - x0)
            height_pixels = abs(y1 - y0)
            
            # Skip if too small
            if width_pixels < 10 or height_pixels < 10:
                continue
            
            width_ft = width_pixels / pixels_per_foot
            height_ft = height_pixels / pixels_per_foot
            area_sqft = width_ft * height_ft
            
            # Filter by reasonable room dimensions
            if (width_ft >= min_room_width_ft and
                height_ft >= min_room_width_ft and
                min_room_area_sqft <= area_sqft <= max_room_area_sqft):
                
                # Determine room type by size
                if area_sqft < 40:
                    room_type = "Closet"
                elif area_sqft < 80:
                    room_type = "Bathroom"
                elif area_sqft < 150:
                    room_type = "Bedroom"
                elif area_sqft < 250:
                    room_type = "Master Bedroom"
                elif area_sqft < 400:
                    room_type = "Living Room"
                else:
                    room_type = "Great Room"
                
                rooms.append(RoomData(
                    name=room_type,
                    rect=(x0, y0, x1, y1),
                    area_sqft=area_sqft,
                    width_ft=width_ft,
                    height_ft=height_ft,
                    source='rectangle',
                    confidence=0.7,
                    ocr_labels=[]
                ))
        
        logger.info(f"Processed {len(rectangles)} rectangles into {len(rooms)} potential rooms")
        return rooms
    
    def _enhance_rooms_with_ocr(
        self,
        rooms: List[RoomData],
        pdf_path: str,
        page_num: int,
        pixels_per_foot: float
    ) -> List[RoomData]:
        """Enhance room data with OCR text"""
        
        # Render page and extract text
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            doc.close()
            return rooms
            
        page = doc[page_num]
        
        # Get text with locations using PyMuPDF
        text_instances = page.get_text("dict")
        
        # Process text blocks
        for block in text_instances.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        text_x = (bbox[0] + bbox[2]) / 2
                        text_y = (bbox[1] + bbox[3]) / 2
                        
                        # Check if text is inside any room
                        for room in rooms:
                            x0, y0, x1, y1 = room.rect
                            if x0 <= text_x <= x1 and y0 <= text_y <= y1:
                                room.ocr_labels.append(text)
                                
                                # Update room name if we find a room label
                                text_lower = text.lower()
                                room_keywords = [
                                    'bedroom', 'bathroom', 'kitchen', 'living',
                                    'dining', 'garage', 'closet', 'office',
                                    'master', 'guest', 'family', 'den'
                                ]
                                
                                for keyword in room_keywords:
                                    if keyword in text_lower:
                                        room.name = text
                                        room.confidence = 0.9
                                        room.source = 'combined'
                                        break
        
        doc.close()
        
        # Count how many rooms got OCR labels
        labeled_rooms = sum(1 for room in rooms if room.ocr_labels)
        logger.info(f"Enhanced {labeled_rooms} rooms with OCR text")
        
        return rooms
    
    def _deduplicate_rooms(self, rooms: List[RoomData]) -> List[RoomData]:
        """Remove duplicate/overlapping rooms"""
        if not rooms:
            return rooms
        
        # Sort by confidence and area (prefer high confidence, larger rooms)
        rooms.sort(key=lambda r: (r.confidence, r.area_sqft), reverse=True)
        
        final_rooms = []
        for room in rooms:
            x0, y0, x1, y1 = room.rect
            
            # Check overlap with existing rooms
            is_duplicate = False
            for existing in final_rooms:
                ex0, ey0, ex1, ey1 = existing.rect
                
                # Calculate intersection
                ix0 = max(x0, ex0)
                iy0 = max(y0, ey0)
                ix1 = min(x1, ex1)
                iy1 = min(y1, ey1)
                
                if ix0 < ix1 and iy0 < iy1:
                    # Calculate overlap percentage
                    intersection_area = (ix1 - ix0) * (iy1 - iy0)
                    room_area = (x1 - x0) * (y1 - y0)
                    
                    if intersection_area > room_area * 0.5:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                final_rooms.append(room)
        
        logger.info(f"Deduplicated {len(rooms)} rooms to {len(final_rooms)} unique rooms")
        return final_rooms


# Global instance
hybrid_parser = HybridBlueprintParser()