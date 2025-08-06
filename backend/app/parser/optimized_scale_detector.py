"""
Optimized scale detection using extract_text() instead of extract_words()
For improved performance with large PDFs
"""

import re
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QuickScaleResult:
    """Result of quick scale detection"""
    scale_factor: float  # pixels per foot
    confidence: float  # 0.0 to 1.0
    detection_method: str


class OptimizedScaleDetector:
    """
    Fast scale detection using text extraction instead of word extraction
    Optimized for performance with large PDFs
    """
    
    # Standard architectural scales mapping
    COMMON_SCALES = {
        "1/16": 192.0,  # 1/16"=1' (very small scale)
        "3/32": 128.0,  # 3/32"=1'
        "1/8": 96.0,    # 1/8"=1' (common for large buildings)
        "3/16": 64.0,   # 3/16"=1'
        "1/4": 48.0,    # 1/4"=1' (MOST COMMON for residential)
        "3/8": 32.0,    # 3/8"=1'
        "1/2": 24.0,    # 1/2"=1'
        "3/4": 18.0,    # 3/4"=1'
        "1": 12.0,      # 1"=1' (very large scale)
    }
    
    def __init__(self, dpi: float = 72.0):
        self.dpi = dpi
        # Adjust scales for actual DPI
        self.adjusted_scales = {
            k: v * (dpi / 72.0) for k, v in self.COMMON_SCALES.items()
        }
    
    def detect_scale_from_text(self, page_text: str) -> Optional[QuickScaleResult]:
        """
        Quick scale detection from page text only
        Much faster than processing individual words
        
        Args:
            page_text: Full text extracted from page using extract_text()
            
        Returns:
            QuickScaleResult if scale found, None otherwise
        """
        if not page_text:
            return None
        
        # Convert to lowercase for matching
        text_lower = page_text.lower()
        
        # Scale notation patterns
        scale_patterns = [
            # Pattern: SCALE: 1/4"=1'-0" or similar
            (r'scale[:\s]*([13])/(\d+)["\s]*=["\s]*1[\'"-]', self._parse_fraction_scale),
            # Pattern: 1/4"=1' without "scale" prefix
            (r'([13])/(\d+)["\s]*=["\s]*1[\'"-]', self._parse_fraction_scale),
            # Pattern: SCALE 1:48 or 1:50 (metric)
            (r'scale[:\s]*1:(\d+)', self._parse_metric_scale),
            (r'1:(\d+)', self._parse_metric_scale),
            # Pattern: SCALE = 1/4 INCH
            (r'scale[:\s]*=?[:\s]*([13])/(\d+)["\s]*inch', self._parse_fraction_scale),
            # Pattern: 1/4 inch = 1 foot
            (r'([13])/(\d+)["\s]*inch[:\s]*=[:\s]*1["\s]*foot', self._parse_fraction_scale),
        ]
        
        best_match = None
        highest_confidence = 0.0
        
        for pattern, parser_func in scale_patterns:
            matches = re.findall(pattern, text_lower)
            
            for match in matches:
                try:
                    scale_factor = parser_func(match)
                    
                    # Sanity check the scale
                    if 10.0 <= scale_factor <= 200.0:
                        # Higher confidence for explicit "scale:" notation
                        confidence = 0.95 if 'scale' in pattern else 0.85
                        
                        if confidence > highest_confidence:
                            highest_confidence = confidence
                            best_match = QuickScaleResult(
                                scale_factor=scale_factor,
                                confidence=confidence,
                                detection_method=f"text_pattern: {pattern[:30]}"
                            )
                            
                            logger.info(f"Found scale notation: {match} -> {scale_factor:.1f} px/ft")
                        
                except Exception as e:
                    logger.debug(f"Failed to parse scale from match {match}: {e}")
                    continue
        
        # If no explicit scale found, look for common scale references
        if not best_match:
            best_match = self._detect_implicit_scale(text_lower)
        
        return best_match
    
    def _parse_fraction_scale(self, match) -> float:
        """Parse fractional scale like 1/4"=1'"""
        if isinstance(match, tuple):
            if len(match) == 2:
                numerator = float(match[0])
                denominator = float(match[1])
            else:
                numerator = 1.0
                denominator = float(match[0])
        else:
            # Single value, assume it's the denominator
            numerator = 1.0
            denominator = float(match)
        
        # Calculate pixels per foot
        # For 1/4"=1', we have 0.25 inches = 1 foot
        # So 1 foot = 0.25 inches on paper
        # At 72 DPI, 0.25 inches = 0.25 * 72 = 18 pixels
        # But typical PDF rendering is at 2x, so 1/4"=1' -> 48 px/ft
        inches_per_foot = numerator / denominator
        base_pixels = inches_per_foot * 72.0  # Base calculation
        
        # Apply typical PDF rendering factor (blueprints are often rendered at higher resolution)
        pdf_factor = 2.667  # Empirically determined for typical blueprints
        scale_factor = base_pixels * pdf_factor * (self.dpi / 72.0)
        
        return scale_factor
    
    def _parse_metric_scale(self, match) -> float:
        """Parse metric scale like 1:50"""
        if isinstance(match, tuple):
            ratio = float(match[0])
        else:
            ratio = float(match)
        
        # 1:50 means 1 unit on paper = 50 units in real life
        # Convert to pixels per foot
        # Assuming metric scale where 1mm on paper = ratio mm in real life
        # 1 foot = 304.8 mm
        # At 72 DPI, 1 inch = 25.4 mm
        mm_per_foot = 304.8
        mm_per_inch = 25.4
        pixels_per_inch = self.dpi
        
        # Calculate pixels per foot
        scale_factor = (pixels_per_inch * mm_per_foot) / (ratio * mm_per_inch)
        
        return scale_factor
    
    def _detect_implicit_scale(self, text: str) -> Optional[QuickScaleResult]:
        """
        Detect scale from implicit references when no explicit notation found
        """
        # Look for common blueprint indicators
        indicators = {
            "quarter inch": ("1/4", 0.7),
            "eighth inch": ("1/8", 0.7),
            "half inch": ("1/2", 0.7),
            "three sixteenth": ("3/16", 0.6),
            "residential": ("1/4", 0.5),  # Residential often uses 1/4"
            "commercial": ("1/8", 0.5),   # Commercial often uses 1/8"
        }
        
        for indicator, (scale_key, confidence) in indicators.items():
            if indicator in text:
                if scale_key in self.adjusted_scales:
                    scale_factor = self.adjusted_scales[scale_key]
                    logger.info(f"Implicit scale detection from '{indicator}' -> {scale_factor:.1f} px/ft")
                    
                    return QuickScaleResult(
                        scale_factor=scale_factor,
                        confidence=confidence,
                        detection_method=f"implicit: {indicator}"
                    )
        
        return None
    
    def get_default_scale(self) -> QuickScaleResult:
        """
        Return default scale when detection fails
        1/4"=1' is most common for residential blueprints
        """
        return QuickScaleResult(
            scale_factor=self.adjusted_scales["1/4"],
            confidence=0.3,
            detection_method="default_fallback"
        )


def extract_scale_quickly(pdf_path: str, page_number: int = 0) -> Optional[QuickScaleResult]:
    """
    Convenience function to quickly extract scale from a PDF page
    Uses extract_text() for performance
    
    Args:
        pdf_path: Path to PDF file
        page_number: Page number to extract from (0-indexed)
        
    Returns:
        QuickScaleResult if scale found, None otherwise
    """
    import pdfplumber
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_number >= len(pdf.pages):
                logger.warning(f"Page {page_number} does not exist in PDF")
                return None
            
            page = pdf.pages[page_number]
            
            # Use extract_text() which is much faster than extract_words()
            page_text = page.extract_text()
            
            if not page_text:
                logger.warning(f"No text found on page {page_number}")
                return None
            
            # Quick scale detection
            detector = OptimizedScaleDetector()
            result = detector.detect_scale_from_text(page_text)
            
            if not result:
                logger.info("No scale found, using default")
                result = detector.get_default_scale()
            
            return result
            
    except Exception as e:
        logger.error(f"Error extracting scale: {e}")
        return None