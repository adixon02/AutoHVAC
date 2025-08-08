"""
Integration module for new deterministic scale detection and room filtering
This will be integrated into blueprint_parser.py
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from app.parser.schema import Room, ParsingMetadata
from services.deterministic_scale_detector import deterministic_scale_detector
from services.room_filter import room_filter, RoomFilterConfig
from services.error_types import NeedsInputError

logger = logging.getLogger(__name__)


def detect_and_validate_scale(
    ocr_text: str,
    dimensions: List[Dict[str, Any]],
    geometric_elements: List[Dict[str, Any]],
    page_size: Tuple[float, float],
    page_context,
    metadata: ParsingMetadata
) -> float:
    """
    Detect scale using deterministic methods and validate.
    Updates page_context and metadata.
    
    Returns:
        Scale in pixels per foot
        
    Raises:
        NeedsInputError if scale cannot be determined reliably
    """
    logger.info("Starting deterministic scale detection")
    
    # Check for user override
    scale_override = os.getenv('SCALE_OVERRIDE')
    if scale_override:
        try:
            override_value = float(scale_override)
            logger.info(f"Using SCALE_OVERRIDE: {override_value} px/ft")
            page_context.set_scale(override_value)
            metadata.scale_detection_method = 'user_override'
            metadata.scale_confidence = 1.0
            return override_value
        except ValueError:
            logger.warning(f"Invalid SCALE_OVERRIDE value: {scale_override}")
    
    # Use deterministic scale detector
    scale_result = deterministic_scale_detector.detect_scale(
        ocr_text=ocr_text,
        dimensions=dimensions,
        geometric_elements=geometric_elements,
        page_size=page_size,
        override=None
    )
    
    # Log scale detection results
    logger.info(f"Scale detection result: {scale_result.pixels_per_foot:.1f} px/ft")
    logger.info(f"  Notation: {scale_result.scale_notation}")
    logger.info(f"  Confidence: {scale_result.confidence:.2f}")
    logger.info(f"  Corroborations: {scale_result.corroborations}")
    logger.info(f"  Tolerance: {scale_result.tolerance_percent:.1f}%")
    
    for estimate in scale_result.estimates:
        logger.info(f"  - {estimate.method}: {estimate.pixels_per_foot:.1f} px/ft "
                   f"(confidence: {estimate.confidence:.2f}) - {estimate.evidence}")
    
    # Update metadata
    metadata.scale_detection_method = 'deterministic_multi_method'
    metadata.scale_confidence = scale_result.confidence
    metadata.scale_notation = scale_result.scale_notation
    metadata.scale_corroborations = scale_result.corroborations
    
    # Check if we need user input
    if scale_result.needs_override:
        raise NeedsInputError(
            input_type='scale',
            message=f"Scale detection uncertain ({scale_result.corroborations} corroborations, "
                   f"{scale_result.confidence:.0%} confidence). Manual override required.",
            details={
                'detected_scale': scale_result.pixels_per_foot,
                'notation': scale_result.scale_notation,
                'confidence': scale_result.confidence,
                'corroborations': scale_result.corroborations,
                'estimates': [
                    {'method': e.method, 'scale': e.pixels_per_foot, 'evidence': e.evidence}
                    for e in scale_result.estimates
                ],
                'recommendation': scale_result.recommendation or 
                                'Set SCALE_OVERRIDE=48 for 1/4"=1\' or SCALE_OVERRIDE=96 for 1/8"=1\''
            }
        )
    
    # Set scale in context (will validate consistency)
    page_context.set_scale(scale_result.pixels_per_foot)
    
    return scale_result.pixels_per_foot


def filter_and_validate_rooms(
    rooms: List[Room],
    scale_px_per_ft: float,
    metadata: ParsingMetadata
) -> List[Room]:
    """
    Filter rooms using size and geometry constraints.
    Updates metadata with filtering statistics.
    
    Returns:
        Filtered list of valid rooms
        
    Raises:
        NeedsInputError if room detection results are invalid
    """
    logger.info(f"Starting room filtering with {len(rooms)} input rooms")
    
    # Convert Room objects to dicts for filter
    room_dicts = []
    for room in rooms:
        room_dict = {
            'name': room.name,
            'area': room.area,  # Already in sqft
            'width': getattr(room, 'width', 0),
            'height': getattr(room, 'height', 0),
            'polygon': getattr(room, 'polygon', None),
            'bounds': getattr(room, 'bounds', None),
            'original': room  # Keep reference to original
        }
        
        # If area is in pixels, convert
        if hasattr(room, 'area_px'):
            room_dict['area'] = room.area_px / (scale_px_per_ft ** 2)
        
        room_dicts.append(room_dict)
    
    # Apply room filter
    config = RoomFilterConfig(
        min_room_sqft=float(os.getenv('MIN_ROOM_SQFT', '40')),
        max_room_sqft=float(os.getenv('MAX_ROOM_SQFT', '1000')),
        min_total_sqft=float(os.getenv('MIN_TOTAL_SQFT', '500')),
        max_total_sqft=float(os.getenv('MAX_TOTAL_SQFT', '10000')),
        max_room_count=int(os.getenv('MAX_ROOM_COUNT', '40'))
    )
    
    filter_instance = room_filter if room_filter.config == config else RoomFilter(config)
    
    filtered_dicts, filter_stats = filter_instance.filter_rooms(
        rooms=room_dicts,
        scale_px_per_ft=1.0,  # Already in feet
        enable_strict=True
    )
    
    # Update metadata
    metadata.room_filter_stats = filter_stats
    metadata.rooms_filtered_count = filter_stats['input_count'] - filter_stats['output_count']
    
    # Log filtering results
    logger.info(f"Room filtering complete: {filter_stats['input_count']} -> {filter_stats['output_count']} rooms")
    if filter_stats.get('filtered_reasons'):
        for reason, count in filter_stats['filtered_reasons'].items():
            if count > 0:
                logger.info(f"  Filtered {count} rooms: {reason}")
    
    # Validate total building
    is_valid, error_msg = filter_instance.validate_total_building(filtered_dicts)
    if not is_valid:
        logger.error(f"Building validation failed: {error_msg}")
        
        # Determine what input is needed
        if 'area' in error_msg and 'below minimum' in error_msg:
            input_type = 'scale'
            recommendation = 'Scale may be incorrect. Set SCALE_OVERRIDE if needed.'
        elif 'room count' in error_msg and 'exceeds' in error_msg:
            input_type = 'plan_quality'
            recommendation = 'Too many rooms detected. Check MIN_ROOM_SQFT setting.'
        else:
            input_type = 'plan_quality'
            recommendation = 'Blueprint quality issues detected.'
        
        raise NeedsInputError(
            input_type=input_type,
            message=f"Building validation failed: {error_msg}",
            details={
                'total_area': filter_stats.get('total_area', 0),
                'room_count': filter_stats['output_count'],
                'avg_room_area': filter_stats.get('avg_area', 0),
                'min_room_area': filter_stats.get('min_area', 0),
                'max_room_area': filter_stats.get('max_area', 0),
                'filtered_count': filter_stats['input_count'] - filter_stats['output_count'],
                'filter_reasons': filter_stats.get('filtered_reasons', {}),
                'recommendation': recommendation
            }
        )
    
    # Convert back to Room objects
    filtered_rooms = []
    for room_dict in filtered_dicts:
        if 'original' in room_dict:
            # Update original room with filtered area
            original_room = room_dict['original']
            original_room.area = room_dict['area']
            filtered_rooms.append(original_room)
        else:
            # Create new Room object
            filtered_rooms.append(Room(
                name=room_dict.get('name', 'Unknown'),
                area=room_dict['area'],
                room_type=room_dict.get('room_type', 'other'),
                floor=room_dict.get('floor', 1)
            ))
    
    # Final sanity check
    if not filtered_rooms:
        raise NeedsInputError(
            input_type='plan_quality',
            message="No valid rooms detected after filtering",
            details={
                'input_rooms': filter_stats['input_count'],
                'filter_reasons': filter_stats.get('filtered_reasons', {}),
                'recommendation': 'Check blueprint quality or adjust filter settings'
            }
        )
    
    total_area = sum(r.area for r in filtered_rooms)
    avg_area = total_area / len(filtered_rooms)
    
    logger.info(f"Final room validation: {len(filtered_rooms)} rooms, "
               f"{total_area:.0f} sqft total, {avg_area:.0f} sqft average")
    
    return filtered_rooms


def apply_scale_to_rooms(rooms: List[Room], scale_px_per_ft: float) -> List[Room]:
    """
    Apply scale conversion to rooms if needed.
    """
    for room in rooms:
        # Check if room dimensions are in pixels
        if hasattr(room, 'area_px'):
            room.area = room.area_px / (scale_px_per_ft ** 2)
        
        if hasattr(room, 'width_px'):
            room.width = room.width_px / scale_px_per_ft
        
        if hasattr(room, 'height_px'):
            room.height = room.height_px / scale_px_per_ft
        
        # Convert polygon if in pixels
        if hasattr(room, 'polygon_px'):
            room.polygon = [
                (x/scale_px_per_ft, y/scale_px_per_ft) 
                for x, y in room.polygon_px
            ]
    
    return rooms