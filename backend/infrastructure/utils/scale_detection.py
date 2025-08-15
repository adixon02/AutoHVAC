"""
Scale Detection Utilities
Detects scale from blueprint text and images
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScaleResult:
    scale_found: bool
    scale_px_per_ft: float
    scale_text: str
    confidence: float
    method: str  # "text", "ruler", "dimension"


def detect_scale_from_pdf(
    text_blocks: List[Dict[str, Any]],
    image: Optional[Any] = None
) -> ScaleResult:
    """
    Detect scale from PDF text and optionally image.
    
    Args:
        text_blocks: Extracted text blocks from PDF
        image: Optional image for visual scale detection
        
    Returns:
        ScaleResult with detected scale information
    """
    
    # Common scale patterns
    scale_patterns = [
        r"SCALE[:\s]+1[/:\"'\s]+(\d+)",  # SCALE: 1:48
        r"(\d+)[\"']\s*=\s*1['\"]",  # 1/4" = 1'
        r"1/(\d+)[\"']\s*=\s*1['\"]",  # 1/4" = 1'
        r"SCALE.*?(\d+)\s*FT",  # SCALE 50 FT
    ]
    
    for block in text_blocks:
        text = block.get('text', '').upper()
        
        for pattern in scale_patterns:
            match = re.search(pattern, text)
            if match:
                scale_value = float(match.group(1))
                
                # Convert to pixels per foot (assuming standard DPI)
                # This is simplified - real implementation would measure
                px_per_ft = 72 / scale_value  # Assuming 72 DPI
                
                logger.info(f"Found scale in text: {text}, px/ft: {px_per_ft}")
                
                return ScaleResult(
                    scale_found=True,
                    scale_px_per_ft=px_per_ft,
                    scale_text=text,
                    confidence=0.8,
                    method="text"
                )
    
    # Default if no scale found
    logger.warning("No scale detected, using default")
    return ScaleResult(
        scale_found=False,
        scale_px_per_ft=1.5,  # Default assumption
        scale_text="",
        confidence=0.3,
        method="default"
    )