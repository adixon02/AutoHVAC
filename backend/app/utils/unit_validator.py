"""
Unit validation utilities for ensuring correct measurement units throughout the system.

This module provides validation and correction for room areas and dimensions to catch
and fix unit conversion errors early in the processing pipeline.
"""

import logging
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)

# Room area bounds in square feet
MIN_ROOM_AREA_SQFT = 10.0  # Minimum for tiny closets
MAX_ROOM_AREA_SQFT = 5000.0  # Maximum for large commercial spaces
TYPICAL_MIN_RESIDENTIAL = 15.0  # Typical minimum for residential rooms
TYPICAL_MAX_RESIDENTIAL = 1000.0  # Typical maximum for residential rooms

# Common scale factors (pixels per foot)
COMMON_SCALE_FACTORS = [48.0, 96.0, 24.0, 12.0]  # 1/4"=1', 1/8"=1', 1/2"=1', 1"=1'


def validate_room_area(
    area: float, 
    room_name: str, 
    scale_factor: Optional[float] = None,
    auto_correct: bool = True
) -> Tuple[float, List[str]]:
    """
    Validate and potentially correct room areas.
    
    Args:
        area: The area value to validate
        room_name: Name of the room for logging
        scale_factor: Scale factor if known (pixels/foot)
        auto_correct: Whether to attempt automatic correction
    
    Returns:
        Tuple of (corrected_area, list_of_warnings)
    """
    warnings = []
    corrected_area = area
    
    # Check if area is suspiciously small (likely in wrong units)
    if area < 1.0:
        warnings.append(
            f"Room '{room_name}' area {area:.2f} sqft is impossibly small - likely unit error"
        )
        
        if auto_correct and scale_factor:
            # Try to correct assuming the area was given in feet instead of sqft
            potential_correction = area * (scale_factor ** 2)
            if MIN_ROOM_AREA_SQFT <= potential_correction <= MAX_ROOM_AREA_SQFT:
                corrected_area = potential_correction
                warnings.append(
                    f"Auto-corrected '{room_name}' from {area:.2f} to {corrected_area:.2f} sqft"
                )
        elif auto_correct:
            # Try common scale factor corrections
            for test_scale in COMMON_SCALE_FACTORS:
                potential_correction = area * (test_scale ** 2)
                if TYPICAL_MIN_RESIDENTIAL <= potential_correction <= TYPICAL_MAX_RESIDENTIAL:
                    corrected_area = potential_correction
                    warnings.append(
                        f"Auto-corrected '{room_name}' from {area:.2f} to {corrected_area:.2f} sqft (assumed scale {test_scale})"
                    )
                    break
    
    # Check if area is within reasonable bounds
    elif area < MIN_ROOM_AREA_SQFT:
        warnings.append(
            f"Room '{room_name}' area {area:.2f} sqft is below minimum ({MIN_ROOM_AREA_SQFT} sqft)"
        )
    elif area > MAX_ROOM_AREA_SQFT:
        warnings.append(
            f"Room '{room_name}' area {area:.2f} sqft exceeds maximum ({MAX_ROOM_AREA_SQFT} sqft)"
        )
    
    # Check against typical residential bounds
    if TYPICAL_MIN_RESIDENTIAL <= area <= TYPICAL_MAX_RESIDENTIAL:
        # Area is in typical range, likely correct
        pass
    elif area > TYPICAL_MAX_RESIDENTIAL and area <= MAX_ROOM_AREA_SQFT:
        warnings.append(
            f"Room '{room_name}' area {area:.2f} sqft is unusually large for residential"
        )
    
    # Log all warnings
    for warning in warnings:
        logger.warning(warning)
    
    return corrected_area, warnings


def validate_dimensions(
    width: float,
    height: float,
    room_name: str,
    scale_factor: Optional[float] = None,
    auto_correct: bool = True
) -> Tuple[Tuple[float, float], List[str]]:
    """
    Validate and potentially correct room dimensions.
    
    Args:
        width: Width value to validate
        height: Height value to validate
        room_name: Name of the room for logging
        scale_factor: Scale factor if known (pixels/foot)
        auto_correct: Whether to attempt automatic correction
    
    Returns:
        Tuple of ((corrected_width, corrected_height), list_of_warnings)
    """
    warnings = []
    corrected_width = width
    corrected_height = height
    
    # Check if dimensions are suspiciously small (likely in wrong units)
    if width < 1.0 or height < 1.0:
        warnings.append(
            f"Room '{room_name}' dimensions {width:.2f}x{height:.2f} ft are impossibly small"
        )
        
        if auto_correct and scale_factor:
            # Try to correct assuming dimensions were in page units
            potential_width = width / scale_factor if width < 1.0 else width
            potential_height = height / scale_factor if height < 1.0 else height
            
            if 3.0 <= potential_width <= 100.0 and 3.0 <= potential_height <= 100.0:
                corrected_width = potential_width
                corrected_height = potential_height
                warnings.append(
                    f"Auto-corrected '{room_name}' dimensions from {width:.2f}x{height:.2f} to {corrected_width:.2f}x{corrected_height:.2f} ft"
                )
    
    # Check minimum room dimensions (3 feet minimum for any dimension)
    if corrected_width < 3.0:
        warnings.append(f"Room '{room_name}' width {corrected_width:.2f} ft is below minimum (3 ft)")
    if corrected_height < 3.0:
        warnings.append(f"Room '{room_name}' height {corrected_height:.2f} ft is below minimum (3 ft)")
    
    # Check maximum room dimensions
    if corrected_width > 100.0:
        warnings.append(f"Room '{room_name}' width {corrected_width:.2f} ft exceeds typical maximum")
    if corrected_height > 100.0:
        warnings.append(f"Room '{room_name}' height {corrected_height:.2f} ft exceeds typical maximum")
    
    # Log warnings
    for warning in warnings:
        logger.warning(warning)
    
    return (corrected_width, corrected_height), warnings


def validate_scale_factor(scale_factor: Optional[float]) -> Tuple[float, List[str]]:
    """
    Validate scale factor is reasonable.
    
    Args:
        scale_factor: Scale factor to validate (pixels per foot)
    
    Returns:
        Tuple of (validated_scale_factor, list_of_warnings)
    """
    warnings = []
    
    if scale_factor is None or scale_factor <= 0:
        warnings.append("No valid scale factor provided, using default 48 px/ft (1/4\" = 1')")
        return 48.0, warnings
    
    # Check if scale factor is in reasonable range
    if scale_factor < 6.0:
        warnings.append(f"Scale factor {scale_factor} px/ft is unusually low")
    elif scale_factor > 200.0:
        warnings.append(f"Scale factor {scale_factor} px/ft is unusually high")
    
    # Check if it matches common scales
    if scale_factor not in COMMON_SCALE_FACTORS:
        closest = min(COMMON_SCALE_FACTORS, key=lambda x: abs(x - scale_factor))
        if abs(scale_factor - closest) < 5.0:
            warnings.append(
                f"Scale factor {scale_factor} px/ft is close to common scale {closest} px/ft"
            )
    
    return scale_factor, warnings