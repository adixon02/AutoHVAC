"""
Room Filtering and Validation Module
Ensures only valid rooms are included in HVAC calculations
"""

import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


@dataclass
class RoomFilterConfig:
    """Configuration for room filtering"""
    min_room_sqft: float = 40.0      # Minimum room size
    max_room_sqft: float = 1000.0    # Maximum room size (single room)
    min_room_width_ft: float = 4.0   # Minimum room dimension
    max_aspect_ratio: float = 5.0    # Maximum length/width ratio
    min_total_sqft: float = 500.0    # Minimum total building size
    max_total_sqft: float = 10000.0  # Maximum total for SFH
    max_room_count: int = 40         # Maximum rooms for SFH
    
    # Tolerance for polygon operations
    simplify_tolerance_ft: float = 0.5
    buffer_tolerance_ft: float = 0.1


class RoomFilter:
    """
    Filters and validates rooms extracted from blueprints.
    Removes non-room elements and ensures reasonable sizes.
    """
    
    def __init__(self, config: Optional[RoomFilterConfig] = None):
        self.config = config or RoomFilterConfig()
    
    def filter_rooms(
        self,
        rooms: List[Dict[str, Any]],
        scale_px_per_ft: float,
        enable_strict: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter rooms based on size and geometry constraints.
        
        Args:
            rooms: List of room dictionaries with polygon/bounds
            scale_px_per_ft: Scale factor for converting pixels to feet
            enable_strict: Whether to apply strict filtering
            
        Returns:
            Tuple of (filtered_rooms, filter_stats)
        """
        if not rooms:
            return [], {'input_count': 0, 'output_count': 0, 'filtered_reasons': {}}
        
        logger.info(f"Starting room filter with {len(rooms)} input rooms")
        
        filtered_rooms = []
        filter_stats = {
            'input_count': len(rooms),
            'filtered_reasons': {
                'too_small': 0,
                'too_large': 0,
                'bad_aspect': 0,
                'bad_geometry': 0,
                'duplicate': 0,
                'non_room': 0
            }
        }
        
        # Convert and validate each room
        for i, room in enumerate(rooms):
            try:
                # Convert to feet
                room_ft = self._convert_to_feet(room, scale_px_per_ft)
                
                if not room_ft:
                    filter_stats['filtered_reasons']['bad_geometry'] += 1
                    continue
                
                # Apply filters
                reason = self._check_room_validity(room_ft, enable_strict)
                
                if reason:
                    filter_stats['filtered_reasons'][reason] += 1
                    logger.debug(f"Room {i} filtered: {reason} (area={room_ft.get('area', 0):.1f} sqft)")
                else:
                    filtered_rooms.append(room_ft)
                    
            except Exception as e:
                logger.warning(f"Error processing room {i}: {e}")
                filter_stats['filtered_reasons']['bad_geometry'] += 1
        
        # Remove duplicates/overlaps
        filtered_rooms = self._remove_duplicates(filtered_rooms, filter_stats)
        
        # Check if we're detecting non-room elements
        if enable_strict:
            filtered_rooms = self._remove_non_rooms(filtered_rooms, filter_stats)
        
        filter_stats['output_count'] = len(filtered_rooms)
        
        # Log filtering results
        logger.info(f"Room filter complete: {len(rooms)} -> {len(filtered_rooms)} rooms")
        for reason, count in filter_stats['filtered_reasons'].items():
            if count > 0:
                logger.info(f"  Filtered {count} rooms: {reason}")
        
        # Calculate statistics
        if filtered_rooms:
            areas = [r['area'] for r in filtered_rooms]
            filter_stats['min_area'] = min(areas)
            filter_stats['max_area'] = max(areas)
            filter_stats['avg_area'] = sum(areas) / len(areas)
            filter_stats['total_area'] = sum(areas)
        
        return filtered_rooms, filter_stats
    
    def _convert_to_feet(self, room: Dict[str, Any], scale_px_per_ft: float) -> Optional[Dict[str, Any]]:
        """Convert room from pixels to feet."""
        try:
            room_ft = room.copy()
            
            # Convert polygon if present
            if 'polygon' in room:
                polygon_px = room['polygon']
                polygon_ft = [(x/scale_px_per_ft, y/scale_px_per_ft) for x, y in polygon_px]
                room_ft['polygon'] = polygon_ft
                
                # Calculate area and dimensions from polygon
                poly = Polygon(polygon_ft)
                if poly.is_valid and poly.area > 0:
                    room_ft['area'] = poly.area
                    room_ft['perimeter'] = poly.length
                    
                    # Get bounding box
                    minx, miny, maxx, maxy = poly.bounds
                    room_ft['width'] = maxx - minx
                    room_ft['height'] = maxy - miny
                    room_ft['bounds'] = (minx, miny, maxx, maxy)
                else:
                    return None
                    
            # Convert rectangle bounds if no polygon
            elif 'bounds' in room or ('x' in room and 'y' in room):
                if 'bounds' in room:
                    x1, y1, x2, y2 = room['bounds']
                else:
                    x1, y1 = room['x'], room['y']
                    x2, y2 = x1 + room.get('width', 0), y1 + room.get('height', 0)
                
                x1_ft, y1_ft = x1/scale_px_per_ft, y1/scale_px_per_ft
                x2_ft, y2_ft = x2/scale_px_per_ft, y2/scale_px_per_ft
                
                room_ft['bounds'] = (x1_ft, y1_ft, x2_ft, y2_ft)
                room_ft['width'] = abs(x2_ft - x1_ft)
                room_ft['height'] = abs(y2_ft - y1_ft)
                room_ft['area'] = room_ft['width'] * room_ft['height']
                room_ft['perimeter'] = 2 * (room_ft['width'] + room_ft['height'])
                
            # Convert simple width/height
            elif 'width' in room and 'height' in room:
                room_ft['width'] = room['width'] / scale_px_per_ft
                room_ft['height'] = room['height'] / scale_px_per_ft
                room_ft['area'] = room_ft['width'] * room_ft['height']
                room_ft['perimeter'] = 2 * (room_ft['width'] + room_ft['height'])
                
            # Must have area by now
            elif 'area' not in room_ft:
                return None
            
            return room_ft
            
        except Exception as e:
            logger.debug(f"Failed to convert room: {e}")
            return None
    
    def _check_room_validity(self, room: Dict[str, Any], enable_strict: bool) -> Optional[str]:
        """
        Check if room meets validity criteria.
        Returns rejection reason or None if valid.
        """
        area = room.get('area', 0)
        width = room.get('width', 0)
        height = room.get('height', 0)
        
        # Area checks
        if area < self.config.min_room_sqft:
            return 'too_small'
        
        if area > self.config.max_room_sqft:
            return 'too_large'
        
        # Dimension checks
        if width > 0 and height > 0:
            min_dim = min(width, height)
            max_dim = max(width, height)
            
            if min_dim < self.config.min_room_width_ft:
                return 'too_small'  # Too narrow
            
            if enable_strict:
                aspect_ratio = max_dim / min_dim if min_dim > 0 else float('inf')
                if aspect_ratio > self.config.max_aspect_ratio:
                    return 'bad_aspect'  # Too elongated (likely a hallway)
        
        # Check for micro-rooms that might be fixtures/hatching
        if enable_strict and area < 10:  # Less than 10 sqft
            return 'non_room'
        
        return None  # Valid room
    
    def _remove_duplicates(self, rooms: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Remove duplicate or heavily overlapping rooms."""
        if len(rooms) <= 1:
            return rooms
        
        unique_rooms = []
        processed_indices = set()
        
        for i, room1 in enumerate(rooms):
            if i in processed_indices:
                continue
            
            # Check for overlaps with other rooms
            is_duplicate = False
            
            for j, room2 in enumerate(rooms[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                # Check if rooms overlap significantly
                if self._rooms_overlap(room1, room2):
                    # Keep the larger room
                    if room1.get('area', 0) >= room2.get('area', 0):
                        processed_indices.add(j)
                        stats['filtered_reasons']['duplicate'] += 1
                    else:
                        is_duplicate = True
                        processed_indices.add(i)
                        stats['filtered_reasons']['duplicate'] += 1
                        break
            
            if not is_duplicate:
                unique_rooms.append(room1)
        
        return unique_rooms
    
    def _rooms_overlap(self, room1: Dict[str, Any], room2: Dict[str, Any]) -> bool:
        """Check if two rooms overlap significantly (>80% of smaller room)."""
        try:
            # Use polygons if available
            if 'polygon' in room1 and 'polygon' in room2:
                poly1 = Polygon(room1['polygon'])
                poly2 = Polygon(room2['polygon'])
                
                if poly1.is_valid and poly2.is_valid:
                    intersection = poly1.intersection(poly2)
                    if intersection.area > 0:
                        smaller_area = min(poly1.area, poly2.area)
                        overlap_ratio = intersection.area / smaller_area
                        return overlap_ratio > 0.8
            
            # Use bounds as fallback
            elif 'bounds' in room1 and 'bounds' in room2:
                x1_min, y1_min, x1_max, y1_max = room1['bounds']
                x2_min, y2_min, x2_max, y2_max = room2['bounds']
                
                # Calculate intersection
                x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
                y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
                
                if x_overlap > 0 and y_overlap > 0:
                    intersection_area = x_overlap * y_overlap
                    smaller_area = min(room1.get('area', float('inf')), 
                                     room2.get('area', float('inf')))
                    
                    if smaller_area > 0:
                        overlap_ratio = intersection_area / smaller_area
                        return overlap_ratio > 0.8
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking room overlap: {e}")
            return False
    
    def _remove_non_rooms(self, rooms: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Remove elements that are likely not rooms (hatching, fixtures, etc).
        Uses statistical analysis to identify outliers.
        """
        if len(rooms) < 5:
            return rooms  # Not enough data for statistical filtering
        
        areas = [r['area'] for r in rooms]
        
        # Calculate statistics
        mean_area = sum(areas) / len(areas)
        median_area = sorted(areas)[len(areas)//2]
        
        # If median is very different from mean, we might have outliers
        if median_area < mean_area * 0.5:
            # Many small elements - filter more aggressively
            threshold = median_area * 3  # Keep rooms within 3x median
        else:
            # Normal distribution - use standard thresholds
            threshold = self.config.max_room_sqft
        
        filtered = []
        for room in rooms:
            if room['area'] <= threshold:
                filtered.append(room)
            else:
                stats['filtered_reasons']['non_room'] += 1
                logger.debug(f"Filtered non-room element: {room['area']:.1f} sqft > {threshold:.1f}")
        
        return filtered
    
    def validate_total_building(self, rooms: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Validate the total building makes sense for residential.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not rooms:
            return False, "No rooms found"
        
        total_area = sum(r.get('area', 0) for r in rooms)
        room_count = len(rooms)
        avg_area = total_area / room_count if room_count > 0 else 0
        
        # Check total area
        if total_area < self.config.min_total_sqft:
            return False, f"Total area {total_area:.0f} sqft below minimum ({self.config.min_total_sqft})"
        
        if total_area > self.config.max_total_sqft:
            return False, f"Total area {total_area:.0f} sqft exceeds SFH maximum ({self.config.max_total_sqft})"
        
        # Check room count
        if room_count > self.config.max_room_count:
            return False, f"Room count {room_count} exceeds typical SFH ({self.config.max_room_count})"
        
        # Check average room size
        if avg_area < self.config.min_room_sqft:
            return False, f"Average room size {avg_area:.0f} sqft below minimum ({self.config.min_room_sqft})"
        
        return True, None


# Singleton instance with default config
room_filter = RoomFilter()