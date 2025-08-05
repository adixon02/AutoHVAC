"""
Robust scale detection for architectural blueprints
Handles various scales and formats with confidence scoring
"""

import re
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScaleResult:
    """Result of scale detection with confidence metrics"""
    scale_factor: float  # pixels per foot
    confidence: float  # 0.0 to 1.0
    detection_method: str
    validation_results: Dict[str, bool]
    alternative_scales: List[Tuple[float, float]]  # (scale, confidence) pairs


class ScaleDetector:
    """
    Multi-method scale detection for blueprints
    Combines text parsing, dimension verification, and room size validation
    """
    
    # Common architectural scales (scale notation -> pixels per foot at 72 DPI)
    # Note: These are based on the fact that 1 inch = 72 pixels at 72 DPI
    # For 1/4"=1', that means 1/4 inch on paper = 1 foot in real life
    # So 1 foot in real life = 0.25 inches on paper = 0.25 * 72 = 18 pixels
    # However, PDFs are often rendered at higher effective resolution
    # We'll multiply by a typical PDF rendering factor
    COMMON_SCALES = {
        "1\"=1'": 72.0,      # 1 inch = 1 foot
        "3/4\"=1'": 54.0,    # 3/4 inch = 1 foot  
        "1/2\"=1'": 36.0,    # 1/2 inch = 1 foot
        "3/8\"=1'": 27.0,    # 3/8 inch = 1 foot
        "1/4\"=1'": 48.0,    # 1/4 inch = 1 foot (very common) - adjusted for typical PDF rendering
        "3/16\"=1'": 36.0,   # 3/16 inch = 1 foot - adjusted
        "1/8\"=1'": 96.0,    # 1/8 inch = 1 foot (common for large buildings) - adjusted
        "3/32\"=1'": 18.0,   # 3/32 inch = 1 foot - adjusted
        "1/16\"=1'": 12.0,   # 1/16 inch = 1 foot - adjusted
    }
    
    # Typical room size ranges (in square feet)
    ROOM_SIZE_RANGES = {
        'bedroom': (80, 400),
        'bathroom': (20, 120),
        'kitchen': (70, 300),
        'living': (150, 500),
        'dining': (100, 300),
        'closet': (10, 100),
        'hallway': (20, 200),
        'garage': (200, 800),
        'master': (150, 500),
        'office': (70, 250),
        'laundry': (30, 100),
        'pantry': (15, 80),
    }
    
    # Typical total home sizes
    MIN_HOME_SIZE = 500  # sq ft
    MAX_HOME_SIZE = 10000  # sq ft
    TYPICAL_HOME_RANGE = (1000, 4000)  # Most common
    
    def __init__(self, dpi: float = 72.0):
        self.dpi = dpi
        # Adjust common scales for actual DPI
        self.adjusted_scales = {
            k: v * (dpi / 72.0) for k, v in self.COMMON_SCALES.items()
        }
        
    def detect_scale(
        self,
        text_elements: List[Dict[str, Any]],
        dimensions: List[Dict[str, Any]],
        rectangles: List[Dict[str, Any]],
        lines: List[Dict[str, Any]],
        page_width: float,
        page_height: float
    ) -> ScaleResult:
        """
        Main entry point for scale detection
        Combines multiple detection methods and returns best result with confidence
        """
        logger.info("Starting multi-method scale detection")
        
        results = []
        
        # Method 1: Direct text notation detection
        text_scale = self._detect_from_text_notation(text_elements)
        if text_scale:
            results.append(text_scale)
            logger.info(f"Text notation found scale: {text_scale[0]:.1f} px/ft (confidence: {text_scale[1]:.2f})")
        
        # Method 2: Dimension measurement verification
        dim_scale = None
        if dimensions:
            dim_scale = self._verify_from_dimensions(dimensions, lines)
            if dim_scale:
                results.append(dim_scale)
                logger.info(f"Dimension verification found scale: {dim_scale[0]:.1f} px/ft (confidence: {dim_scale[1]:.2f})")
        
        # Method 3: Room size validation approach
        if not results:
            # Try common scales and validate room sizes
            validated_scales = self._test_scales_by_room_sizes(rectangles, text_elements)
            results.extend(validated_scales)
            if validated_scales:
                logger.info(f"Room size validation found {len(validated_scales)} potential scales")
        
        # Method 4: Page size heuristics
        if not results:
            page_scale = self._estimate_from_page_size(page_width, page_height)
            if page_scale:
                results.append(page_scale)
                logger.info(f"Page size heuristics estimated scale: {page_scale[0]:.1f} px/ft (confidence: {page_scale[1]:.2f})")
        
        # Select best result
        if results:
            # Sort by confidence
            results.sort(key=lambda x: x[1], reverse=True)
            best_scale, best_confidence = results[0]
            
            # Validate the best scale
            validation = self._validate_scale(best_scale, rectangles, text_elements)
            
            # Adjust confidence based on validation
            if validation['rooms_reasonable']:
                best_confidence = min(1.0, best_confidence * 1.2)
            else:
                best_confidence *= 0.7
                
            method = self._determine_detection_method(best_scale, text_scale, dim_scale)
            
            return ScaleResult(
                scale_factor=best_scale,
                confidence=best_confidence,
                detection_method=method,
                validation_results=validation,
                alternative_scales=results[:3]  # Top 3 alternatives
            )
        
        # Fallback: Use most common scale with low confidence
        logger.warning("No scale detected, using default 1/4\"=1' scale")
        default_scale = 48.0 * (self.dpi / 72.0)
        
        return ScaleResult(
            scale_factor=default_scale,
            confidence=0.3,
            detection_method="fallback_default",
            validation_results={'rooms_reasonable': False, 'total_area_reasonable': False},
            alternative_scales=[(24.0 * (self.dpi / 72.0), 0.2), (96.0 * (self.dpi / 72.0), 0.2)]
        )
    
    def _detect_from_text_notation(self, text_elements: List[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
        """
        Detect scale from explicit text notation like "SCALE: 1/4"=1'-0"
        """
        # Scale patterns with proper calculation
        # For architectural scales like 1/4"=1', we need to calculate pixels per foot
        # Standard PDF rendering often uses higher effective resolution than 72 DPI
        # We normalize based on common blueprint scales
        scale_patterns = [
            # Standard architectural notation - adjusted for typical PDF rendering
            (r'scale[:\s]*1/(\d+)["\s]*=["\s]*1', lambda m: 48.0 * (4.0 / float(m.group(1)))),  # 1/4"=48px, 1/8"=96px
            (r'scale[:\s]*(\d+)/(\d+)["\s]*=["\s]*1', lambda m: 48.0 * (4.0 * float(m.group(1)) / float(m.group(2)))),
            (r'1/(\d+)["\s]*=["\s]*1[\'"-]', lambda m: 48.0 * (4.0 / float(m.group(1)))),
            (r'(\d+)/(\d+)["\s]*=["\s]*1[\'"-]', lambda m: 48.0 * (4.0 * float(m.group(1)) / float(m.group(2)))),
            # Metric scales
            (r'1:(\d+)', lambda m: 72.0 / (float(m.group(1)) * 12.0)),  # 1:50 means 1 unit = 50 units
            (r'scale[:\s]*1:(\d+)', lambda m: 72.0 / (float(m.group(1)) * 12.0)),
        ]
        
        for element in text_elements:
            text = element.get('text', '').lower()
            
            for pattern, scale_func in scale_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        scale = scale_func(match) * (self.dpi / 72.0)
                        # Sanity check
                        if 2.0 <= scale <= 200.0:
                            logger.info(f"Found scale notation '{match.group()}' -> {scale:.1f} px/ft")
                            return (scale, 0.9)  # High confidence for explicit notation
                    except:
                        continue
        
        return None
    
    def _verify_from_dimensions(self, dimensions: List[Dict[str, Any]], lines: List[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
        """
        Verify scale by measuring labeled dimensions against their pixel lengths
        """
        verified_scales = []
        
        for dim in dimensions:
            # Look for dimension text like "12'-0"" or "10'"
            text = dim.get('dimension_text', '')
            parsed = dim.get('parsed_dimensions', [])
            
            if not parsed or len(parsed) < 1:
                continue
                
            # Get the dimension value in feet
            dim_feet = parsed[0] if isinstance(parsed[0], (int, float)) else None
            if not dim_feet or dim_feet <= 0:
                continue
            
            # Find the dimension line (look for nearby lines)
            dim_x = dim.get('x0', 0)
            dim_y = dim.get('top', dim.get('y0', 0))
            
            # Find horizontal or vertical lines near this dimension
            for line in lines:
                line_x0, line_y0 = line.get('x0', 0), line.get('y0', 0)
                line_x1, line_y1 = line.get('x1', 0), line.get('y1', 0)
                
                # Check if dimension is near this line
                line_center_x = (line_x0 + line_x1) / 2
                line_center_y = (line_y0 + line_y1) / 2
                
                dist_to_dim = np.sqrt((line_center_x - dim_x)**2 + (line_center_y - dim_y)**2)
                
                if dist_to_dim < 50:  # Within 50 pixels
                    # Calculate line length
                    line_length = np.sqrt((line_x1 - line_x0)**2 + (line_y1 - line_y0)**2)
                    
                    if line_length > 10:  # Minimum length
                        # Calculate scale
                        scale = line_length / dim_feet
                        
                        # Sanity check
                        if 10.0 <= scale <= 150.0:
                            verified_scales.append(scale)
                            logger.debug(f"Dimension '{text}' ({dim_feet}ft) measures {line_length:.1f}px -> {scale:.1f} px/ft")
        
        if verified_scales:
            # Use median for robustness
            median_scale = np.median(verified_scales)
            confidence = min(0.95, 0.7 + 0.05 * len(verified_scales))  # More measurements = higher confidence
            logger.info(f"Verified scale from {len(verified_scales)} dimensions: {median_scale:.1f} px/ft")
            return (median_scale, confidence)
        
        return None
    
    def _test_scales_by_room_sizes(self, rectangles: List[Dict[str, Any]], text_elements: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        Test different scales and score them based on resulting room sizes
        """
        # Common scales to test (in pixels per foot)
        # These are the actual pixel values used in typical PDF blueprints
        test_scales = [
            12.0,   # 1"=1' (rare, very large scale)
            24.0,   # 1/2"=1'
            36.0,   # 3/8"=1' or 3/16"=1'
            48.0,   # 1/4"=1' (very common residential)
            64.0,   # 3/16"=1' alternative
            96.0,   # 1/8"=1' (common for large buildings)
        ]
        
        # Extract room type hints from text
        room_types = self._extract_room_types(text_elements)
        
        results = []
        
        for scale in test_scales:
            score = self._score_scale_by_room_sizes(scale, rectangles, room_types)
            if score > 0.3:  # Minimum threshold
                confidence = score * 0.8  # Scale score to confidence
                results.append((scale, confidence))
                logger.debug(f"Scale {scale:.1f} px/ft scored {score:.2f}")
        
        return results
    
    def _score_scale_by_room_sizes(self, scale: float, rectangles: List[Dict[str, Any]], room_types: List[str]) -> float:
        """
        Score a scale based on how well resulting room sizes match expectations
        """
        if not rectangles:
            return 0.0
        
        room_areas = []
        
        for rect in rectangles:
            width = rect.get('width', 0)
            height = rect.get('height', 0)
            
            if width <= 0 or height <= 0:
                continue
            
            # Convert to square feet
            width_ft = width / scale
            height_ft = height / scale
            area_sqft = width_ft * height_ft
            
            room_areas.append(area_sqft)
        
        if not room_areas:
            return 0.0
        
        # Score based on criteria
        score = 0.0
        max_score = 0.0
        
        # Criterion 1: Reasonable room sizes (20-500 sq ft)
        reasonable_rooms = sum(1 for a in room_areas if 20 <= a <= 500)
        score += (reasonable_rooms / len(room_areas)) * 3.0
        max_score += 3.0
        
        # Criterion 2: Total area in typical range
        total_area = sum(room_areas)
        if self.TYPICAL_HOME_RANGE[0] <= total_area <= self.TYPICAL_HOME_RANGE[1]:
            score += 2.0
        elif self.MIN_HOME_SIZE <= total_area <= self.MAX_HOME_SIZE:
            score += 1.0
        max_score += 2.0
        
        # Criterion 3: Room size distribution
        small_rooms = sum(1 for a in room_areas if 10 <= a < 100)
        medium_rooms = sum(1 for a in room_areas if 100 <= a < 300)
        large_rooms = sum(1 for a in room_areas if 300 <= a < 600)
        
        if small_rooms > 0 and medium_rooms > 0:
            score += 1.0  # Good mix
        max_score += 1.0
        
        # Criterion 4: No extreme outliers
        if all(5 <= a <= 1000 for a in room_areas):
            score += 1.0
        max_score += 1.0
        
        return score / max_score if max_score > 0 else 0.0
    
    def _estimate_from_page_size(self, page_width: float, page_height: float) -> Optional[Tuple[float, float]]:
        """
        Estimate scale based on page dimensions and typical architectural sheet sizes
        """
        # Common architectural sheet sizes at 72 DPI
        # Assume the building footprint takes up ~60-80% of the sheet
        
        # Estimate building dimensions
        building_width_estimate = 50.0  # feet (typical residential)
        building_height_estimate = 40.0  # feet
        
        # Calculate what scale would fit this building on the page
        scale_x = page_width * 0.7 / building_width_estimate
        scale_y = page_height * 0.7 / building_height_estimate
        
        # Use the smaller scale (to fit both dimensions)
        estimated_scale = min(scale_x, scale_y)
        
        # Round to nearest common scale
        common_scales = [12, 18, 24, 36, 48, 72, 96]
        nearest_scale = min(common_scales, key=lambda x: abs(x * (self.dpi / 72.0) - estimated_scale))
        
        return (nearest_scale * (self.dpi / 72.0), 0.4)  # Low confidence
    
    def _validate_scale(self, scale: float, rectangles: List[Dict[str, Any]], text_elements: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Validate a scale by checking if it produces reasonable results
        """
        validation = {
            'rooms_reasonable': False,
            'total_area_reasonable': False,
            'has_typical_rooms': False,
            'dimensions_consistent': True
        }
        
        if not rectangles:
            return validation
        
        # Calculate room areas
        room_areas = []
        for rect in rectangles[:50]:  # Limit to first 50 rectangles
            width = rect.get('width', 0) / scale
            height = rect.get('height', 0) / scale
            area = width * height
            
            if 10 <= area <= 1000:  # Reasonable room size
                room_areas.append(area)
        
        if room_areas:
            # Check if most rooms are reasonable
            reasonable = sum(1 for a in room_areas if 20 <= a <= 500)
            validation['rooms_reasonable'] = reasonable >= len(room_areas) * 0.5
            
            # Check total area
            total_area = sum(room_areas)
            validation['total_area_reasonable'] = self.MIN_HOME_SIZE <= total_area <= self.MAX_HOME_SIZE
            
            # Check for typical room sizes
            has_small = any(20 <= a <= 100 for a in room_areas)
            has_medium = any(100 <= a <= 300 for a in room_areas)
            validation['has_typical_rooms'] = has_small and has_medium
        
        return validation
    
    def _extract_room_types(self, text_elements: List[Dict[str, Any]]) -> List[str]:
        """
        Extract room type hints from text elements
        """
        room_keywords = ['bedroom', 'bathroom', 'kitchen', 'living', 'dining', 
                        'closet', 'hallway', 'garage', 'master', 'office',
                        'laundry', 'pantry', 'family', 'bath', 'bed']
        
        room_types = []
        for element in text_elements:
            text = element.get('text', '').lower()
            for keyword in room_keywords:
                if keyword in text:
                    room_types.append(keyword)
                    break
        
        return room_types
    
    def _determine_detection_method(self, scale: float, text_scale, dim_scale) -> str:
        """
        Determine which method was used for the final scale
        """
        if text_scale and abs(scale - text_scale[0]) < 1.0:
            return "text_notation"
        elif dim_scale and abs(scale - dim_scale[0]) < 1.0:
            return "dimension_verification"
        else:
            return "room_size_validation"