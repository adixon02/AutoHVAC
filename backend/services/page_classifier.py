"""
Page Classification Module for Blueprint Analysis
Identifies floor plan pages vs elevation/detail/schedule pages
"""

import cv2
import numpy as np
import logging
from typing import Dict, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PageClassification:
    """Page classification result"""
    page_type: str  # 'floor_plan', 'elevation', 'detail', 'schedule', 'title', 'unknown'
    confidence: float
    features: Dict[str, float]
    floor_level: Optional[str] = None  # 'first', 'second', 'basement', etc.


class PageClassifier:
    """Classify blueprint pages to identify floor plans"""
    
    def __init__(self):
        """Initialize page classifier"""
        self.min_line_length = 50  # Minimum line length to consider
        self.min_contour_area = 1000  # Minimum contour area for rooms
    
    def classify_page(self, image: np.ndarray, ocr_text: List[str] = None) -> PageClassification:
        """Classify a blueprint page
        
        Args:
            image: OpenCV image array (BGR format)
            ocr_text: Optional list of OCR text from the page
            
        Returns:
            PageClassification object
        """
        # Extract features from the image
        features = self._extract_page_features(image)
        
        # Add text-based features if available
        if ocr_text:
            text_features = self._extract_text_features(ocr_text)
            features.update(text_features)
        
        # Classify based on features
        page_type, confidence = self._classify_from_features(features)
        
        # Detect floor level if it's a floor plan
        floor_level = None
        if page_type == 'floor_plan' and ocr_text:
            floor_level = self._detect_floor_level(ocr_text)
        
        return PageClassification(
            page_type=page_type,
            confidence=confidence,
            features=features,
            floor_level=floor_level
        )
    
    def is_floor_plan(self, image: np.ndarray, ocr_text: List[str] = None) -> bool:
        """Quick check if page is a floor plan
        
        Args:
            image: OpenCV image array
            ocr_text: Optional OCR text
            
        Returns:
            True if page is likely a floor plan
        """
        classification = self.classify_page(image, ocr_text)
        return classification.page_type == 'floor_plan' and classification.confidence > 0.6
    
    def _extract_page_features(self, image: np.ndarray) -> Dict[str, float]:
        """Extract visual features from page
        
        Args:
            image: OpenCV image array
            
        Returns:
            Dictionary of feature values
        """
        features = {}
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. Line density (floor plans have many lines)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, 
                               minLineLength=self.min_line_length, maxLineGap=10)
        features['line_count'] = len(lines) if lines is not None else 0
        features['line_density'] = features['line_count'] / (image.shape[0] * image.shape[1] / 1000000)
        
        # 2. Horizontal/Vertical line ratio (floor plans have mostly H/V lines)
        if lines is not None and len(lines) > 0:
            h_lines, v_lines = self._count_hv_lines(lines)
            features['hv_line_ratio'] = (h_lines + v_lines) / len(lines)
        else:
            features['hv_line_ratio'] = 0
        
        # 3. Closed contour count (rooms)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        room_contours = [c for c in contours if cv2.contourArea(c) > self.min_contour_area]
        features['room_count'] = len(room_contours)
        
        # 4. Text density (floor plans have moderate text)
        # This will be updated with OCR results if available
        features['text_density'] = 0.5  # Default placeholder
        
        # 5. Aspect ratio (floor plans are often square-ish)
        features['aspect_ratio'] = image.shape[1] / image.shape[0]
        
        # 6. White space ratio (floor plans have less white space)
        white_pixels = np.sum(gray > 240)
        total_pixels = gray.size
        features['white_space_ratio'] = white_pixels / total_pixels
        
        # 7. Rectangle detection (doors, windows)
        rectangles = self._detect_rectangles(gray)
        features['rectangle_count'] = len(rectangles)
        
        return features
    
    def _extract_text_features(self, ocr_text: List[str]) -> Dict[str, float]:
        """Extract text-based features
        
        Args:
            ocr_text: List of text strings from OCR
            
        Returns:
            Dictionary of text features
        """
        features = {}
        
        all_text = ' '.join(ocr_text).lower()
        
        # Room name indicators
        room_keywords = ['bedroom', 'bath', 'kitchen', 'living', 'dining', 
                        'garage', 'closet', 'hall', 'entry', 'office']
        features['room_keyword_count'] = sum(1 for keyword in room_keywords if keyword in all_text)
        
        # Dimension indicators
        features['has_dimensions'] = 1.0 if any(x in all_text for x in ["'", '"', 'x']) else 0.0
        
        # Scale indicators
        features['has_scale'] = 1.0 if 'scale' in all_text or '=' in all_text else 0.0
        
        # Floor plan specific terms
        plan_terms = ['floor plan', 'first floor', 'second floor', 'level', 'sqft', 'sq ft']
        features['has_plan_terms'] = 1.0 if any(term in all_text for term in plan_terms) else 0.0
        
        # Elevation/section terms (negative indicators)
        elevation_terms = ['elevation', 'section', 'detail', 'schedule', 'diagram']
        features['has_elevation_terms'] = 1.0 if any(term in all_text for term in elevation_terms) else 0.0
        
        # Update text density
        features['text_density'] = len(ocr_text) / 100.0  # Normalized
        
        return features
    
    def _classify_from_features(self, features: Dict[str, float]) -> Tuple[str, float]:
        """Classify page type from features
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of (page_type, confidence)
        """
        # Simple rule-based classification
        # In production, could use ML model trained on labeled data
        
        score = 0.0
        
        # Positive indicators for floor plan
        if features.get('line_density', 0) > 50:
            score += 0.2
        if features.get('hv_line_ratio', 0) > 0.7:
            score += 0.15
        if features.get('room_count', 0) >= 3:
            score += 0.2
        if features.get('room_keyword_count', 0) >= 3:
            score += 0.15
        if features.get('has_dimensions', 0) > 0:
            score += 0.1
        if features.get('has_plan_terms', 0) > 0:
            score += 0.1
        if features.get('white_space_ratio', 0) < 0.7:
            score += 0.1
        
        # Negative indicators
        if features.get('has_elevation_terms', 0) > 0:
            score -= 0.3
        if features.get('aspect_ratio', 1) > 2 or features.get('aspect_ratio', 1) < 0.5:
            score -= 0.1  # Too narrow/wide for floor plan
        
        # Determine page type
        if score >= 0.6:
            return 'floor_plan', min(score, 0.95)
        elif features.get('has_elevation_terms', 0) > 0:
            return 'elevation', 0.8
        elif features.get('text_density', 0) > 2.0:
            return 'schedule', 0.7
        else:
            return 'unknown', 0.5
    
    def _count_hv_lines(self, lines: np.ndarray) -> Tuple[int, int]:
        """Count horizontal and vertical lines
        
        Args:
            lines: Array of lines from HoughLinesP
            
        Returns:
            Tuple of (horizontal_count, vertical_count)
        """
        h_count = 0
        v_count = 0
        angle_threshold = 10  # degrees
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Calculate angle
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            if angle < angle_threshold or angle > 180 - angle_threshold:
                h_count += 1
            elif 90 - angle_threshold < angle < 90 + angle_threshold:
                v_count += 1
        
        return h_count, v_count
    
    def _detect_rectangles(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect rectangles (potential doors/windows)
        
        Args:
            gray: Grayscale image
            
        Returns:
            List of rectangle bounding boxes
        """
        rectangles = []
        
        # Find contours
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Approximate contour to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Check if it's a rectangle (4 vertices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                area = w * h
                
                # Filter by size (doors/windows are small-medium)
                if 100 < area < 5000:
                    rectangles.append((x, y, w, h))
        
        return rectangles
    
    def _detect_floor_level(self, ocr_text: List[str]) -> Optional[str]:
        """Detect floor level from OCR text
        
        Args:
            ocr_text: List of text strings
            
        Returns:
            Floor level string or None
        """
        all_text = ' '.join(ocr_text).lower()
        
        # Floor level patterns
        patterns = {
            'first': ['first floor', '1st floor', 'ground floor', 'level 1', 'floor 1'],
            'second': ['second floor', '2nd floor', 'upper floor', 'level 2', 'floor 2'],
            'basement': ['basement', 'lower level', 'level b', 'floor b'],
            'third': ['third floor', '3rd floor', 'level 3', 'floor 3']
        }
        
        for level, terms in patterns.items():
            if any(term in all_text for term in terms):
                return level
        
        return None


# Create singleton instance
page_classifier = PageClassifier()