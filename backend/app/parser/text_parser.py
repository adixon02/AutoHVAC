"""
Advanced text parser for architectural PDFs
Extracts room labels, dimensions, and notes using pdfplumber + OCR
"""

import pdfplumber
import fitz  # PyMuPDF for image extraction
from PIL import Image
import cv2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ocr_extractor import OCRExtractor
import re
import logging
import traceback
import threading
import time
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from io import BytesIO
from .schema import RawText
from services.pdf_thread_manager import safe_pdfplumber_operation, safe_pymupdf_operation

logger = logging.getLogger(__name__)


class TextParser:
    """Elite text extraction for HVAC blueprints"""
    
    def __init__(self):
        # Initialize OCR extractor
        self.ocr_extractor = OCRExtractor(use_gpu=False)
        self.room_keywords = [
            'bedroom', 'living', 'kitchen', 'bathroom', 'dining', 'office',
            'family', 'master', 'guest', 'utility', 'laundry', 'closet',
            'hall', 'foyer', 'pantry', 'garage', 'basement', 'attic',
            'den', 'study', 'library', 'sunroom', 'porch', 'deck'
        ]
        
        self.dimension_patterns = [
            r"(\d+)'\s*-?\s*(\d+)\"?",           # 12'-6"
            r"(\d+)'\s*(\d+)\"",                 # 12'6"
            r"(\d+)'",                           # 12'
            r"(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)", # 12.5 x 15.0
            r"(\d+)\s*[xX]\s*(\d+)",            # 12 x 15
        ]
    
    # Removed _retry_on_document_closed - now using thread-safe PDF manager
    
    def parse(self, pdf_path: str, page_number: int = 0) -> RawText:
        """
        Extract text elements from architectural PDF using thread-safe operations
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number to parse (default: 0)
            
        Returns:
            RawText with all extracted text elements
        """
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting thread-safe text parsing")
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
        
        try:
            # Extract words using thread-safe pdfplumber operation
            def pdfplumber_operation(pdf):
                logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF in pdfplumber operation for: {pdf_path}")
                
                if page_number >= len(pdf.pages) or page_number < 0:
                    logger.error(f"[Thread {thread_name}:{thread_id}] Invalid page number {page_number + 1}, PDF has {len(pdf.pages)} pages")
                    raise ValueError(f"Page {page_number + 1} does not exist (PDF has {len(pdf.pages)} pages)")
                
                page = pdf.pages[page_number]
                logger.info(f"[Thread {thread_name}:{thread_id}] Processing page {page_number + 1} of {len(pdf.pages)} via pdfplumber")
                logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                
                # CRITICAL: Extract words directly here - do NOT pass page object to another function
                words = []
                logger.info(f"[Thread {thread_name}:{thread_id}] Extracting words from pdfplumber page object")
                
                try:
                    raw_words = page.extract_words()
                    logger.info(f"[Thread {thread_name}:{thread_id}] Found {len(raw_words)} raw words from pdfplumber")
                    
                    for word in raw_words:
                        words.append({
                            'text': str(word['text']),
                            'x0': float(word['x0']),
                            'top': float(word['top']),
                            'x1': float(word['x1']),
                            'bottom': float(word['bottom']),
                            'width': float(word['x1'] - word['x0']),
                            'height': float(word['bottom'] - word['top']),
                            'size': float(word.get('size', 12)),
                            'font': word.get('fontname', ''),
                            'source': 'pdfplumber'
                        })
                        
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
                        logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in pdfplumber word extraction")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
                    else:
                        logger.error(f"[Thread {thread_name}:{thread_id}] Error extracting words from pdfplumber: {e}")
                        logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
                    raise
                
                return words
            
            words = safe_pdfplumber_operation(
                pdf_path, 
                pdfplumber_operation, 
                f"pdfplumber_text_extraction_page_{page_number + 1}",
                max_retries=2
            )
            logger.info(f"[Thread {thread_name}:{thread_id}] Extracted {len(words)} words with pdfplumber")
            
            # Extract words using thread-safe OCR operation  
            ocr_words = self._extract_words_ocr_safe(pdf_path, page_number)
            logger.info(f"[Thread {thread_name}:{thread_id}] Extracted {len(ocr_words)} words with OCR")
            
            # Combine and deduplicate
            all_words = self._merge_word_lists(words, ocr_words)
            logger.info(f"[Thread {thread_name}:{thread_id}] Combined total: {len(all_words)} words")
            
            # Classify text elements
            room_labels = self._identify_room_labels(all_words)
            dimensions = self._identify_dimensions(all_words)
            notes = self._identify_notes(all_words)
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Text parsing completed: {len(room_labels)} rooms, {len(dimensions)} dimensions, {len(notes)} notes")
            logger.info(f"[Thread {thread_name}:{thread_id}] Final word count: {len(all_words)}")
            
            return RawText(
                words=all_words,
                room_labels=room_labels,
                dimensions=dimensions,
                notes=notes
            )
            
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
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in text parsing")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                logger.error(f"[Thread {thread_name}:{thread_id}] Text parsing failed: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            raise
    
    
    def _extract_words_ocr_safe(self, pdf_path: str, page_number: int = 0) -> List[Dict[str, Any]]:
        """Extract words using OCR with thread-safe operations"""
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        
        logger.info(f"[Thread {thread_name}:{thread_id}] Starting OCR text extraction")
        logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
        logger.info(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
        
        if not self.ocr_extractor or not self.ocr_extractor.ocr:
            logger.info(f"[Thread {thread_name}:{thread_id}] PaddleOCR not available, skipping")
            return []
        
        def ocr_operation(doc):
            """OCR operation to be executed thread-safely"""
            logger.info(f"[Thread {thread_name}:{thread_id}] Opening PDF in OCR operation for: {pdf_path}")
            
            if page_number >= len(doc) or page_number < 0:
                logger.warning(f"[Thread {thread_name}:{thread_id}] Invalid page number {page_number + 1} for OCR, PDF has {len(doc)} pages")
                return []
                
            page = doc[page_number]
            logger.info(f"[Thread {thread_name}:{thread_id}] Rendering page {page_number + 1} for OCR")
            logger.info(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
            
            # Render page as image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            
            # Convert to numpy array for PaddleOCR
            img = Image.open(BytesIO(img_data))
            img_array = np.array(img)
            # Convert RGB to BGR for OpenCV/PaddleOCR
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            logger.info(f"[Thread {thread_name}:{thread_id}] Running PaddleOCR on rendered page")
            
            # Use PaddleOCR to extract text
            text_regions = self.ocr_extractor.extract_all_text(img_array)
            
            # Process OCR results
            words = []
            for region in text_regions:
                if region.text.strip() and region.confidence > 0.3:  # Confidence threshold
                    # Get bounding box corners
                    bbox = region.bbox
                    x = float(min(point[0] for point in bbox)) / 2  # Adjust for 2x zoom
                    y = float(min(point[1] for point in bbox)) / 2
                    
                    # Calculate width and height from bounding box
                    w = float(max(point[0] for point in bbox)) / 2 - x
                    h = float(max(point[1] for point in bbox)) / 2 - y
                    
                    words.append({
                        'text': region.text.strip(),
                        'x0': x,
                        'top': y,
                        'x1': x + w,
                        'bottom': y + h,
                        'width': w,
                        'height': h,
                        'size': h,  # Approximate font size
                        'font': 'paddleocr',
                        'confidence': region.confidence,
                        'source': 'paddleocr'
                    })
            
            logger.info(f"[Thread {thread_name}:{thread_id}] OCR completed, found {len(words)} words")
            return words
        
        try:
            result = safe_pymupdf_operation(
                pdf_path,
                ocr_operation,
                f"ocr_extraction_page_{page_number + 1}",
                max_retries=2
            )
            logger.info(f"[Thread {thread_name}:{thread_id}] OCR extraction completed, found {len(result)} words")
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
                logger.error(f"[Thread {thread_name}:{thread_id}] DOCUMENT CLOSED ERROR in OCR extraction")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error type: {type(e).__name__}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Error message: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread ID: {thread_id}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Thread name: {thread_name}")
                logger.error(f"[Thread {thread_name}:{thread_id}] FULL STACK TRACE:\n{traceback.format_exc()}")
            else:
                logger.error(f"[Thread {thread_name}:{thread_id}] OCR extraction failed: {type(e).__name__}: {str(e)}")
                logger.error(f"[Thread {thread_name}:{thread_id}] PDF file: {pdf_path}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Page number: {page_number + 1}")
                logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            
            return []  # Don't fail completely, just return empty results
    
    def _merge_word_lists(self, words1: List[Dict], words2: List[Dict]) -> List[Dict]:
        """Merge word lists and remove duplicates"""
        all_words = words1.copy()
        
        for word2 in words2:
            # Check if this word is already captured by pdfplumber
            is_duplicate = False
            for word1 in words1:
                if (abs(word1['x0'] - word2['x0']) < 10 and 
                    abs(word1['top'] - word2['top']) < 10 and
                    word1['text'].lower() == word2['text'].lower()):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                all_words.append(word2)
        
        return all_words
    
    def _identify_room_labels(self, words: List[Dict]) -> List[Dict[str, Any]]:
        """Identify words that are likely room labels"""
        room_labels = []
        
        for word in words:
            text = word['text'].lower()
            
            # Check if text contains room keywords
            is_room = False
            for keyword in self.room_keywords:
                if keyword in text:
                    is_room = True
                    break
            
            # Additional heuristics
            if not is_room:
                # Check for numbered rooms
                if re.match(r'(bed|bath|room)\s*\d+', text):
                    is_room = True
                # Check for common abbreviations
                elif text in ['br', 'ba', 'kit', 'lr', 'dr', 'mb']:
                    is_room = True
            
            if is_room:
                room_labels.append({
                    **word,
                    'room_type': self._classify_room_type(word['text']),
                    'confidence': self._calculate_room_confidence(word)
                })
        
        return room_labels
    
    def _identify_dimensions(self, words: List[Dict]) -> List[Dict[str, Any]]:
        """Identify dimension annotations"""
        dimensions = []
        
        for word in words:
            text = word['text']
            
            # Check against dimension patterns
            for pattern in self.dimension_patterns:
                match = re.search(pattern, text)
                if match:
                    dimensions.append({
                        **word,
                        'dimension_text': text,
                        'parsed_dimensions': self._parse_dimension(text, match),
                        'confidence': 0.9 if "'" in text or '"' in text else 0.7
                    })
                    break
        
        return dimensions
    
    def _identify_notes(self, words: List[Dict]) -> List[Dict[str, Any]]:
        """Identify notes and annotations"""
        notes = []
        note_keywords = ['note', 'spec', 'see', 'typ', 'detail', 'section']
        
        for word in words:
            text = word['text'].lower()
            
            # Check for note indicators
            if any(keyword in text for keyword in note_keywords):
                notes.append({
                    **word,
                    'note_type': 'specification',
                    'confidence': 0.8
                })
            # Check for parenthetical notes
            elif '(' in word['text'] and ')' in word['text']:
                notes.append({
                    **word,
                    'note_type': 'parenthetical',
                    'confidence': 0.6
                })
        
        return notes
    
    def _classify_room_type(self, text: str) -> str:
        """Classify the type of room"""
        text = text.lower()
        
        if any(word in text for word in ['bed', 'br']):
            return 'bedroom'
        elif any(word in text for word in ['bath', 'ba']):
            return 'bathroom'
        elif any(word in text for word in ['kitchen', 'kit']):
            return 'kitchen'
        elif any(word in text for word in ['living', 'lr']):
            return 'living'
        elif any(word in text for word in ['dining', 'dr']):
            return 'dining'
        else:
            return 'other'
    
    def _calculate_room_confidence(self, word: Dict) -> float:
        """Calculate confidence that this is a room label"""
        confidence = 0.5
        
        # Larger text is more likely to be room labels
        if word['size'] > 10:
            confidence += 0.2
        
        # Text in certain positions (center of rectangles) more likely
        # This would require geometry context
        
        # OCR text is less reliable
        if word.get('source') == 'ocr':
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _parse_dimension(self, text: str, match) -> Tuple[float, float]:
        """Parse dimension text into numeric values"""
        try:
            groups = match.groups()
            
            if "'" in text:  # Architectural format
                feet = float(groups[0])
                inches = float(groups[1]) if len(groups) > 1 and groups[1] else 0
                return (feet + inches / 12, 0)  # Convert to decimal feet
            elif 'x' in text.lower():  # Width x Height
                return (float(groups[0]), float(groups[1]))
            else:
                return (float(groups[0]), 0)
                
        except (ValueError, IndexError):
            return (0, 0)
    
    def get_text_near_point(self, words: List[Dict], x: float, y: float, radius: float = 50) -> List[Dict]:
        """Find text elements near a specific point"""
        nearby = []
        
        for word in words:
            # Calculate distance from point to word center
            word_center_x = (word['x0'] + word['x1']) / 2
            word_center_y = (word['top'] + word['bottom']) / 2
            
            distance = np.sqrt((x - word_center_x)**2 + (y - word_center_y)**2)
            
            if distance <= radius:
                nearby.append({
                    **word,
                    'distance': distance
                })
        
        return sorted(nearby, key=lambda w: w['distance'])
    
    def group_text_lines(self, words: List[Dict], tolerance: float = 5) -> List[List[Dict]]:
        """Group words into text lines"""
        lines = []
        used_words = set()
        
        for word in words:
            if id(word) in used_words:
                continue
                
            line = [word]
            used_words.add(id(word))
            
            # Find words on the same horizontal line
            for other_word in words:
                if (id(other_word) not in used_words and
                    abs(word['top'] - other_word['top']) < tolerance):
                    line.append(other_word)
                    used_words.add(id(other_word))
            
            # Sort words in line by x position
            line.sort(key=lambda w: w['x0'])
            lines.append(line)
        
        return lines
    
    def score_room_labels_for_floor_plan(self, words: List[Dict]) -> Dict[str, Any]:
        """
        Score the room labels found in text for floor plan likelihood
        
        Args:
            words: List of word dictionaries from text extraction
            
        Returns:
            Dictionary with room label scoring metrics
        """
        room_labels = self._identify_room_labels(words)
        
        # Count different types of room labels
        room_types = {}
        total_confidence = 0.0
        
        for label in room_labels:
            room_type = label.get('room_type', 'other')
            confidence = label.get('confidence', 0.5)
            
            if room_type not in room_types:
                room_types[room_type] = {'count': 0, 'total_confidence': 0.0}
            
            room_types[room_type]['count'] += 1
            room_types[room_type]['total_confidence'] += confidence
            total_confidence += confidence
        
        # Calculate diversity score (more room types = better floor plan)
        diversity_score = len(room_types) * 10
        
        # Calculate confidence score
        avg_confidence = total_confidence / len(room_labels) if room_labels else 0.0
        confidence_score = avg_confidence * 20
        
        # Essential room bonus (bedrooms, bathrooms, living areas)
        essential_rooms = {'bedroom', 'bathroom', 'living', 'kitchen'}
        essential_found = sum(1 for rt in essential_rooms if rt in room_types)
        essential_bonus = essential_found * 15
        
        # Calculate total room label score
        total_score = diversity_score + confidence_score + essential_bonus
        
        return {
            'total_room_labels': len(room_labels),
            'room_types_found': len(room_types),
            'room_type_breakdown': room_types,
            'average_confidence': round(avg_confidence, 3),
            'diversity_score': diversity_score,
            'confidence_score': round(confidence_score, 1),
            'essential_bonus': essential_bonus,
            'total_score': round(total_score, 1),
            'floor_plan_probability': min(total_score / 100, 1.0)  # Normalize to 0-1
        }
    
    def count_dimension_annotations(self, words: List[Dict]) -> Dict[str, Any]:
        """
        Count and analyze dimension annotations in text
        
        Args:
            words: List of word dictionaries from text extraction
            
        Returns:
            Dictionary with dimension analysis metrics
        """
        dimensions = self._identify_dimensions(words)
        
        # Categorize dimensions by pattern type
        pattern_counts = {}
        total_confidence = 0.0
        
        for dim in dimensions:
            confidence = dim.get('confidence', 0.5)
            text = dim.get('dimension_text', '')
            
            # Categorize by pattern
            if "'" in text and '"' in text:
                pattern_type = 'architectural'  # Feet and inches
                confidence_weight = 1.0
            elif "'" in text:
                pattern_type = 'feet_only'
                confidence_weight = 0.8
            elif 'x' in text.lower():
                pattern_type = 'area_dimensions'
                confidence_weight = 0.7
            else:
                pattern_type = 'other'
                confidence_weight = 0.5
            
            if pattern_type not in pattern_counts:
                pattern_counts[pattern_type] = {'count': 0, 'total_confidence': 0.0}
            
            pattern_counts[pattern_type]['count'] += 1
            pattern_counts[pattern_type]['total_confidence'] += confidence * confidence_weight
            total_confidence += confidence * confidence_weight
        
        # Calculate dimension score
        architectural_bonus = pattern_counts.get('architectural', {}).get('count', 0) * 8
        dimension_score = len(dimensions) * 5 + architectural_bonus
        
        return {
            'total_dimensions': len(dimensions),
            'pattern_breakdown': pattern_counts,
            'architectural_dimensions': pattern_counts.get('architectural', {}).get('count', 0),
            'total_confidence': round(total_confidence, 2),
            'dimension_score': dimension_score,
            'floor_plan_probability': min(dimension_score / 50, 1.0)  # Normalize to 0-1
        }
    
    def analyze_text_for_floor_plan(self, pdf_path: str, page_number: int = 0) -> Dict[str, Any]:
        """
        Comprehensive text analysis for floor plan detection
        
        Args:
            pdf_path: Path to PDF file
            page_number: Zero-based page number to analyze
            
        Returns:
            Dictionary with complete text analysis for floor plan scoring
        """
        try:
            # Extract text from specified page
            raw_text = self.parse(pdf_path, page_number)
            
            # Perform various analyses
            room_analysis = self.score_room_labels_for_floor_plan(raw_text.words)
            dimension_analysis = self.count_dimension_annotations(raw_text.words)
            
            # Overall text score
            text_score = room_analysis['total_score'] + dimension_analysis['dimension_score']
            
            return {
                'page_number': page_number + 1,
                'total_words': len(raw_text.words),
                'room_analysis': room_analysis,
                'dimension_analysis': dimension_analysis,
                'text_score': round(text_score, 1),
                'floor_plan_probability': round((room_analysis['floor_plan_probability'] + 
                                               dimension_analysis['floor_plan_probability']) / 2, 3)
            }
            
        except Exception as e:
            import threading
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            logger.error(f"[Thread {thread_name}:{thread_id}] Error analyzing text for page {page_number + 1}: {str(e)}")
            logger.error(f"[Thread {thread_name}:{thread_id}] Full traceback:\n{traceback.format_exc()}")
            return {
                'page_number': page_number + 1,
                'total_words': 0,
                'room_analysis': {},
                'dimension_analysis': {},
                'text_score': 0.0,
                'floor_plan_probability': 0.0,
                'error': str(e)
            }