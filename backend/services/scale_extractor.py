"""
Simple OCR-based scale extraction for architectural blueprints
Replaces complex 500+ line scale detector with focused approach
"""

import re
import logging
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScaleResult:
    """Scale detection result with confidence"""
    pixels_per_foot: float
    scale_notation: str  # e.g., "1/4\"=1'"
    confidence: float
    source: str  # "ocr", "dimension", "default"
    page_num: int


class ScaleExtractor:
    """
    Lean scale extraction using OCR and validation
    Focus: Find the right scale from the right page
    """
    
    # Common architectural scales: notation -> pixels per foot
    # Based on typical PDF rendering at ~100 DPI effective resolution
    SCALE_MAP = {
        "1\"=1'": 12.0,      # 1 inch = 1 foot (rare, very detailed)
        "3/4\"=1'": 18.0,    # 3/4 inch = 1 foot
        "1/2\"=1'": 24.0,    # 1/2 inch = 1 foot
        "3/8\"=1'": 32.0,    # 3/8 inch = 1 foot
        "1/4\"=1'": 48.0,    # 1/4 inch = 1 foot (MOST COMMON)
        "3/16\"=1'": 64.0,   # 3/16 inch = 1 foot
        "1/8\"=1'": 96.0,    # 1/8 inch = 1 foot (large buildings)
        "3/32\"=1'": 128.0,  # 3/32 inch = 1 foot
        "1/16\"=1'": 192.0,  # 1/16 inch = 1 foot (site plans)
    }
    
    def extract_scale(
        self,
        ocr_text: str,
        page_num: int = 0,
        sample_rooms: Optional[List[Dict]] = None,
        dimension_strings: Optional[List[str]] = None,
        polygon_edges: Optional[List[float]] = None
    ) -> ScaleResult:
        """
        Extract scale from OCR text with validation
        
        Args:
            ocr_text: OCR extracted text from the page
            page_num: Page number (0-indexed)
            sample_rooms: Optional room rectangles for validation
            dimension_strings: Optional list of dimension strings for least-squares fitting
            polygon_edges: Optional list of polygon edge lengths in pixels
            
        Returns:
            ScaleResult with detected scale and confidence
        """
        # Try least-squares fitting if dimension strings provided
        if dimension_strings and polygon_edges and len(dimension_strings) >= 3:
            try:
                scale = self.extract_scale_least_squares(dimension_strings, polygon_edges, page_num)
                if scale and scale.confidence > 0.95:
                    logger.info(f"Scale detected via least-squares: {scale.pixels_per_foot:.1f} px/ft, confidence: {scale.confidence:.3f}")
                    return scale
            except Exception as e:
                logger.warning(f"Least-squares scale detection failed: {e}")
        
        # Try OCR-based detection
        scale = self._extract_from_ocr(ocr_text, page_num)
        
        if scale and scale.confidence > 0.7:
            # Validate with sample rooms if provided
            if sample_rooms:
                validated = self._validate_with_rooms(scale.pixels_per_foot, sample_rooms)
                if not validated:
                    logger.warning(f"Scale {scale.scale_notation} failed room validation")
                    scale.confidence *= 0.5
            
            return scale
        
        # Fallback to default with low confidence
        logger.warning("No scale detected from OCR, using default 1/4\"=1'")
        return ScaleResult(
            pixels_per_foot=48.0,
            scale_notation="1/4\"=1'",
            confidence=0.3,
            source="default",
            page_num=page_num
        )
    
    def _extract_from_ocr(self, text: str, page_num: int) -> Optional[ScaleResult]:
        """Extract scale notation from OCR text"""
        if not text:
            return None
        
        # Clean and normalize text
        text = text.upper()
        
        # Pattern variations for scale notation
        patterns = [
            # Standard format: SCALE: 1/4"=1'-0"
            (r'SCALE[:\s]+1/(\d+)["\']\s*=\s*1[\'"\-]', lambda m: f"1/{m.group(1)}\"=1'"),
            # Fraction format: SCALE: 3/16"=1'
            (r'SCALE[:\s]+(\d+)/(\d+)["\']\s*=\s*1[\'"\-]', lambda m: f"{m.group(1)}/{m.group(2)}\"=1'"),
            # Simple format: 1/4"=1'
            (r'(?:^|\s)1/(\d+)["\']\s*=\s*1[\'"\-]', lambda m: f"1/{m.group(1)}\"=1'"),
            # With spacing: 1/4 " = 1 '
            (r'(?:^|\s)1/(\d+)\s*["\']\s*=\s*1\s*[\'"\-]', lambda m: f"1/{m.group(1)}\"=1'"),
            # Metric format: 1:48
            (r'(?:SCALE[:\s]+)?1:(\d+)', lambda m: self._metric_to_imperial(int(m.group(1)))),
        ]
        
        best_match = None
        best_confidence = 0.0
        
        for pattern, formatter in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    notation = formatter(match)
                    if notation in self.SCALE_MAP:
                        # Higher confidence if "SCALE" keyword is present
                        confidence = 0.9 if "SCALE" in match.group() else 0.8
                        
                        if confidence > best_confidence:
                            best_match = notation
                            best_confidence = confidence
                            
                            logger.info(f"Found scale notation: {notation} (confidence: {confidence})")
                        
                except Exception as e:
                    logger.debug(f"Failed to parse scale match: {e}")
        
        if best_match:
            return ScaleResult(
                pixels_per_foot=self.SCALE_MAP[best_match],
                scale_notation=best_match,
                confidence=best_confidence,
                source="ocr",
                page_num=page_num
            )
        
        return None
    
    def extract_scale_least_squares(
        self,
        dimension_strings: List[str],
        edge_lengths_px: List[float],
        page_num: int = 0
    ) -> Optional[ScaleResult]:
        """
        Fit scale using multiple dimensions via least-squares regression
        
        Args:
            dimension_strings: List of dimension strings (e.g., "21'-6\"")
            edge_lengths_px: Corresponding edge lengths in pixels
            page_num: Page number
            
        Returns:
            ScaleResult with high confidence if variance < 5%
        """
        # Parse dimension strings to feet
        parsed_dims_ft = []
        for dim_str in dimension_strings:
            try:
                feet_value = self._parse_dimension_to_feet(dim_str)
                if feet_value and feet_value > 0:
                    parsed_dims_ft.append(feet_value)
            except Exception as e:
                logger.debug(f"Failed to parse dimension '{dim_str}': {e}")
        
        if len(parsed_dims_ft) < 3:
            logger.warning(f"Insufficient valid dimensions for least-squares: {len(parsed_dims_ft)}")
            return None
        
        # Match dimensions to edges (simplified - assumes same order)
        min_pairs = min(len(parsed_dims_ft), len(edge_lengths_px))
        if min_pairs < 3:
            return None
        
        dims_array = np.array(parsed_dims_ft[:min_pairs])
        edges_array = np.array(edge_lengths_px[:min_pairs])
        
        # Remove outliers using IQR method
        ratios = edges_array / dims_array
        q1, q3 = np.percentile(ratios, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        mask = (ratios >= lower_bound) & (ratios <= upper_bound)
        clean_dims = dims_array[mask]
        clean_edges = edges_array[mask]
        
        if len(clean_dims) < 3:
            logger.warning("Too many outliers removed in scale detection")
            return None
        
        # Least-squares fit: edges = scale * dims
        # Using numpy's least squares: minimize ||Ax - b||^2
        A = clean_dims.reshape(-1, 1)
        b = clean_edges
        
        scale_matrix, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
        scale_px_per_ft = float(scale_matrix[0])
        
        # Calculate confidence based on residual variance
        if len(residuals) > 0:
            rmse = np.sqrt(residuals[0] / len(clean_dims))
            mean_edge = np.mean(clean_edges)
            variance_pct = (rmse / mean_edge) if mean_edge > 0 else 1.0
            confidence = max(0, 1.0 - variance_pct)
        else:
            confidence = 0.5
        
        logger.info(f"Least-squares scale: {scale_px_per_ft:.1f} px/ft from {len(clean_dims)} dimensions")
        logger.info(f"Variance: {variance_pct*100:.1f}%, Confidence: {confidence:.3f}")
        
        # FAIL if variance > 5%
        if variance_pct > 0.05:
            raise ValueError(f"Scale variance {variance_pct*100:.1f}% exceeds 5% threshold")
        
        # Determine closest standard scale
        best_notation = "1/4\"=1'"
        best_diff = float('inf')
        for notation, standard_scale in self.SCALE_MAP.items():
            diff = abs(scale_px_per_ft - standard_scale)
            if diff < best_diff:
                best_diff = diff
                best_notation = notation
        
        return ScaleResult(
            pixels_per_foot=scale_px_per_ft,
            scale_notation=best_notation,
            confidence=confidence,
            source="least_squares",
            page_num=page_num
        )
    
    def _parse_dimension_to_feet(self, dim_str: str) -> Optional[float]:
        """Parse dimension string to feet value"""
        # Pattern: 21'-6" or 21'6" or 21.5'
        patterns = [
            r"(\d+)'[\s-]*(\d+)\"",  # 21'-6" or 21'6"
            r"(\d+\.?\d*)'",          # 21.5' or 21'
            r"(\d+)\.(\d+)",          # 21.5 (decimal feet)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, dim_str)
            if match:
                if len(match.groups()) == 2:
                    # Feet and inches
                    feet = float(match.group(1))
                    inches = float(match.group(2))
                    return feet + inches / 12
                elif len(match.groups()) == 1:
                    # Just feet
                    return float(match.group(1))
        
        return None
    
    def _metric_to_imperial(self, ratio: int) -> str:
        """Convert metric scale ratio to imperial notation"""
        # Common metric to imperial conversions
        metric_map = {
            48: "1/4\"=1'",   # 1:48 = 1/4"=1'
            96: "1/8\"=1'",   # 1:96 = 1/8"=1'
            24: "1/2\"=1'",   # 1:24 = 1/2"=1'
            50: "1/4\"=1'",   # 1:50 ≈ 1/4"=1'
            100: "1/8\"=1'",  # 1:100 ≈ 1/8"=1'
        }
        
        # Find closest match
        if ratio in metric_map:
            return metric_map[ratio]
        
        # Approximate for other ratios
        if ratio < 30:
            return "1/2\"=1'"
        elif ratio < 60:
            return "1/4\"=1'"
        elif ratio < 120:
            return "1/8\"=1'"
        else:
            return "1/16\"=1'"
    
    def _validate_with_rooms(
        self,
        pixels_per_foot: float,
        sample_rooms: List[Dict]
    ) -> bool:
        """
        Validate scale by checking if it produces reasonable room sizes
        
        Args:
            pixels_per_foot: Scale to validate
            sample_rooms: List of room rectangles with width/height in pixels
            
        Returns:
            True if scale produces reasonable room sizes
        """
        if not sample_rooms:
            return True  # Can't validate without rooms
        
        room_areas = []
        for room in sample_rooms[:10]:  # Check first 10 rooms
            width_px = room.get('width', 0)
            height_px = room.get('height', 0)
            
            if width_px > 0 and height_px > 0:
                width_ft = width_px / pixels_per_foot
                height_ft = height_px / pixels_per_foot
                area_sqft = width_ft * height_ft
                room_areas.append(area_sqft)
        
        if not room_areas:
            return True  # Can't validate
        
        # Check if most rooms are in reasonable range (20-600 sq ft)
        reasonable = sum(1 for a in room_areas if 20 <= a <= 600)
        ratio = reasonable / len(room_areas)
        
        # Also check total area is reasonable (500-10000 sq ft)
        total_area = sum(room_areas)
        total_reasonable = 500 <= total_area <= 10000
        
        logger.debug(f"Scale validation: {reasonable}/{len(room_areas)} rooms reasonable, "
                    f"total area: {total_area:.0f} sq ft")
        
        return ratio >= 0.5 and total_reasonable
    
    def find_scale_in_multiple_pages(
        self,
        pages_ocr: List[Tuple[int, str]],
        sample_rooms_per_page: Optional[Dict[int, List[Dict]]] = None
    ) -> ScaleResult:
        """
        Find scale from multiple pages, prioritizing floor plan pages
        
        Args:
            pages_ocr: List of (page_num, ocr_text) tuples
            sample_rooms_per_page: Optional rooms per page for validation
            
        Returns:
            Best scale found across all pages
        """
        best_scale = None
        
        for page_num, ocr_text in pages_ocr:
            # Check if this is likely a floor plan page
            is_floor_plan = self._is_floor_plan_page(ocr_text)
            
            # Extract scale
            sample_rooms = sample_rooms_per_page.get(page_num) if sample_rooms_per_page else None
            scale = self.extract_scale(ocr_text, page_num, sample_rooms)
            
            # Boost confidence for floor plan pages
            if is_floor_plan and scale.source == "ocr":
                scale.confidence = min(0.95, scale.confidence * 1.2)
                logger.info(f"Page {page_num} is floor plan, boosted confidence to {scale.confidence}")
            
            # Keep best scale
            if not best_scale or scale.confidence > best_scale.confidence:
                best_scale = scale
        
        return best_scale or ScaleResult(
            pixels_per_foot=48.0,
            scale_notation="1/4\"=1'",
            confidence=0.3,
            source="default",
            page_num=0
        )
    
    def _is_floor_plan_page(self, text: str) -> bool:
        """Check if page is likely a floor plan based on text"""
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Strong indicators
        floor_plan_keywords = [
            "FLOOR PLAN",
            "FIRST FLOOR",
            "SECOND FLOOR",
            "GROUND FLOOR",
            "LEVEL 1",
            "LEVEL 2"
        ]
        
        for keyword in floor_plan_keywords:
            if keyword in text_upper:
                return True
        
        # Weak indicators (need multiple)
        weak_indicators = [
            "BEDROOM", "BATHROOM", "KITCHEN", "LIVING",
            "DINING", "CLOSET", "GARAGE", "ENTRY"
        ]
        
        indicator_count = sum(1 for ind in weak_indicators if ind in text_upper)
        return indicator_count >= 3


# Global instance
scale_extractor = ScaleExtractor()