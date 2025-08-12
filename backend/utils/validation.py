"""
Input validation and type conversion utilities for AutoHVAC
Provides robust type checking and conversion for HVAC calculations
"""

import re
import logging
from typing import Union, Optional, List, Dict, Any, Tuple
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """
    Safely convert value to float with bounds checking
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Float value within specified bounds
    """
    try:
        if isinstance(value, str):
            # Handle common string formats
            value = value.strip().replace(',', '')
            # Handle feet-inch notation like "12'-6""
            if "'" in value or '"' in value:
                value = parse_dimension_string(value)
        
        result = float(value)
        
        # Apply bounds checking
        if min_val is not None and result < min_val:
            logger.warning(f"Value {result} below minimum {min_val}, using minimum")
            result = min_val
        if max_val is not None and result > max_val:
            logger.warning(f"Value {result} above maximum {max_val}, using maximum")
            result = max_val
            
        return result
        
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Could not convert '{value}' to float, using default {default}")
        return default


def safe_int(value: Any, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """
    Safely convert value to int with bounds checking
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Integer value within specified bounds
    """
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '')
        
        result = int(float(value))  # Convert via float to handle "12.0" strings
        
        # Apply bounds checking
        if min_val is not None and result < min_val:
            logger.warning(f"Value {result} below minimum {min_val}, using minimum")
            result = min_val
        if max_val is not None and result > max_val:
            logger.warning(f"Value {result} above maximum {max_val}, using maximum")
            result = max_val
            
        return result
        
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Could not convert '{value}' to int, using default {default}")
        return default


def parse_dimension_string(dim_str: str) -> float:
    """
    Parse dimension strings like "12'-6"", "15'0"", "29 x 12", "14.5'"
    
    Args:
        dim_str: Dimension string to parse
        
    Returns:
        Dimension in feet as float
    """
    if not isinstance(dim_str, str):
        return safe_float(dim_str)
    
    dim_str = dim_str.strip().upper()
    
    # Handle "x" separated dimensions - take the first one
    if ' X ' in dim_str or ' x ' in dim_str.lower():
        parts = re.split(r'\s*[Xx]\s*', dim_str)
        dim_str = parts[0].strip()
    
    # Pattern for feet-inch notation: 12'-6", 12'6", 12'-6, 12'6, 12'
    feet_inch_pattern = r"(\d+(?:\.\d+)?)'\s*-?\s*(\d+(?:\.\d+)?)?\s*\"?"
    match = re.match(feet_inch_pattern, dim_str)
    
    if match:
        feet = safe_float(match.group(1), 0.0)
        inches = safe_float(match.group(2) or "0", 0.0)
        return feet + (inches / 12.0)
    
    # Pattern for decimal feet: 12.5', 12.5ft, 12.5
    decimal_pattern = r"(\d+(?:\.\d+)?)\s*(?:'|ft|feet)?"
    match = re.match(decimal_pattern, dim_str)
    
    if match:
        return safe_float(match.group(1), 0.0)
    
    # Fallback to basic float conversion
    return safe_float(dim_str, 0.0)


def parse_dimensions_tuple(dimensions: Any) -> Tuple[float, float]:
    """
    Parse various dimension formats into (width, length) tuple
    
    Args:
        dimensions: Dimensions in various formats
        
    Returns:
        Tuple of (width, length) in feet
    """
    if isinstance(dimensions, (list, tuple)) and len(dimensions) >= 2:
        return (safe_float(dimensions[0]), safe_float(dimensions[1]))
    
    if isinstance(dimensions, str):
        # Handle "width x length" format
        if ' x ' in dimensions.lower() or ' X ' in dimensions:
            parts = re.split(r'\s*[Xx]\s*', dimensions)
            if len(parts) >= 2:
                width = parse_dimension_string(parts[0])
                length = parse_dimension_string(parts[1])
                return (width, length)
        
        # Handle single dimension - assume square
        dim = parse_dimension_string(dimensions)
        return (dim, dim)
    
    # Fallback for single numeric value
    dim = safe_float(dimensions, 12.0)
    return (dim, dim)


