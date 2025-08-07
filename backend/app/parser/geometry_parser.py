"""
Elite geometry parser for architectural PDFs
Extracts walls, rooms, and duct outlines using pdfplumber + PyMuPDF
"""

import pdfplumber
import fitz  # PyMuPDF
import numpy as np
import logging
import time
import traceback
import threading
from typing import Dict, List, Any, Optional, Tuple
import re
from .schema import RawGeometry
from .scale_detector import ScaleDetector, ScaleResult
from .multi_page_scale_detector import MultiPageScaleDetector
from .exceptions import ScaleDetectionError
from .smart_drawing_extractor import smart_extractor
from .optimized_scale_detector import OptimizedScaleDetector, extract_scale_quickly
from services.pdf_thread_manager import safe_pdfplumber_operation, safe_pymupdf_operation

# Try to import OCR extractor for better text extraction
try:
    from services.ocr_extractor import OCRExtractor
except ImportError:
    OCRExtractor = None  # type: ignore
    logging.warning("PaddleOCR not available for scale detection - using basic text extraction")

logger = logging.getLogger(__name__)


class GeometryParser:
    """Advanced PDF geometry extraction for HVAC blueprints"""
    
    def __init__(self):
        # Initialize scale detector
        self.scale_detector = ScaleDetector(dpi=72.0)  # Standard PDF DPI
        # Initialize optimized scale detector for fast text-based detection
        self.optimized_scale_detector = OptimizedScaleDetector(dpi=72.0)
        # Initialize multi-page scale detector for better accuracy
        self.multi_page_scale_detector = MultiPageScaleDetector()
        # Initialize OCR extractor if available
        self.ocr_extractor = OCRExtractor(use_gpu=False) if OCRExtractor else None
        
        # Keep legacy scale patterns for backward compatibility
        self.scale_patterns = [
            # Standard architectural scales
            r'1/(\d+)"?\s*=\s*1\'?-?0?"?',    # 1/4" = 1'-0" -> captures denominator
            r'1"?\s*=\s*(\d+)\'?-?(\d+)?"?',  # 1" = 20'-0"
            r'(\d+)\s*:\s*(\d+)',              # 1:240
            r'SCALE\s*[:\-]\s*1/(\d+)',        # SCALE: 1/4
            r'SCALE\s*[:\-]\s*(.+)',           # SCALE: 1/4" = 1'-0"
            # Common variations
            r'(\d+)"\s*=\s*(\d+)\'',           # 1" = 8'
            r'1\s*:\s*(\d+)',                  # 1:48
        ]
        
        # Increased limits - smart extractor handles timeouts properly
        self.MAX_LINES = 50000  # Increased from 10000
        self.MAX_RECTANGLES = 10000  # Increased from 5000  
        self.MAX_POLYLINES = 10000  # Increased from 2000
        self.MAX_DRAWING_ITEMS = 5000  # Increased from 1000
        
        # Plausible architectural scales in px/ft for standard 72 DPI PDFs
        # 1/8"=1' -> 24, 1/4"=1' -> 48, 1/2"=1' -> 96
        self.PLAUSIBLE_SCALES = [96.0, 48.0, 24.0]
        # Residential total area plausibility bounds (single plan page)
        self.MIN_RES_AREA_SQFT = 600.0
        self.MAX_RES_AREA_SQFT = 8000.0
    
    # Removed _retry_on_document_closed - now using thread-safe PDF manager
    
    def parse(self, pdf_path: str, page_number: int = 0) -> RawGeometry:
        """
        Extract comprehensive geometry from architectural PDF using thread-safe operations
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number to parse (default: 0)
            
        Returns:
            RawGeometry with all extracted elements
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting thread-safe geometry parsing")
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
        
        try:
            # Extract basic page info and geometry using thread-safe pdfplumber operation
            def pdfplumber_operation(pdf):
                logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF in pdfplumber operation for: {pdf_path}")
                
                if not pdf.pages:
                    logger.error(f"[Thread {thread_name}:{thread_id}] PDF has no pages: {pdf_path}")
                    raise ValueError("PDF has no pages")
                
                if page_number >= len(pdf.pages) or page_number < 0:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Invalid page number {page_number + 1}, PDF has {len(pdf.pages)} pages")
                    raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(pdf.pages)} pages)")
                
                page = pdf.pages[page_number]
                logger.info(f"[Thread {thread_name}:{thread_id}] Processing page {page_number + 1} of {len(pdf.pages)} via pdfplumber")
                logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                
                # Extract basic page info
                page_width = float(page.width)
                page_height = float(page.height)
                logger.info(f"[Thread {thread_name}:{thread_id}] Page dimensions: {page_width} x {page_height}")
                
                # Use robust multi-method scale detection
                logger.info(f"[Thread {thread_name}:{thread_id}] Starting robust scale detection...")
                scale_start = time.time()
                scale_factor = None
                scale_result = None
                
                try:
                    # OPTIMIZATION: Try fast text-based scale detection first
                    quick_scale_success = False
                    try:
                        logger.info(f"[Thread {thread_name}:{thread_id}] Attempting optimized text-based scale detection...")
                        page_text = page.extract_text()  # Much faster than extract_words()
                        
                        if page_text:
                            quick_result = self.optimized_scale_detector.detect_scale_from_text(page_text)
                            
                            if quick_result and quick_result.confidence >= 0.85:
                                # High confidence text-based detection - use it directly
                                logger.info(f"[Thread {thread_name}:{thread_id}] Fast scale detection successful: {quick_result.scale_factor:.1f} px/ft (confidence: {quick_result.confidence:.2f})")
                                scale_factor = quick_result.scale_factor
                                scale_result = ScaleResult(
                                    scale_factor=quick_result.scale_factor,
                                    confidence=quick_result.confidence,
                                    detection_method=f"optimized_{quick_result.detection_method}",
                                    validation_results={'text_based': True, 'optimized': True},
                                    alternative_scales=[]
                                )
                                quick_scale_success = True
                                logger.info(f"[Thread {thread_name}:{thread_id}] Using optimized scale, skipping expensive word extraction")
                                
                    except Exception as e:
                        logger.debug(f"[Thread {thread_name}:{thread_id}] Fast scale detection failed: {e}")
                    
                    # Only do expensive extraction if quick detection failed or had low confidence
                    if not quick_scale_success:
                        # Extract text elements for scale detection
                        # Use PaddleOCR if available for better accuracy
                        if self.ocr_extractor and getattr(self.ocr_extractor, 'ocr', None):
                            logger.info(f"[Thread {thread_name}:{thread_id}] Using PaddleOCR for text extraction")
                            # Render page as image for OCR
                            import fitz
                            import numpy as np
                            from PIL import Image
                            from io import BytesIO
                            import cv2
                            
                            # Convert page to image
                            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                            pix = page.page.get_pixmap(matrix=mat) if hasattr(page, 'page') else None
                            if pix:
                                img_data = pix.tobytes("ppm")
                                img = Image.open(BytesIO(img_data))
                                img_array = np.array(img)
                                # Convert RGB to BGR for OpenCV/PaddleOCR
                                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                                
                                # Extract text with PaddleOCR
                                text_regions = self.ocr_extractor.extract_all_text(img_array)
                                
                                # Convert to text elements format
                                text_elements = []
                                for region in text_regions:
                                    if region.text.strip() and region.confidence > 0.3:
                                        bbox = region.bbox
                                        x = float(min(point[0] for point in bbox)) / 2  # Adjust for 2x zoom
                                        y = float(min(point[1] for point in bbox)) / 2
                                        text_elements.append({
                                            'text': region.text.strip(),
                                            'x0': x,
                                            'top': y,
                                            'confidence': region.confidence,
                                            'source': 'paddleocr'
                                        })
                                logger.info(f"[Thread {thread_name}:{thread_id}] PaddleOCR extracted {len(text_elements)} text elements")
                            else:
                                # Fallback to pdfplumber
                                logger.warning(f"[Thread {thread_name}:{thread_id}] Failed to render page for OCR, using pdfplumber")
                                words = page.extract_words()
                                text_elements = [{'text': w['text'], 'x0': w.get('x0', 0), 'top': w.get('top', 0)} for w in words]
                        else:
                            # Use pdfplumber text extraction
                            logger.info(f"[Thread {thread_name}:{thread_id}] Using pdfplumber for text extraction (PaddleOCR not available)")
                            words = page.extract_words()
                            text_elements = [{'text': w['text'], 'x0': w.get('x0', 0), 'top': w.get('top', 0)} for w in words]
                        
                        # Extract dimensions (look for patterns like "12'-0"")
                        dimensions = []
                        dimension_pattern = r"(\d+)['\s]*-?\s*(\d+)?[\"\s]*"
                        for element in text_elements:
                            if re.search(dimension_pattern, element['text']):
                                dimensions.append({
                                    'dimension_text': element['text'],
                                    'x0': element.get('x0', 0),
                                    'top': element.get('top', 0),
                                    'parsed_dimensions': self._parse_dimension_text(element['text'])
                                })
                        
                        # We'll get rectangles and lines later, but pass empty for initial detection
                        # This allows text-based detection to work first
                        scale_result = self.scale_detector.detect_scale(
                            text_elements=text_elements,
                            dimensions=dimensions,
                            rectangles=[],  # Will be filled after we extract them
                            lines=[],  # Will be filled after we extract them
                            page_width=page_width,
                            page_height=page_height
                        )
                        
                        scale_factor = scale_result.scale_factor
                        logger.info(f"[Thread {thread_name}:{thread_id}] Scale detection result:")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Scale: {scale_factor:.1f} px/ft")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Confidence: {scale_result.confidence:.2f}")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Method: {scale_result.detection_method}")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Validation: {scale_result.validation_results}")
                        
                        # Check if confidence is too low and raise exception if needed
                        if scale_result.confidence < 0.5:
                            logger.warning(f"[Thread {thread_name}:{thread_id}] Scale detection confidence too low: {scale_result.confidence:.2f}")
                            # We'll raise this after extracting geometry to provide more context
                        
                except Exception as e:
                    logger.warning(f"[Thread {thread_name}:{thread_id}] Robust scale detection failed: {e}")
                    # Use fallback scale
                    scale_factor = 48.0  # Default to 1/4" scale
                    scale_result = ScaleResult(
                        scale_factor=scale_factor,
                        confidence=0.3,
                        detection_method="error_fallback",
                        validation_results={},
                        alternative_scales=[]
                    )
                
                logger.info(f"[Thread {thread_name}:{thread_id}] Scale detection took {time.time() - scale_start:.2f}s, result: {scale_factor}")
                
                # CRITICAL: Extract lines directly - no method calls with page objects
                logger.info(f"[Thread {thread_name}:{thread_id}] Extracting lines...")
                lines_start = time.time()
                lines = []
                
                try:
                    raw_lines = page.lines
                    logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(raw_lines)} raw lines to process")
                    
                    # Apply smart limits based on line count
                    if len(raw_lines) > 20000:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] Excessive lines ({len(raw_lines)}), sampling every 5th line instead of skipping")
                        raw_lines = raw_lines[::5]  # Sample every 5th line for very complex drawings
                    elif len(raw_lines) > 10000:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] Many lines ({len(raw_lines)}), sampling every 3rd line")
                        raw_lines = raw_lines[::3]  # Sample every 3rd line
                    elif len(raw_lines) > 5000:
                        logger.info(f"[Thread {thread_name}:{thread_id}] Moderate lines ({len(raw_lines)}), sampling every 2nd line")
                        raw_lines = raw_lines[::2]  # Sample every 2nd line
                    
                    for i, line in enumerate(raw_lines):
                        try:
                            # Coerce pdfplumber Decimal values to float before math
                            x0 = float(line.get('x0')) if line.get('x0') is not None else None
                            y0 = float(line.get('y0')) if line.get('y0') is not None else None
                            x1 = float(line.get('x1')) if line.get('x1') is not None else None
                            y1 = float(line.get('y1')) if line.get('y1') is not None else None
                            
                            # Validate coordinates
                            if any(coord is None for coord in [x0, y0, x1, y1]):
                                continue
                            
                            # Compute length using floats to avoid Decimal/NumPy issues
                            dx = x1 - x0
                            dy = y1 - y0
                            length = float((dx * dx + dy * dy) ** 0.5)
                            
                            # Skip degenerate lines
                            if length < 0.1:
                                continue
                            
                            width = float(line.get('width', 1.0))
                            
                            lines.append({
                                'type': 'line',
                                'coords': [x0, y0, x1, y1],
                                'x0': x0,
                                'y0': y0,
                                'x1': x1,
                                'y1': y1,
                                'width': width,
                                'length': length,
                                'line_type': 'wall' if width > 2.0 and length > 50 else 'dimension' if length > 100 and width < 1.5 else 'other',
                                'orientation': 'vertical' if abs(x1 - x0) < 2 else 'horizontal' if abs(y1 - y0) < 2 else 'diagonal',
                                'wall_probability': min((length/200 + width/3.0)/2, 1.0)
                            })
                            
                        except Exception as e:
                            logger.debug(f"[Thread {thread_name}:{thread_id}] Error processing line {i}: {e}")
                            continue
                    
                    logger.info(f"[Thread {thread_name}:{thread_id}] Successfully processed {len(lines)} valid lines")
                    
                except Exception as e:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Line extraction failed: {e}")
                    lines = []
                
                logger.info(f"[Thread {thread_name}:{thread_id}] Line extraction took {time.time() - lines_start:.2f}s, found {len(lines)} lines")
                
                # CRITICAL: Extract rectangles directly - no method calls with page objects
                logger.info(f"[Thread {thread_name}:{thread_id}] Extracting rectangles...")
                rects_start = time.time()
                rectangles = []
                
                try:
                    raw_rects = page.rects
                    logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(raw_rects)} raw rectangles to process")
                    
                    # Debug: Check if page.rects is actually returning rectangles
                    if len(raw_rects) == 0:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] No rectangles found by pdfplumber. Checking for alternative sources...")
                        # Try to extract rectangles from curves/edges if available
                        if hasattr(page, 'curves') and page.curves:
                            logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(page.curves)} curves that might contain rectangles")
                        if hasattr(page, 'edges') and page.edges:
                            logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(page.edges)} edges that might form rectangles")
                    
                    # Debug: Log a sample of raw rectangle sizes
                    if len(raw_rects) > 0 and scale_factor:
                        for i, rect in enumerate(raw_rects[:5]):  # Log first 5 rectangles
                            if rect.get('x0') is not None and rect.get('x1') is not None:
                                w = rect['x1'] - rect['x0']
                                h = rect['y1'] - rect['y0']
                                area = w * h
                                area_sqft = area / (scale_factor ** 2) if scale_factor > 0 else 0
                                logger.info(f"[Thread {thread_name}:{thread_id}] Sample rect {i}: {w:.0f}x{h:.0f} px, area={area:.0f} px², ~{area_sqft:.1f} sqft")
                    
                    # Apply defensive limit
                    if len(raw_rects) > self.MAX_RECTANGLES:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] Too many rectangles ({len(raw_rects)}), limiting to {self.MAX_RECTANGLES}")
                        raw_rects = raw_rects[:self.MAX_RECTANGLES]
                    
                    # Calculate scale-aware thresholds for rectangle filtering
                    if scale_factor and scale_factor > 0:
                        # Adaptive thresholds based on scale to handle different blueprint types
                        # Lower minimum to catch more potential rooms, let fallback parser validate
                        min_room_sqft = 10  # Lowered to catch smaller valid spaces (pantries, closets)
                        max_room_sqft = 2000  # Increased to handle open floor plans and great rooms
                        
                        # Convert to page units: area_page = area_sqft * (scale_px_per_ft)^2
                        min_area_page_units = min_room_sqft * (scale_factor ** 2)
                        max_area_page_units = max_room_sqft * (scale_factor ** 2)
                        
                        logger.info(f"[Thread {thread_name}:{thread_id}] Using scale-aware rectangle filtering:")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Scale factor: {scale_factor:.1f} px/ft")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Min area: {min_area_page_units:.0f} page units ({min_room_sqft} sq ft)")
                        logger.info(f"[Thread {thread_name}:{thread_id}]   Max area: {max_area_page_units:.0f} page units ({max_room_sqft} sq ft)")
                    else:
                        # Use conservative defaults when no scale is detected
                        # These work for typical low-resolution PDFs
                        min_area_page_units = 100
                        max_area_page_units = 500000  # Increased from 200000 to handle more cases
                        logger.info(f"[Thread {thread_name}:{thread_id}] No scale detected, using default rectangle filtering")
                    
                    for i, rect in enumerate(raw_rects):
                        try:
                            # Validate coordinates
                            if any(coord is None for coord in [rect.get('x0'), rect.get('y0'), rect.get('x1'), rect.get('y1')]):
                                continue
                            
                            width = float(rect['x1'] - rect['x0'])
                            height = float(rect['y1'] - rect['y0'])
                            
                            # Skip degenerate rectangles
                            if width <= 0 or height <= 0:
                                continue
                            
                            area = width * height
                            
                            # Filter meaningful rectangles using scale-aware thresholds
                            if area > min_area_page_units and area < max_area_page_units:
                                # Calculate estimated square footage for logging
                                est_sqft = area / (scale_factor ** 2) if scale_factor else 0
                                
                                # Log significant rectangles for debugging
                                if est_sqft > 50:  # Log rooms larger than 50 sqft
                                    logger.info(f"[Thread {thread_name}:{thread_id}] Found room: {est_sqft:.1f} sqft "
                                              f"({width:.0f}x{height:.0f} px, area={area:.0f} px²)")
                                
                                rectangles.append({
                                    'type': 'rect',
                                    'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                                    'x0': float(rect['x0']),
                                    'y0': float(rect['y0']),
                                    'x1': float(rect['x1']),
                                    'y1': float(rect['y1']),
                                    'width': width,
                                    'height': height,
                                    'area': area,  # Area in pixels
                                    # Add converted measurements for downstream use
                                    'area_sqft': area / (scale_factor ** 2) if scale_factor and scale_factor > 0 else None,
                                    'width_ft': width / scale_factor if scale_factor and scale_factor > 0 else None,
                                    'height_ft': height / scale_factor if scale_factor and scale_factor > 0 else None,
                                    'center_x': float(rect['x0'] + width / 2),
                                    'center_y': float(rect['y0'] + height / 2),
                                    'aspect_ratio': width / height if height > 0 else 0,
                                    'room_probability': 0.5,  # Simplified
                                    'estimated_sqft': est_sqft  # Add for debugging
                                })
                            elif area > 0:  # Log why rectangles are filtered out
                                if scale_factor:
                                    est_sqft = area / (scale_factor ** 2)
                                    if est_sqft > max_room_sqft:
                                        logger.debug(f"[Thread {thread_name}:{thread_id}] Rectangle {i} filtered: too large ({est_sqft:.0f} sq ft > {max_room_sqft} sq ft)")
                                    elif est_sqft < min_room_sqft:
                                        # Only log significant filtered rectangles (5-25 sqft range)
                                        if 5 <= est_sqft < min_room_sqft:
                                            logger.info(f"[Thread {thread_name}:{thread_id}] Rectangle {i} filtered: {est_sqft:.0f} sq ft < {min_room_sqft} sq ft threshold")
                            
                        except Exception as e:
                            logger.debug(f"[Thread {thread_name}:{thread_id}] Error processing rectangle {i}: {e}")
                            continue
                    
                    # If we failed to accept any rectangles on the first pass, retry with relaxed min area
                    if len(rectangles) == 0 and len(raw_rects) > 0:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] No rectangles accepted; retrying with relaxed min area")
                        rectangles_relaxed = []
                        # Use a smaller minimum room size to catch closets/pantries
                        relaxed_min_sqft = 4 if scale_factor and scale_factor > 0 else None
                        relaxed_min_area_units = (relaxed_min_sqft * (scale_factor ** 2)) if relaxed_min_sqft else 25.0
                        for i, rect in enumerate(raw_rects):
                            try:
                                if any(coord is None for coord in [rect.get('x0'), rect.get('y0'), rect.get('x1'), rect.get('y1')]):
                                    continue
                                width = float(rect['x1'] - rect['x0'])
                                height = float(rect['y1'] - rect['y0'])
                                if width <= 0 or height <= 0:
                                    continue
                                area = width * height
                                if area > relaxed_min_area_units:
                                    est_sqft = area / (scale_factor ** 2) if scale_factor and scale_factor > 0 else None
                                    rectangles_relaxed.append({
                                        'type': 'rect',
                                        'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                                        'x0': float(rect['x0']),
                                        'y0': float(rect['y0']),
                                        'x1': float(rect['x1']),
                                        'y1': float(rect['y1']),
                                        'width': width,
                                        'height': height,
                                        'area': area,
                                        'area_sqft': est_sqft,
                                        'width_ft': width / scale_factor if scale_factor and scale_factor > 0 else None,
                                        'height_ft': height / scale_factor if scale_factor and scale_factor > 0 else None,
                                        'center_x': float(rect['x0'] + width / 2),
                                        'center_y': float(rect['y0'] + height / 2),
                                        'aspect_ratio': width / height if height > 0 else 0,
                                        'room_probability': 0.4,
                                        'estimated_sqft': est_sqft
                                    })
                            except Exception:
                                continue
                        if rectangles_relaxed:
                            rectangles = sorted(rectangles_relaxed, key=lambda r: r['area'], reverse=True)
                            logger.info(f"[Thread {thread_name}:{thread_id}] Relaxed pass accepted {len(rectangles)} rectangles")
                        else:
                            logger.info(f"[Thread {thread_name}:{thread_id}] Relaxed pass still found 0 rectangles")

                    # If confidence is low or still zero rectangles, try alternative common scales and pick the one that accepts the most rectangles
                    try:
                        current_accept_count = len(rectangles)
                        low_confidence = (scale_result.confidence < 0.5) if scale_result else True
                        # Do not override a strong text/implicit detection
                        strong_text_detection = bool(scale_result and str(scale_result.detection_method).startswith("optimized_") and scale_result.confidence >= 0.75)
                        implicit_detection = bool(scale_result and "implicit" in str(scale_result.detection_method).lower() and scale_result.confidence >= 0.7)
                        if (low_confidence or current_accept_count == 0) and not (strong_text_detection or implicit_detection) and len(raw_rects) > 0:
                            logger.warning(f"[Thread {thread_name}:{thread_id}] Low-confidence scale ({scale_result.confidence if scale_result else 'n/a'}). Evaluating alternative scales")
                            # Restrict to plausible architectural scales only
                            candidate_scales = list(self.PLAUSIBLE_SCALES)
                            best_scale = scale_factor or 48.0
                            best_count = current_accept_count
                            best_rects = rectangles
                            best_area_sqft = sum((r.get('area', 0.0) / ((scale_factor or 48.0) ** 2)) for r in rectangles) if rectangles else 0.0

                            def accept_rects_for_scale(test_scale: float) -> List[Dict[str, Any]]:
                                min_sqft, max_sqft = 10, 2000
                                min_units = min_sqft * (test_scale ** 2)
                                max_units = max_sqft * (test_scale ** 2)
                                accepted: List[Dict[str, Any]] = []
                                for rr in raw_rects:
                                    try:
                                        if any(coord is None for coord in [rr.get('x0'), rr.get('y0'), rr.get('x1'), rr.get('y1')]):
                                            continue
                                        w = float(rr['x1'] - rr['x0'])
                                        h = float(rr['y1'] - rr['y0'])
                                        if w <= 0 or h <= 0:
                                            continue
                                        a = w * h
                                        if a > min_units and a < max_units:
                                            est_sqft = a / (test_scale ** 2)
                                            accepted.append({
                                                'type': 'rect',
                                                'coords': [float(rr['x0']), float(rr['y0']), float(rr['x1']), float(rr['y1'])],
                                                'x0': float(rr['x0']),
                                                'y0': float(rr['y0']),
                                                'x1': float(rr['x1']),
                                                'y1': float(rr['y1']),
                                                'width': w,
                                                'height': h,
                                                'area': a,
                                                'area_sqft': est_sqft,
                                                'width_ft': w / test_scale,
                                                'height_ft': h / test_scale,
                                                'center_x': float(rr['x0'] + w / 2),
                                                'center_y': float(rr['y0'] + h / 2),
                                                'aspect_ratio': w / h if h > 0 else 0,
                                                'room_probability': 0.5,
                                                'estimated_sqft': est_sqft
                                            })
                                    except Exception:
                                        continue
                                return sorted(accepted, key=lambda r: r['area'], reverse=True)
                            for cand in candidate_scales:
                                accepted = accept_rects_for_scale(cand)
                                # Plausibility checks: minimum count and total area within residential bounds
                                total_area_sqft = sum(r['area'] / (cand ** 2) for r in accepted)
                                plausible_area = self.MIN_RES_AREA_SQFT <= total_area_sqft <= self.MAX_RES_AREA_SQFT
                                enough_rooms = len(accepted) >= 10  # avoid switching based on a few rectangles
                                if len(accepted) > best_count and plausible_area and enough_rooms:
                                    best_count = len(accepted)
                                    best_scale = cand
                                    best_rects = accepted
                                    best_area_sqft = total_area_sqft
                            if best_count > current_accept_count:
                                logger.info(f"[Thread {thread_name}:{thread_id}] Switching scale to {best_scale:.1f} px/ft based on rectangle acceptance ({best_count} vs {current_accept_count}), total_area≈{best_area_sqft:.0f} sqft")
                                scale_factor = best_scale
                                rectangles = best_rects
                                # Adjust scale_result to reflect change
                                if scale_result:
                                    scale_result.scale_factor = best_scale
                                    scale_result.detection_method = "alt_scale_rectangles_plausible"
                                    # Confidence improves if area and count are plausible
                                    scale_result.confidence = max(scale_result.confidence, 0.7)
                    except Exception as _e:
                        logger.debug(f"[Thread {thread_name}:{thread_id}] Alternative scale evaluation failed: {_e}")
                    
                    logger.info(f"[Thread {thread_name}:{thread_id}] Successfully processed {len(rectangles)} valid rectangles")
                    rectangles = sorted(rectangles, key=lambda r: r['area'], reverse=True)
                    
                except Exception as e:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Rectangle extraction failed: {e}")
                    rectangles = []
                
                logger.info(f"[Thread {thread_name}:{thread_id}] Rectangle extraction took {time.time() - rects_start:.2f}s, found {len(rectangles)} rectangles")
                
                return {
                    'page_width': page_width,
                    'page_height': page_height,
                    'scale_factor': scale_factor,
                    'lines': lines,
                    'rectangles': rectangles
                }
            
            # Get basic geometry from pdfplumber
            pdfplumber_results = safe_pdfplumber_operation(
                pdf_path,
                pdfplumber_operation,
                f"pdfplumber_geometry_extraction_page_{page_number + 1}",
                max_retries=2
            )
            
            # Extract polylines using smart extractor with progressive degradation
            logger.info(f"[Thread {thread_name}:{thread_id}] Extracting polylines with smart extractor...")
            poly_start = time.time()
            
            # Use smart extractor that never blocks
            extraction_result = smart_extractor.extract_drawings(pdf_path, page_number)
            
            # Convert to legacy polyline format
            polylines = []
            for polyline in extraction_result.polylines:
                if len(polyline) >= 2:
                    polylines.append({
                        'points': polyline,
                        'quality': extraction_result.quality_factor
                    })
            
            # Also add drawings as simplified polylines if quality is low
            if extraction_result.quality_factor < 0.5 and extraction_result.drawings:
                for drawing in extraction_result.drawings[:100]:  # Limit to 100
                    if 'bbox' in drawing:
                        bbox = drawing['bbox']
                        # Convert bbox to polyline
                        polylines.append({
                            'points': [
                                (bbox[0], bbox[1]),
                                (bbox[2], bbox[3])
                            ],
                            'quality': extraction_result.quality_factor,
                            'type': 'bbox_fallback'
                        })
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Smart extraction took {time.time() - poly_start:.2f}s")
            logger.info(f"[Thread {thread_name}:{thread_id}] Method: {extraction_result.extraction_method}, Quality: {extraction_result.quality_factor}")
            logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(polylines)} polylines")
            
            # Compile final result
            result = RawGeometry(
                page_width=pdfplumber_results['page_width'],
                page_height=pdfplumber_results['page_height'],
                scale_factor=pdfplumber_results['scale_factor'],
                lines=pdfplumber_results['lines'],
                rectangles=pdfplumber_results['rectangles'],
                polylines=polylines
            )
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Geometry parsing completed successfully")
            logger.info(f"[Thread {thread_name}:{thread_id}] Final result - Lines: {len(result.lines)}, Rectangles: {len(result.rectangles)}, Polylines: {len(result.polylines)}")
            return result
                
        except Exception as e:
            error_str = str(e).lower()
            
            # CRITICAL: Check for document closed errors and log full context
            if any(error_phrase in error_str for error_phrase in [
                "document closed", 
                "seek of closed file", 
                "closed file", 
                "bad file descriptor",
                "document has been closed"
            ]):
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in geometry parsing")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                logger.error(f"[Thread {thread_name}:{thread_id}] Geometry parsing failed: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            raise
    
    def _detect_scale(self, page) -> Optional[float]:
        """Detect scale markers in the blueprint"""
        words = page.extract_words()
        text = ' '.join([w['text'] for w in words])
        
        for pattern in self.scale_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Parse scale ratio (simplified)
                    if ':' in match.group():
                        parts = match.group().split(':')
                        return float(parts[1]) / float(parts[0])
                    else:
                        # Parse architectural scale like 1/4" = 1'-0"
                        return 48.0  # Default to 1/4" scale
                except:
                    continue
        
        return None
    
    def _extract_lines(self, page) -> List[Dict[str, Any]]:
        """Extract line segments (walls, dimensions)"""
        lines = []
        
        try:
            raw_lines = page.lines
            logger.info(f"Found {len(raw_lines)} raw lines to process")
            
            # Apply defensive limit
            if len(raw_lines) > self.MAX_LINES:
                logger.warning(f"Too many lines ({len(raw_lines)}), limiting to {self.MAX_LINES}")
                raw_lines = raw_lines[:self.MAX_LINES]
            
            for i, line in enumerate(raw_lines):
                try:
                    x0, y0, x1, y1 = line['x0'], line['y0'], line['x1'], line['y1']
                    
                    # Validate coordinates
                    if any(coord is None for coord in [x0, y0, x1, y1]):
                        logger.debug(f"Skipping line {i} with None coordinates")
                        continue
                    
                    length = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
                    
                    # Skip degenerate lines
                    if length < 0.1:
                        continue
                    
                    # Classify line type
                    line_type = self._classify_line(line, length)
                    
                    lines.append({
                        'type': 'line',
                        'coords': [float(x0), float(y0), float(x1), float(y1)],
                        'x0': float(x0),
                        'y0': float(y0),
                        'x1': float(x1),
                        'y1': float(y1),
                        'width': float(line.get('width', 1.0)),
                        'length': float(length),
                        'line_type': line_type,
                        'orientation': self._get_orientation(x0, y0, x1, y1),
                        'wall_probability': self._calculate_wall_probability(line, length)
                    })
                    
                except Exception as e:
                    logger.debug(f"Error processing line {i}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(lines)} valid lines")
            return self._group_parallel_lines(lines)
            
        except Exception as e:
            logger.error(f"Line extraction failed: {e}")
            return []
    
    def _extract_rectangles(self, page) -> List[Dict[str, Any]]:
        """Extract rectangles (likely rooms)"""
        rectangles = []
        
        try:
            raw_rects = page.rects
            logger.info(f"Found {len(raw_rects)} raw rectangles to process")
            
            # Apply defensive limit
            if len(raw_rects) > self.MAX_RECTANGLES:
                logger.warning(f"Too many rectangles ({len(raw_rects)}), limiting to {self.MAX_RECTANGLES}")
                raw_rects = raw_rects[:self.MAX_RECTANGLES]
            
            for i, rect in enumerate(raw_rects):
                try:
                    # Validate coordinates
                    if any(coord is None for coord in [rect.get('x0'), rect.get('y0'), rect.get('x1'), rect.get('y1')]):
                        logger.debug(f"Skipping rectangle {i} with None coordinates")
                        continue
                    
                    width = float(rect['x1'] - rect['x0'])
                    height = float(rect['y1'] - rect['y0'])
                    
                    # Skip degenerate rectangles
                    if width <= 0 or height <= 0:
                        continue
                    
                    area = width * height
                    
                    # Filter meaningful rectangles - using more permissive threshold
                    # This method doesn't have scale_factor, so use conservative filtering
                    # The actual room size validation happens in geometry_fallback.py
                    if area > 100:  # Very minimal filtering - let downstream handle it
                        # Note: This path doesn't have scale_factor, so we can't convert to feet yet
                        # The conversion will happen downstream when scale_factor is available
                        rectangles.append({
                            'type': 'rect',
                            'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                            'x0': float(rect['x0']),
                            'y0': float(rect['y0']),
                            'x1': float(rect['x1']),
                            'y1': float(rect['y1']),
                            'width': width,
                            'height': height,
                            'area': area,  # Area in pixels
                            # Can't convert without scale_factor
                            'area_sqft': None,
                            'width_ft': None,
                            'height_ft': None,
                            'center_x': float(rect['x0'] + width / 2),
                            'center_y': float(rect['y0'] + height / 2),
                            'aspect_ratio': width / height if height > 0 else 0,
                            'room_probability': self._calculate_room_probability(width, height, area)
                        })
                    
                except Exception as e:
                    logger.debug(f"Error processing rectangle {i}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(rectangles)} valid rectangles")
            return sorted(rectangles, key=lambda r: r['area'], reverse=True)
            
        except Exception as e:
            logger.error(f"Rectangle extraction failed: {e}")
            return []
    
    def _extract_polylines_pymupdf_safe(self, pdf_path: str, page_number: int = 0) -> List[Dict[str, Any]]:
        """Extract polylines and complex paths using thread-safe PyMuPDF operations"""
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting PyMuPDF polyline extraction")
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
        
        def pymupdf_operation(doc):
            """PyMuPDF operation to be executed thread-safely"""
            logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF in PyMuPDF operation for: {pdf_path}")
            
            if len(doc) == 0:
                logger.warning(f"[Thread {thread_name}:{thread_id}] PDF has no pages for PyMuPDF processing: {pdf_path}")
                return []
            
            if page_number >= len(doc) or page_number < 0:
                logger.warning(f"[Thread {thread_name}:{thread_id}] Invalid page number {page_number + 1} for PyMuPDF, PDF has {len(doc)} pages")
                return []
            
            page = doc[page_number]
            logger.info(f"[Thread {thread_name}:{thread_id}] Getting drawings from page {page_number + 1} via PyMuPDF")
            logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
            
            # Get all drawing paths with timeout protection
            drawings = page.get_drawings()
            logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(drawings)} drawings to process")
            
            # Apply defensive limit
            if len(drawings) > self.MAX_POLYLINES:
                logger.warning(f"Too many drawings ({len(drawings)}), limiting to {self.MAX_POLYLINES}")
                drawings = drawings[:self.MAX_POLYLINES]
            
            polylines = []
            for i, drawing in enumerate(drawings):
                try:
                    if not drawing or 'items' not in drawing:
                        continue
                        
                    items = drawing['items']
                    if not items or len(items) <= 2:
                        continue
                    
                    # Apply limit on drawing complexity
                    if len(items) > self.MAX_DRAWING_ITEMS:
                        logger.debug(f"Skipping complex drawing {i} with {len(items)} items")
                        continue
                    
                    # Extract path points
                    points = []
                    for j, item in enumerate(items):
                        if not item or len(item) < 3:
                            continue
                        
                        # Safely extract coordinates with null checks
                        try:
                            x, y = item[1], item[2]
                            if x is not None and y is not None and isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                points.extend([float(x), float(y)])
                        except (TypeError, ValueError, IndexError) as e:
                            logger.debug(f"Error extracting coordinates from item {j}: {e}")
                            continue
                    
                    if len(points) >= 6:  # At least 3 points
                        try:
                            stroke_width = float(drawing.get('width', 1.0)) if drawing.get('width') is not None else 1.0
                            
                            # Safely extract color
                            color = 0
                            if drawing.get('stroke') and isinstance(drawing['stroke'], dict):
                                color = drawing['stroke'].get('color', 0)
                            
                            closed = bool(drawing.get('closePath', False))
                            
                            polylines.append({
                                'points': points,
                                'stroke_width': stroke_width,
                                'color': color,
                                'closed': closed,
                                'duct_probability': self._calculate_duct_probability(points, drawing)
                            })
                        except (TypeError, ValueError) as e:
                            logger.debug(f"Error processing drawing {i} properties: {e}")
                            continue
                    
                except Exception as e:
                    logger.debug(f"Error processing drawing {i}: {e}")
                    continue
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Successfully processed {len(polylines)} valid polylines")
            return polylines
        
        try:
            result = safe_pymupdf_operation(
                pdf_path,
                pymupdf_operation,
                f"pymupdf_polyline_extraction_page_{page_number + 1}",
                max_retries=2
            )
            logger.info(f"[Thread {thread_name}:{thread_id}] PyMuPDF polyline extraction completed, found {len(result)} polylines")
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            
            # CRITICAL: Check for document closed errors and log full context
            if any(error_phrase in error_str for error_phrase in [
                "document closed", 
                "seek of closed file", 
                "closed file", 
                "bad file descriptor",
                "document has been closed"
            ]):
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in PyMuPDF polyline extraction")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                logger.error(f"[Thread {thread_name}:{thread_id}] PyMuPDF polyline extraction failed: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            
            return []  # Don't fail completely, just return empty results
    
    def _classify_line(self, line: Dict, length: float) -> str:
        """Classify line as wall, dimension, or other"""
        width = float(line.get('width', 1.0))
        
        if width > 2.0 and length > 50:
            return 'wall'
        elif length > 100 and width < 1.5:
            return 'dimension'
        else:
            return 'other'
    
    def _get_orientation(self, x0: float, y0: float, x1: float, y1: float) -> str:
        """Get line orientation"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        if dx < 2:
            return 'vertical'
        elif dy < 2:
            return 'horizontal'
        else:
            angle = np.arctan2(dy, dx) * 180 / np.pi
            if 22.5 <= angle <= 67.5:
                return 'diagonal'
            else:
                return 'horizontal' if dx > dy else 'vertical'
    
    def _calculate_wall_probability(self, line: Dict, length: float) -> float:
        """Calculate probability that line represents a wall"""
        width = float(line.get('width', 1.0))
        
        # Longer, thicker lines are more likely walls
        length_score = min(length / 200, 1.0)
        width_score = min(width / 3.0, 1.0)
        
        return (length_score + width_score) / 2
    
    def _calculate_room_probability(self, width: float, height: float, area: float) -> float:
        """Calculate probability that rectangle is a room"""
        # Reasonable room proportions
        aspect_ratio = width / height if height > 0 else 0
        aspect_score = 1.0 - abs(aspect_ratio - 1.5) / 3.0  # Prefer ~1.5:1 ratio
        aspect_score = max(0, min(1, aspect_score))
        
        # Reasonable room size
        area_score = 1.0 if 100 <= area <= 10000 else 0.5
        
        return (aspect_score + area_score) / 2
    
    def _calculate_duct_probability(self, points: List[float], drawing: Dict) -> float:
        """Calculate probability that polyline is ductwork"""
        # Ductwork is typically thin, curved paths
        width = drawing.get('width', 1.0)
        
        if width < 2.0 and len(points) > 6:
            return 0.8
        return 0.2
    
    def _group_parallel_lines(self, lines: List[Dict]) -> List[Dict]:
        """Group parallel lines that might form walls"""
        # Simple implementation - could be enhanced with clustering
        grouped = []
        
        for line in lines:
            # Find nearby parallel lines
            parallel_count = 0
            for other in lines:
                if (line != other and 
                    line['orientation'] == other['orientation'] and
                    self._lines_parallel(line, other)):
                    parallel_count += 1
            
            line['parallel_count'] = parallel_count
            grouped.append(line)
        
        return grouped
    
    def _lines_parallel(self, line1: Dict, line2: Dict, tolerance: float = 10.0) -> bool:
        """Check if two lines are parallel and nearby"""
        # Simplified parallel check based on distance
        dist1 = np.sqrt((line1['x0'] - line2['x0'])**2 + (line1['y0'] - line2['y0'])**2)
        dist2 = np.sqrt((line1['x1'] - line2['x1'])**2 + (line1['y1'] - line2['y1'])**2)
        
        return min(dist1, dist2) < tolerance
    
    def _parse_dimension_text(self, text: str) -> List[float]:
        """
        Parse dimension text like "12'-0"" or "10'" into feet
        Returns list of dimension values in feet
        """
        dimensions = []
        
        # Common dimension patterns
        patterns = [
            r"(\d+)['\s]*-?\s*(\d+)?[\"\s]*",  # 12'-0" or 12'-6"
            r"(\d+\.?\d*)['\s]*",  # 10' or 10.5'
            r"(\d+)[\"\s]*",  # 12" (inches)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2 and groups[1]:  # Feet and inches
                        feet = float(groups[0])
                        inches = float(groups[1])
                        dimensions.append(feet + inches / 12.0)
                    elif "'" in text:  # Just feet
                        dimensions.append(float(groups[0]))
                    elif '"' in text:  # Just inches
                        dimensions.append(float(groups[0]) / 12.0)
                except:
                    continue
        
        return dimensions