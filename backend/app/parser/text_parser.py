"""
Advanced text parser for architectural PDFs
Extracts room labels, dimensions, and notes using pdfplumber + OCR
"""

import pdfplumber
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("Warning: pytesseract not available, OCR functionality disabled")
import fitz  # PyMuPDF for image extraction
import re
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from io import BytesIO
from .schema import RawText


class TextParser:
    """Elite text extraction for HVAC blueprints"""
    
    def __init__(self):
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
    
    def parse(self, pdf_path: str) -> RawText:
        """
        Extract text elements from architectural PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            RawText with all extracted text elements
        """
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # Process first page
            
            # Extract words using pdfplumber
            words = self._extract_words_pdfplumber(page)
            
            # Try OCR for any missed text
            ocr_words = self._extract_words_ocr(pdf_path)
            
            # Combine and deduplicate
            all_words = self._merge_word_lists(words, ocr_words)
            
            # Classify text elements
            room_labels = self._identify_room_labels(all_words)
            dimensions = self._identify_dimensions(all_words)
            notes = self._identify_notes(all_words)
            
            return RawText(
                words=all_words,
                room_labels=room_labels,
                dimensions=dimensions,
                notes=notes
            )
    
    def _extract_words_pdfplumber(self, page) -> List[Dict[str, Any]]:
        """Extract words using pdfplumber"""
        words = []
        raw_words = page.extract_words()
        
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
        
        return words
    
    def _extract_words_ocr(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract words using OCR for handwritten/unclear text"""
        words = []
        
        if not PYTESSERACT_AVAILABLE:
            return words
        
        try:
            # Check if tesseract is available
            try:
                pytesseract.get_tesseract_version()
            except (pytesseract.TesseractNotFoundError, FileNotFoundError) as e:
                print(f"Tesseract OCR not found in PATH: {e}")
                return words
            
            # Convert PDF page to image using PyMuPDF
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Render page as image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            
            # Convert to PIL Image
            img = Image.open(BytesIO(img_data))
            
            # OCR with bounding boxes
            ocr_data = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Uniform block of text
            )
            
            # Process OCR results
            for i, text in enumerate(ocr_data['text']):
                if text.strip() and int(ocr_data['conf'][i]) > 30:  # Confidence threshold
                    x = float(ocr_data['left'][i]) / 2  # Adjust for 2x zoom
                    y = float(ocr_data['top'][i]) / 2
                    w = float(ocr_data['width'][i]) / 2
                    h = float(ocr_data['height'][i]) / 2
                    
                    words.append({
                        'text': text.strip(),
                        'x0': x,
                        'top': y,
                        'x1': x + w,
                        'bottom': y + h,
                        'width': w,
                        'height': h,
                        'size': h,  # Approximate font size
                        'font': 'ocr',
                        'confidence': int(ocr_data['conf'][i]),
                        'source': 'ocr'
                    })
            
            doc.close()
            
        except pytesseract.TesseractNotFoundError as e:
            print(f"Tesseract OCR not installed or not in PATH: {e}")
        except ImportError as e:
            print(f"Required OCR dependencies not available: {e}")
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            # Don't fail completely, just log the error
        
        return words
    
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