def validate_room_data(room_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize room data for HVAC calculations
    
    Args:
        room_data: Raw room data dictionary
        
    Returns:
        Validated room data dictionary
    """
    validated = {}
    
    # Required string fields
    validated['name'] = str(room_data.get('name', 'Unknown Room')).strip()
    validated['room_type'] = str(room_data.get('room_type', 'other')).lower().strip()
    
    # Dimension handling
    raw_dimensions = room_data.get('dimensions_ft', room_data.get('raw_dimensions', [12.0, 12.0]))
    validated['dimensions_ft'] = parse_dimensions_tuple(raw_dimensions)
    
    # Calculate area from dimensions if not provided
    area = room_data.get('area')
    if area is None or not isinstance(area, (int, float)) or area <= 0:
        width, length = validated['dimensions_ft']
        validated['area'] = width * length
        validated['area_source'] = 'calculated_from_dimensions'
    else:
        validated['area'] = safe_float(area, 144.0, min_val=1.0, max_val=50000.0)
        validated['area_source'] = room_data.get('area_source', 'provided')
        # Mark if this came from GPT-4V to preserve it
        if room_data.get('dimensions_source') == 'gpt4o_vision':
            validated['area_source'] = 'gpt4v_detected'
    
    # Integer fields with bounds
    validated['floor'] = safe_int(room_data.get('floor', 1), 1, min_val=1, max_val=10)
    validated['windows'] = safe_int(room_data.get('windows', 1), 0, min_val=0, max_val=20)
    validated['exterior_doors'] = safe_int(room_data.get('exterior_doors', 0), 0, min_val=0, max_val=5)
    validated['exterior_walls'] = safe_int(room_data.get('exterior_walls', 1), 1, min_val=0, max_val=4)
    
    # Float fields with bounds
    validated['confidence'] = safe_float(room_data.get('confidence', 0.5), 0.5, min_val=0.0, max_val=1.0)
    validated['ceiling_height'] = safe_float(room_data.get('ceiling_height', 9.0), 9.0, min_val=6.0, max_val=20.0)
    
    # Boolean fields
    validated['corner_room'] = bool(room_data.get('corner_room', False))
    validated['label_found'] = bool(room_data.get('label_found', False))
    validated['area_matches_dimensions'] = bool(room_data.get('area_matches_dimensions', True))
    
    # String fields with defaults
    validated['orientation'] = str(room_data.get('orientation', 'unknown')).upper().strip()
    validated['dimension_source'] = str(room_data.get('dimension_source', 'estimated')).lower().strip()
    validated['notes'] = str(room_data.get('notes', '')).strip()
    
    # Validate orientation
    valid_orientations = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'UNKNOWN']
    if validated['orientation'] not in valid_orientations:
        validated['orientation'] = 'UNKNOWN'
    
    # Validate dimension source
    valid_sources = ['measured', 'estimated', 'scaled', 'error', 'gpt4v_fallback']
    if validated['dimension_source'] not in valid_sources:
        validated['dimension_source'] = 'estimated'
    
    # Sanity check: area vs dimensions
    width, length = validated['dimensions_ft']
    calculated_area = width * length
    area_diff = abs(calculated_area - validated['area']) / validated['area']
    
    if area_diff > 0.2:  # More than 20% difference
        logger.warning(f"Room '{validated['name']}': Area mismatch - calculated {calculated_area:.1f} vs provided {validated['area']:.1f} (source: {validated.get('area_source', 'unknown')})")
        validated['area_matches_dimensions'] = False
        
        # PRESERVE GPT-4V AREAS: Only override if NOT from GPT-4V
        if validated.get('area_source') != 'gpt4v_detected':
            # Use calculated area if it seems more reasonable
            if 10 <= calculated_area <= 2000:  # Reasonable room size
                validated['area'] = calculated_area
                logger.info(f"Room '{validated['name']}': Using calculated area {calculated_area:.1f} sqft")
        else:
            logger.info(f"Room '{validated['name']}': Preserving GPT-4V detected area {validated['area']:.1f} sqft (irregular room shape)")
            # Store both for transparency
            validated['calculated_area_sqft'] = calculated_area
    
    return validated


def validate_climate_data(climate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate climate data for HVAC calculations
    
    Args:
        climate_data: Raw climate data dictionary
        
    Returns:
        Validated climate data dictionary
    """
    validated = {}
    
    # Required fields with fallbacks
    validated['zip_code'] = str(climate_data.get('zip_code', '90210')).zfill(5)
    validated['climate_zone'] = str(climate_data.get('climate_zone', '4A')).strip()
    
    # Temperature fields with reasonable bounds
    validated['heating_db_99'] = safe_int(climate_data.get('heating_db_99', 10), 10, min_val=-30, max_val=60)
    validated['cooling_db_1'] = safe_int(climate_data.get('cooling_db_1', 90), 90, min_val=70, max_val=130)
    validated['cooling_wb_1'] = safe_int(climate_data.get('cooling_wb_1', 75), 75, min_val=50, max_val=90)
    
    # Optional location fields
    validated['city'] = str(climate_data.get('city', '')).strip()
    validated['state'] = str(climate_data.get('state', '')).strip()
    validated['state_abbr'] = str(climate_data.get('state_abbr', '')).upper().strip()
    
    # Validate climate zone format
    if not re.match(r'^[1-8][ABC]?$', validated['climate_zone']):
        logger.warning(f"Invalid climate zone '{validated['climate_zone']}', using default '4A'")
        validated['climate_zone'] = '4A'
    
    return validated


def validate_calculation_inputs(
    area: Any, 
    u_factor: Any, 
    temperature_diff: Any,
    component_type: str = "wall"
) -> Tuple[float, float, float]:
    """
    Validate inputs for HVAC load calculations
    
    Args:
        area: Component area in sq ft
        u_factor: U-factor (heat transfer coefficient)
        temperature_diff: Temperature difference
        component_type: Type of component for validation bounds
        
    Returns:
        Tuple of validated (area, u_factor, temperature_diff)
    """
    # Validate area based on component type
    if component_type.lower() in ['wall', 'roof', 'floor']:
        min_area, max_area = 1.0, 10000.0
    elif component_type.lower() in ['window', 'door']:
        min_area, max_area = 0.1, 500.0
    else:
        min_area, max_area = 0.1, 50000.0
    
    validated_area = safe_float(area, 100.0, min_val=min_area, max_val=max_area)
    
    # Validate U-factor (typical range for building components)
    validated_u_factor = safe_float(u_factor, 0.5, min_val=0.01, max_val=5.0)
    
    # Validate temperature difference
    validated_temp_diff = safe_float(temperature_diff, 20.0, min_val=-50.0, max_val=100.0)
    
    return validated_area, validated_u_factor, validated_temp_diff


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unknown_file.pdf"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure reasonable length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:90] + '.' + ext if ext else name[:100]
    
    return filename


def validate_zip_code(zip_code: Any) -> str:
    """
    Validate and format US zip code
    
    Args:
        zip_code: Zip code in various formats
        
    Returns:
        5-digit zip code string
    """
    if not zip_code:
        return "90210"  # Default fallback
    
    zip_str = str(zip_code).strip()
    
    # Extract digits only
    digits = re.sub(r'\D', '', zip_str)
    
    if len(digits) >= 5:
        return digits[:5]
    elif len(digits) > 0:
        return digits.zfill(5)
    else:
        return "90210"  # Fallback for invalid input