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
        logger.info("Starting multi-hypothesis scale detection")
        
        all_hypotheses = []
        
        # Method 1: Direct text notation detection
        text_scale = self._detect_from_text_notation(text_elements)
        if text_scale:
            all_hypotheses.append(text_scale)
            logger.info(f"Text notation hypothesis: {text_scale[0]:.1f} px/ft (confidence: {text_scale[1]:.2f})")
        
        # Method 2: Dimension measurement verification
        dim_scale = None
        if dimensions:
            dim_scale = self._verify_from_dimensions(dimensions, lines)
            if dim_scale:
                all_hypotheses.append(dim_scale)
                logger.info(f"Dimension verification hypothesis: {dim_scale[0]:.1f} px/ft (confidence: {dim_scale[1]:.2f})")
        
        # Method 3: ALWAYS test common scales with room size validation
        # This helps catch incorrect text notation (like 3/16" vs 1/4")
        validated_scales = self._test_all_scales_thoroughly(rectangles, lines, text_elements)
        all_hypotheses.extend(validated_scales)
        if validated_scales:
            logger.info(f"Room validation found {len(validated_scales)} hypotheses")
        
        # Method 4: Page size heuristics (low confidence fallback)
        page_scale = self._estimate_from_page_size(page_width, page_height)
        if page_scale:
            all_hypotheses.append(page_scale)
            logger.info(f"Page size hypothesis: {page_scale[0]:.1f} px/ft (confidence: {page_scale[1]:.2f})")
        
        # Select best hypothesis through validation
        if all_hypotheses:
            # Test each hypothesis thoroughly
            validated_results = []
            for scale, initial_conf in all_hypotheses:
                validation = self._validate_scale_thoroughly(scale, rectangles, lines, text_elements)
                
                # Calculate final confidence based on validation
                final_confidence = self._calculate_final_confidence(
                    initial_conf, validation, scale, rectangles
                )
                
                validated_results.append((scale, final_confidence, validation))
                logger.debug(f"Scale {scale:.1f} px/ft: initial conf={initial_conf:.2f}, final conf={final_confidence:.2f}")
            
            # Sort by final confidence
            validated_results.sort(key=lambda x: x[1], reverse=True)
            best_scale, best_confidence, best_validation = validated_results[0]
            
            # Check if confidence is high enough
            if best_confidence < 0.6:
                logger.warning(f"Best scale confidence ({best_confidence:.2f}) below threshold")
                # Try to improve by testing intermediate scales
                improved = self._try_intermediate_scales(best_scale, rectangles, lines)
                if improved and improved[1] > best_confidence:
                    best_scale, best_confidence = improved
                    best_validation = self._validate_scale_thoroughly(best_scale, rectangles, lines, text_elements)
            
            method = self._determine_detection_method(best_scale, text_scale, dim_scale)
            
            return ScaleResult(
                scale_factor=best_scale,
                confidence=best_confidence,
                detection_method=method,
                validation_results=best_validation,
                alternative_scales=[(s, c) for s, c, _ in validated_results[:3]]  # Top 3 alternatives
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
    
    def _test_all_scales_thoroughly(self, rectangles: List[Dict[str, Any]], lines: List[Dict[str, Any]], text_elements: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        Test all common scales thoroughly with multiple validation methods
        """
        # Comprehensive list of scales to test
        test_scales = [
            12.0,   # 1"=1' (rare, very large scale)
            18.0,   # 3/4"=1'
            24.0,   # 1/2"=1'
            32.0,   # 3/8"=1'
            36.0,   # Alternative 3/8"=1' 
            48.0,   # 1/4"=1' (MOST COMMON residential)
            64.0,   # 3/16"=1' 
            72.0,   # Alternative scale
            96.0,   # 1/8"=1' (common for large buildings)
            128.0,  # 3/32"=1' (very large buildings)
        ]
        
        # Extract room type hints from text
        room_types = self._extract_room_types(text_elements)
        
        results = []
        best_score = 0.0
        
        for scale in test_scales:
            # Score by multiple criteria
            rect_score = self._score_scale_by_room_sizes(scale, rectangles, room_types)
            line_score = self._score_scale_by_wall_patterns(scale, lines) if lines else 0.0
            text_score = self._score_scale_by_text_labels(scale, text_elements, rectangles) if text_elements else 0.0
            
            # Combined score with weights
            combined_score = (rect_score * 0.5 + line_score * 0.3 + text_score * 0.2)
            
            if combined_score > 0.25:  # Lower threshold to catch more candidates
                confidence = min(0.95, combined_score)
                results.append((scale, confidence))
                logger.debug(f"Scale {scale:.1f} px/ft: rect={rect_score:.2f}, line={line_score:.2f}, text={text_score:.2f}, combined={combined_score:.2f}")
                
                if combined_score > best_score:
                    best_score = combined_score
        
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
    
    def _validate_scale_thoroughly(
        self, 
        scale: float, 
        rectangles: List[Dict[str, Any]], 
        lines: List[Dict[str, Any]],
        text_elements: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Thoroughly validate a scale hypothesis using multiple criteria
        """
        validation = {
            'rooms_reasonable': False,
            'total_area_reasonable': False,
            'has_typical_rooms': False,
            'dimensions_consistent': True,
            'wall_patterns_valid': True,
            'room_count_reasonable': False
        }
        
        if not rectangles:
            return validation
        
        # Calculate room areas with this scale
        room_areas = []
        for rect in rectangles[:100]:  # Limit for performance
            width = rect.get('width', 0) / scale
            height = rect.get('height', 0) / scale
            area = width * height
            
            if 5 <= area <= 2000:  # Very broad range for initial filtering
                room_areas.append(area)
        
        if room_areas:
            # Check room size distribution
            reasonable = sum(1 for a in room_areas if 15 <= a <= 600)
            validation['rooms_reasonable'] = reasonable >= len(room_areas) * 0.4  # More lenient
            
            # Check total area
            total_area = sum(room_areas)
            validation['total_area_reasonable'] = 400 <= total_area <= 15000  # Wider range
            
            # Check for typical room size distribution
            small = sum(1 for a in room_areas if 15 <= a < 100)
            medium = sum(1 for a in room_areas if 100 <= a < 400)
            large = sum(1 for a in room_areas if 400 <= a < 1000)
            validation['has_typical_rooms'] = (small > 0 or medium > 0) and total_area > 500
            
            # Check room count
            validation['room_count_reasonable'] = 3 <= len(room_areas) <= 50
        
        return validation
    
    def _calculate_final_confidence(
        self,
        initial_confidence: float,
        validation: Dict[str, bool],
        scale: float,
        rectangles: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate final confidence score based on validation results
        """
        # Start with initial confidence
        confidence = initial_confidence
        
        # Adjust based on validation
        validation_score = sum(1 for v in validation.values() if v) / len(validation)
        
        # Weight validation heavily
        confidence = confidence * 0.4 + validation_score * 0.6
        
        # Bonus for common residential scales
        if 45 <= scale <= 50:  # 1/4" scale range
            confidence *= 1.1
        elif 94 <= scale <= 98:  # 1/8" scale range
            confidence *= 1.05
        
        # Penalty for extreme scales
        if scale < 15 or scale > 150:
            confidence *= 0.8
        
        return min(0.95, confidence)
    
    def _try_intermediate_scales(
        self,
        base_scale: float,
        rectangles: List[Dict[str, Any]],
        lines: List[Dict[str, Any]]
    ) -> Optional[Tuple[float, float]]:
        """
        Try scales near the base scale to find better fit
        """
        best_result = None
        best_score = 0.0
        
        # Test scales within 20% of base
        test_range = [
            base_scale * 0.8,
            base_scale * 0.9,
            base_scale * 1.1,
            base_scale * 1.2
        ]
        
        room_types = []  # Could extract if needed
        
        for scale in test_range:
            score = self._score_scale_by_room_sizes(scale, rectangles, room_types)
            if score > best_score:
                best_score = score
                best_result = (scale, score * 0.7)  # Lower confidence for interpolated
        
        return best_result
    
    def _score_scale_by_wall_patterns(self, scale: float, lines: List[Dict[str, Any]]) -> float:
        """
        Score scale based on wall line patterns and spacing
        """
        if not lines or len(lines) < 10:
            return 0.5  # Neutral score if insufficient data
        
        # Analyze wall spacing patterns
        wall_lengths = []
        for line in lines[:500]:  # Limit for performance
            length = line.get('length', 0)
            if length > 0:
                length_ft = length / scale
                # Typical wall lengths are 4-30 feet
                if 2 <= length_ft <= 40:
                    wall_lengths.append(length_ft)
        
        if not wall_lengths:
            return 0.3
        
        # Score based on reasonable wall lengths
        reasonable = sum(1 for l in wall_lengths if 4 <= l <= 30)
        score = reasonable / len(wall_lengths) if wall_lengths else 0.0
        
        # Check for common modular dimensions (4, 8, 12, 16 feet)
        modular = sum(1 for l in wall_lengths if any(
            abs(l - m) < 0.5 for m in [4, 8, 10, 12, 14, 16, 20, 24]
        ))
        if modular > len(wall_lengths) * 0.2:
            score += 0.2
        
        return min(1.0, score)
    
    def _score_scale_by_text_labels(
        self,
        scale: float,
        text_elements: List[Dict[str, Any]],
        rectangles: List[Dict[str, Any]]
    ) -> float:
        """
        Score scale by checking if text labels align with room sizes
        """
        if not text_elements or not rectangles:
            return 0.5
        
        # Extract room labels with expected sizes
        room_expectations = {
            'bedroom': (80, 300),
            'master': (120, 400),
            'bathroom': (20, 120),
            'kitchen': (70, 300),
            'living': (150, 500),
            'dining': (100, 300),
            'closet': (10, 80),
            'garage': (200, 800)
        }
        
        matches = 0
        checks = 0
        
        for text_elem in text_elements:
            text = text_elem.get('text', '').lower()
            for room_type, (min_size, max_size) in room_expectations.items():
                if room_type in text:
                    checks += 1
                    # Find nearest rectangle
                    text_x = text_elem.get('x0', 0)
                    text_y = text_elem.get('top', 0)
                    
                    for rect in rectangles:
                        rect_x = (rect.get('x0', 0) + rect.get('x1', 0)) / 2
                        rect_y = (rect.get('y0', 0) + rect.get('y1', 0)) / 2
                        
                        # Check if text is near this rectangle
                        dist = ((text_x - rect_x)**2 + (text_y - rect_y)**2)**0.5
                        if dist < 100:  # Within 100 pixels
                            area = (rect.get('width', 0) / scale) * (rect.get('height', 0) / scale)
                            if min_size <= area <= max_size:
                                matches += 1
                            break
                    break
        
        if checks == 0:
            return 0.5
        
        return matches / checks if checks > 0 else 0.5