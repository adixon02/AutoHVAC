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
from services.pdf_thread_manager import safe_pdfplumber_operation, safe_pymupdf_operation

logger = logging.getLogger(__name__)


class GeometryParser:
    """Advanced PDF geometry extraction for HVAC blueprints"""
    
    def __init__(self):
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
        
        # Defensive limits to prevent infinite processing
        self.MAX_LINES = 10000
        self.MAX_RECTANGLES = 5000
        self.MAX_POLYLINES = 2000
        self.MAX_DRAWING_ITEMS = 1000
    
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
                
                # CRITICAL: Detect scale directly - no method calls with page objects
                logger.info(f"[Thread {thread_name}:{thread_id}] Detecting scale markers...")
                scale_start = time.time()
                scale_factor = None
                try:
                    words = page.extract_words()
                    text = ' '.join([w['text'] for w in words])
                    
                    for i, pattern in enumerate(self.scale_patterns):
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            try:
                                groups = match.groups()
                                
                                # Handle different pattern types
                                if i == 0:  # 1/4" = 1'-0" pattern
                                    denominator = float(groups[0])
                                    scale_factor = 12.0 * denominator  # e.g., 1/4" = 48
                                elif i == 1:  # 1" = 20'-0" pattern
                                    feet = float(groups[0])
                                    inches = float(groups[1]) if len(groups) > 1 and groups[1] else 0
                                    scale_factor = (feet * 12 + inches)
                                elif i in [2, 6]:  # Ratio patterns like 1:48
                                    if len(groups) >= 2:
                                        scale_factor = float(groups[1]) / float(groups[0])
                                    else:
                                        scale_factor = float(groups[0])
                                elif i == 3:  # SCALE: 1/4 pattern
                                    denominator = float(groups[0])
                                    scale_factor = 12.0 * denominator
                                elif i == 5:  # 1" = 8' pattern
                                    inch_val = float(groups[0]) if groups[0] else 1
                                    feet_val = float(groups[1])
                                    scale_factor = (feet_val * 12) / inch_val
                                else:
                                    # Default to 1/4" scale if we can't parse
                                    scale_factor = 48.0
                                
                                logger.info(f"[Thread {thread_name}:{thread_id}] Detected scale from pattern {i}: {scale_factor} ({match.group()})")
                                break
                            except Exception as e:
                                logger.debug(f"[Thread {thread_name}:{thread_id}] Failed to parse scale with pattern {i}: {e}")
                                continue
                except Exception as e:
                    logger.warning(f"[Thread {thread_name}:{thread_id}] Scale detection failed: {e}")
                
                logger.info(f"[Thread {thread_name}:{thread_id}] Scale detection took {time.time() - scale_start:.2f}s, result: {scale_factor}")
                
                # CRITICAL: Extract lines directly - no method calls with page objects
                logger.info(f"[Thread {thread_name}:{thread_id}] Extracting lines...")
                lines_start = time.time()
                lines = []
                
                try:
                    raw_lines = page.lines
                    logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(raw_lines)} raw lines to process")
                    
                    # Apply defensive limit
                    if len(raw_lines) > self.MAX_LINES:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] Too many lines ({len(raw_lines)}), limiting to {self.MAX_LINES}")
                        raw_lines = raw_lines[:self.MAX_LINES]
                    
                    for i, line in enumerate(raw_lines):
                        try:
                            x0, y0, x1, y1 = line['x0'], line['y0'], line['x1'], line['y1']
                            
                            # Validate coordinates
                            if any(coord is None for coord in [x0, y0, x1, y1]):
                                continue
                            
                            length = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
                            
                            # Skip degenerate lines
                            if length < 0.1:
                                continue
                            
                            width = float(line.get('width', 1.0))
                            
                            lines.append({
                                'type': 'line',
                                'coords': [float(x0), float(y0), float(x1), float(y1)],
                                'x0': float(x0),
                                'y0': float(y0),
                                'x1': float(x1),
                                'y1': float(y1),
                                'width': width,
                                'length': float(length),
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
                    
                    # Apply defensive limit
                    if len(raw_rects) > self.MAX_RECTANGLES:
                        logger.warning(f"[Thread {thread_name}:{thread_id}] Too many rectangles ({len(raw_rects)}), limiting to {self.MAX_RECTANGLES}")
                        raw_rects = raw_rects[:self.MAX_RECTANGLES]
                    
                    # Calculate scale-aware thresholds for rectangle filtering
                    if scale_factor and scale_factor > 0:
                        # Convert room size limits from square feet to page units
                        # Using the detected scale factor
                        min_room_sqft = 10  # Minimum room size in square feet (smaller for closets)
                        max_room_sqft = 1200  # Maximum room size in square feet (larger for open spaces)
                        
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
                                
                                rectangles.append({
                                    'type': 'rect',
                                    'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                                    'x0': float(rect['x0']),
                                    'y0': float(rect['y0']),
                                    'x1': float(rect['x1']),
                                    'y1': float(rect['y1']),
                                    'width': width,
                                    'height': height,
                                    'area': area,
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
                                        logger.debug(f"[Thread {thread_name}:{thread_id}] Rectangle {i} filtered: too small ({est_sqft:.0f} sq ft < {min_room_sqft} sq ft)")
                            
                        except Exception as e:
                            logger.debug(f"[Thread {thread_name}:{thread_id}] Error processing rectangle {i}: {e}")
                            continue
                    
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
            
            # Extract polylines using thread-safe PyMuPDF operation
            logger.info(f"[Thread {thread_name}:{thread_id}] Extracting polylines with PyMuPDF...")
            poly_start = time.time()
            polylines = self._extract_polylines_pymupdf_safe(pdf_path, page_number)
            logger.info(f"[Thread {thread_name}:{thread_id}] Polyline extraction took {time.time() - poly_start:.2f}s, found {len(polylines)} polylines")
            
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
                        rectangles.append({
                            'type': 'rect',
                            'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                            'x0': float(rect['x0']),
                            'y0': float(rect['y0']),
                            'x1': float(rect['x1']),
                            'y1': float(rect['y1']),
                            'width': width,
                            'height': height,
                            'area': area,
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