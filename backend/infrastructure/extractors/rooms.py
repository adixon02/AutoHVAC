"""
Enhanced Room Detection and Extraction
Detects actual rooms from vector data using computational geometry
Identifies room types, adjacencies, and thermal characteristics
"""

import logging
import math
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DetectedRoom:
    """A room detected from blueprint vectors"""
    room_id: str
    name: str
    room_type: str  # 'bedroom', 'bathroom', 'kitchen', etc.
    polygon: List[Tuple[float, float]]  # Room boundary points
    area_sqft: float
    perimeter_ft: float
    centroid: Tuple[float, float]
    adjacent_rooms: List[str]  # IDs of adjacent rooms
    exterior_walls: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # Wall segments
    interior_walls: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    windows: List[Dict[str, Any]]  # Window locations and sizes
    doors: List[Dict[str, Any]]  # Door locations and types
    ceiling_height_ft: float
    floor_number: int
    confidence: float


@dataclass
class RoomGraph:
    """Graph representation of room adjacencies"""
    rooms: Dict[str, DetectedRoom]
    adjacency_matrix: np.ndarray  # NxN matrix of adjacencies
    room_index: Dict[str, int]  # Room ID to matrix index
    exterior_rooms: Set[str]  # Rooms with exterior walls
    interior_rooms: Set[str]  # Fully interior rooms


class RoomExtractor:
    """
    Extracts actual rooms from vector blueprints
    Uses computational geometry to identify enclosed spaces
    """
    
    # Room type patterns for text matching
    ROOM_PATTERNS = {
        'bedroom': ['BEDROOM', 'BED', 'BR', 'BDRM', 'MASTER', 'GUEST'],
        'bathroom': ['BATHROOM', 'BATH', 'BA', 'TOILET', 'POWDER', 'WC'],
        'kitchen': ['KITCHEN', 'KIT', 'PANTRY'],
        'living': ['LIVING', 'LV', 'FAMILY', 'GREAT ROOM', 'DEN'],
        'dining': ['DINING', 'DN', 'BREAKFAST', 'NOOK'],
        'garage': ['GARAGE', 'GAR', 'CARPORT'],
        'laundry': ['LAUNDRY', 'UTILITY', 'MUD'],
        'closet': ['CLOSET', 'CLO', 'WIC', 'STORAGE'],
        'hallway': ['HALL', 'CORRIDOR', 'FOYER', 'ENTRY'],
        'office': ['OFFICE', 'STUDY', 'LIBRARY'],
        'bonus': ['BONUS', 'REC', 'GAME', 'MEDIA'],
        'mechanical': ['MECHANICAL', 'FURNACE', 'HVAC', 'WATER HEATER']
    }
    
    def __init__(self):
        self.min_room_area = 25  # Minimum 25 sqft to be a room (not a closet)
        self.max_room_area = 1000  # Maximum reasonable room size
        self.wall_thickness = 0.5  # Typical wall thickness in feet
        
    def extract_rooms(
        self,
        vector_data: Dict[str, Any],
        text_blocks: List[Dict[str, Any]],
        scale_factor: float = 1.0,
        floor_number: int = 1,
        vision_results: Optional[Dict] = None
    ) -> RoomGraph:
        """
        Extract all rooms from vector data
        
        Args:
            vector_data: Vector paths and texts
            text_blocks: Text labels from PDF
            scale_factor: Scale conversion factor
            floor_number: Which floor this is
            vision_results: Optional GPT-4V analysis
            
        Returns:
            RoomGraph with all detected rooms and adjacencies
        """
        logger.info(f"Extracting rooms from floor {floor_number}")
        
        # 1. Find all closed polygons (potential rooms)
        polygons = self._find_closed_polygons(vector_data, scale_factor)
        logger.info(f"Found {len(polygons)} potential room polygons")
        
        # 2. Filter and validate polygons
        valid_rooms = []
        for i, polygon in enumerate(polygons):
            area = self._calculate_polygon_area(polygon)
            if self.min_room_area <= area <= self.max_room_area:
                room = DetectedRoom(
                    room_id=f"room_{floor_number}_{i}",
                    name=f"Room {i+1}",
                    room_type="unknown",
                    polygon=polygon,
                    area_sqft=area,
                    perimeter_ft=self._calculate_perimeter(polygon),
                    centroid=self._calculate_centroid(polygon),
                    adjacent_rooms=[],
                    exterior_walls=[],
                    interior_walls=[],
                    windows=[],
                    doors=[],
                    ceiling_height_ft=9.0,  # Default
                    floor_number=floor_number,
                    confidence=0.7
                )
                valid_rooms.append(room)
        
        logger.info(f"Validated {len(valid_rooms)} rooms")
        
        # 3. Identify room types from text labels
        self._identify_room_types(valid_rooms, text_blocks, vector_data)
        
        # 4. Determine wall types (exterior vs interior)
        self._classify_walls(valid_rooms)
        
        # 5. Build adjacency graph
        room_graph = self._build_adjacency_graph(valid_rooms)
        
        # 6. Find windows and doors
        self._extract_openings(room_graph, vector_data, text_blocks)
        
        # 7. Apply vision results if available
        if vision_results and 'rooms' in vision_results:
            self._apply_vision_results(room_graph, vision_results['rooms'])
        
        # Log summary
        room_types = defaultdict(int)
        for room in room_graph.rooms.values():
            room_types[room.room_type] += 1
        
        logger.info(f"Room extraction complete: {dict(room_types)}")
        logger.info(f"Exterior rooms: {len(room_graph.exterior_rooms)}, "
                   f"Interior rooms: {len(room_graph.interior_rooms)}")
        
        return room_graph
    
    def _find_closed_polygons(
        self,
        vector_data: Dict[str, Any],
        scale_factor: float
    ) -> List[List[Tuple[float, float]]]:
        """
        Find closed polygons representing rooms
        OPTIMIZED: Skip complex polygon detection for now
        """
        if not vector_data or 'paths' not in vector_data:
            return []
        
        paths = vector_data['paths']
        
        # Enhanced detection: Look for both rectangles and line-based polygons
        polygons = []
        
        # 1. Find explicit rectangles first
        for path in paths[:1000]:  # Limit to first 1000 paths for speed
            if hasattr(path, 'points'):
                points = path.points
                path_type = getattr(path, 'path_type', 'line')
            else:
                points = path.get('points', [])
                path_type = path.get('path_type', 'line')
            
            # Process rectangles
            if path_type == 'rect' and len(points) >= 4:
                scaled_points = [(p[0] * scale_factor, p[1] * scale_factor) for p in points]
                
                # Check if it's room-sized (not too small, not too big)
                width = abs(scaled_points[1][0] - scaled_points[0][0])
                height = abs(scaled_points[2][1] - scaled_points[1][1])
                area = width * height
                
                if self.min_room_area <= area <= self.max_room_area:
                    polygons.append(scaled_points[:4])
        
        logger.info(f"Found {len(polygons)} explicit rectangles")
        
        # 2. Build simple polygon detection from line segments (optimized approach)
        # Extract all line segments
        line_segments = []
        for path in paths[:2000]:  # Look at more paths for lines
            if hasattr(path, 'points'):
                points = path.points
                path_type = getattr(path, 'path_type', 'line')
            else:
                points = path.get('points', [])
                path_type = path.get('path_type', 'line')
            
            if path_type == 'line' and len(points) >= 2:
                scaled_points = [(p[0] * scale_factor, p[1] * scale_factor) for p in points]
                # Add each line segment
                for i in range(len(scaled_points) - 1):
                    line_segments.append((scaled_points[i], scaled_points[i + 1]))
        
        logger.info(f"Found {len(line_segments)} line segments for polygon detection")
        
        # 3. Find rectangular patterns from line segments (simpler approach)
        # Group parallel lines that could form rectangles
        horizontal_lines = []
        vertical_lines = []
        
        for (p1, p2) in line_segments:
            length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            if length < 5:  # Skip very short lines
                continue
                
            # Check if line is horizontal or vertical (within tolerance)
            if abs(p1[1] - p2[1]) < 2:  # Horizontal line
                horizontal_lines.append((min(p1[0], p2[0]), max(p1[0], p2[0]), p1[1]))
            elif abs(p1[0] - p2[0]) < 2:  # Vertical line  
                vertical_lines.append((min(p1[1], p2[1]), max(p1[1], p2[1]), p1[0]))
        
        # Find rectangles from parallel line pairs
        rectangles_from_lines = self._find_rectangles_from_lines(horizontal_lines, vertical_lines)
        polygons.extend(rectangles_from_lines)
        
        logger.info(f"Found {len(rectangles_from_lines)} rectangles from line segments")
        logger.info(f"Total polygons found: {len(polygons)}")
        
        return polygons
    
    def _build_intersection_graph(
        self,
        segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    ) -> Dict[Tuple[float, float], List[Tuple[float, float]]]:
        """Build graph of segment intersections"""
        graph = defaultdict(list)
        tolerance = 2.0  # 2 feet tolerance for connections
        
        # Connect segments that share endpoints or are very close
        for i, (p1, p2) in enumerate(segments):
            for j, (q1, q2) in enumerate(segments[i+1:], i+1):
                # Check endpoint connections
                if self._points_close(p1, q1, tolerance):
                    graph[p1].append(p2)
                    graph[q1].append(q2)
                elif self._points_close(p1, q2, tolerance):
                    graph[p1].append(p2)
                    graph[q2].append(q1)
                elif self._points_close(p2, q1, tolerance):
                    graph[p2].append(p1)
                    graph[q1].append(q2)
                elif self._points_close(p2, q2, tolerance):
                    graph[p2].append(p1)
                    graph[q2].append(q1)
                
                # Check for T-intersections
                intersection = self._line_intersection(p1, p2, q1, q2)
                if intersection:
                    graph[intersection].extend([p1, p2, q1, q2])
        
        return graph
    
    def _find_cycles_in_graph(
        self,
        graph: Dict[Tuple[float, float], List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """Find closed cycles (rooms) in the intersection graph"""
        cycles = []
        visited_edges = set()
        
        for start_node in graph:
            # Try to find cycles starting from each node
            cycle = self._find_cycle_from_node(start_node, graph, visited_edges)
            if cycle and len(cycle) >= 3:  # Minimum 3 points for a room
                # Check if this is a new unique cycle
                cycle_set = frozenset(cycle)
                is_new = True
                for existing in cycles:
                    if frozenset(existing) == cycle_set:
                        is_new = False
                        break
                
                if is_new:
                    cycles.append(cycle)
        
        return cycles
    
    def _find_cycle_from_node(
        self,
        start: Tuple[float, float],
        graph: Dict,
        visited: Set
    ) -> Optional[List[Tuple[float, float]]]:
        """DFS to find a cycle from a starting node"""
        # Simplified cycle detection
        # In practice, this would use more sophisticated algorithms
        path = [start]
        current = start
        
        for _ in range(20):  # Limit search depth
            neighbors = graph.get(current, [])
            if not neighbors:
                break
            
            # Choose next unvisited neighbor
            next_node = None
            for n in neighbors:
                edge = (min(current, n), max(current, n))
                if edge not in visited:
                    next_node = n
                    visited.add(edge)
                    break
            
            if not next_node:
                break
            
            if next_node == start and len(path) >= 3:
                # Found a cycle
                return path
            
            path.append(next_node)
            current = next_node
        
        return None
    
    def _points_close(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        tolerance: float
    ) -> bool:
        """Check if two points are within tolerance"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) < tolerance
    
    def _line_intersection(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> Optional[Tuple[float, float]]:
        """Find intersection point of two line segments"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 0.001:
            return None  # Parallel lines
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            # Intersection exists
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y)
        
        return None
    
    def _find_rectangles_from_lines(
        self,
        horizontal_lines: List[Tuple[float, float, float]],  # (x1, x2, y)
        vertical_lines: List[Tuple[float, float, float]]     # (y1, y2, x)
    ) -> List[List[Tuple[float, float]]]:
        """Find rectangles from horizontal and vertical line segments"""
        rectangles = []
        tolerance = 3.0  # 3 feet tolerance for line alignment
        
        # For each pair of horizontal lines, try to find matching vertical lines
        for i, (h1_x1, h1_x2, h1_y) in enumerate(horizontal_lines):
            for j, (h2_x1, h2_x2, h2_y) in enumerate(horizontal_lines[i+1:], i+1):
                # Check if lines are parallel and separated
                if abs(h1_y - h2_y) < 5:  # Too close, probably same line
                    continue
                    
                height = abs(h2_y - h1_y)
                if height < 5 or height > 50:  # Reasonable room height
                    continue
                
                # Find overlap in x direction
                overlap_x1 = max(h1_x1, h2_x1)
                overlap_x2 = min(h1_x2, h2_x2)
                
                if overlap_x2 - overlap_x1 < 5:  # No significant overlap
                    continue
                
                # Look for vertical lines that could complete this rectangle
                for v1_y1, v1_y2, v1_x in vertical_lines:
                    for v2_y1, v2_y2, v2_x in vertical_lines:
                        # Check if vertical lines span the horizontal lines
                        if (abs(v1_x - overlap_x1) < tolerance and 
                            abs(v2_x - overlap_x2) < tolerance and
                            min(v1_y1, v1_y2) <= min(h1_y, h2_y) - tolerance and
                            max(v1_y1, v1_y2) >= max(h1_y, h2_y) + tolerance and
                            min(v2_y1, v2_y2) <= min(h1_y, h2_y) - tolerance and
                            max(v2_y1, v2_y2) >= max(h1_y, h2_y) + tolerance):
                            
                            # Found a rectangle!
                            width = abs(v2_x - v1_x)
                            area = width * height
                            
                            if self.min_room_area <= area <= self.max_room_area:
                                # Create rectangle corners
                                corners = [
                                    (min(v1_x, v2_x), min(h1_y, h2_y)),
                                    (max(v1_x, v2_x), min(h1_y, h2_y)),
                                    (max(v1_x, v2_x), max(h1_y, h2_y)),
                                    (min(v1_x, v2_x), max(h1_y, h2_y))
                                ]
                                
                                # Check for duplicates (same area and approximate position)
                                is_duplicate = False
                                for existing in rectangles:
                                    if (abs(self._calculate_polygon_area(existing) - area) < 10 and
                                        abs(existing[0][0] - corners[0][0]) < 5 and
                                        abs(existing[0][1] - corners[0][1]) < 5):
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    rectangles.append(corners)
        
        return rectangles
    
    def _calculate_polygon_area(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate area using shoelace formula"""
        if len(polygon) < 3:
            return 0
        
        area = 0
        n = len(polygon)
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        
        return abs(area) / 2
    
    def _calculate_perimeter(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate polygon perimeter"""
        if len(polygon) < 2:
            return 0
        
        perimeter = 0
        n = len(polygon)
        for i in range(n):
            j = (i + 1) % n
            dx = polygon[j][0] - polygon[i][0]
            dy = polygon[j][1] - polygon[i][1]
            perimeter += math.sqrt(dx**2 + dy**2)
        
        return perimeter
    
    def _calculate_centroid(self, polygon: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate polygon centroid"""
        if not polygon:
            return (0, 0)
        
        cx = sum(p[0] for p in polygon) / len(polygon)
        cy = sum(p[1] for p in polygon) / len(polygon)
        return (cx, cy)
    
    def _identify_room_types(
        self,
        rooms: List[DetectedRoom],
        text_blocks: List[Dict],
        vector_data: Dict
    ):
        """Identify room types from nearby text labels"""
        # Get text with positions
        texts_with_pos = []
        
        # From text blocks
        for block in text_blocks:
            if 'bbox' in block:
                x = (block['bbox'][0] + block['bbox'][2]) / 2
                y = (block['bbox'][1] + block['bbox'][3]) / 2
                texts_with_pos.append({
                    'text': block['text'],
                    'pos': (x, y)
                })
        
        # From vector texts
        if 'texts' in vector_data:
            for text_item in vector_data['texts']:
                if hasattr(text_item, 'text') and hasattr(text_item, 'position'):
                    texts_with_pos.append({
                        'text': text_item.text,
                        'pos': text_item.position
                    })
        
        # Match rooms to labels
        for room in rooms:
            centroid = room.centroid
            min_dist = float('inf')
            best_label = None
            
            for text_item in texts_with_pos:
                dist = math.sqrt(
                    (centroid[0] - text_item['pos'][0])**2 +
                    (centroid[1] - text_item['pos'][1])**2
                )
                
                if dist < min_dist:
                    min_dist = dist
                    best_label = text_item['text']
            
            if best_label and min_dist < 50:  # Within 50 units
                # Identify room type from label
                label_upper = best_label.upper()
                for room_type, patterns in self.ROOM_PATTERNS.items():
                    for pattern in patterns:
                        if pattern in label_upper:
                            room.room_type = room_type
                            room.name = best_label
                            room.confidence = 0.9
                            break
                    if room.room_type != "unknown":
                        break
    
    def _classify_walls(self, rooms: List[DetectedRoom]):
        """Classify walls as exterior or interior"""
        # Find the overall bounding box
        all_points = []
        for room in rooms:
            all_points.extend(room.polygon)
        
        if not all_points:
            return
        
        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)
        
        tolerance = 5.0  # 5 feet from boundary = exterior
        
        for room in rooms:
            n = len(room.polygon)
            for i in range(n):
                j = (i + 1) % n
                wall = (room.polygon[i], room.polygon[j])
                
                # Check if wall is near building perimeter
                is_exterior = False
                
                # Check each point
                for point in wall:
                    if (abs(point[0] - min_x) < tolerance or
                        abs(point[0] - max_x) < tolerance or
                        abs(point[1] - min_y) < tolerance or
                        abs(point[1] - max_y) < tolerance):
                        is_exterior = True
                        break
                
                if is_exterior:
                    room.exterior_walls.append(wall)
                else:
                    room.interior_walls.append(wall)
    
    def _build_adjacency_graph(self, rooms: List[DetectedRoom]) -> RoomGraph:
        """Build graph of room adjacencies"""
        room_dict = {room.room_id: room for room in rooms}
        n = len(rooms)
        adjacency = np.zeros((n, n), dtype=bool)
        room_index = {room.room_id: i for i, room in enumerate(rooms)}
        
        # Check for shared walls between rooms
        for i, room1 in enumerate(rooms):
            for j, room2 in enumerate(rooms[i+1:], i+1):
                if self._rooms_adjacent(room1, room2):
                    adjacency[i, j] = True
                    adjacency[j, i] = True
                    room1.adjacent_rooms.append(room2.room_id)
                    room2.adjacent_rooms.append(room1.room_id)
        
        # Identify exterior vs interior rooms
        exterior_rooms = {room.room_id for room in rooms if room.exterior_walls}
        interior_rooms = {room.room_id for room in rooms if not room.exterior_walls}
        
        return RoomGraph(
            rooms=room_dict,
            adjacency_matrix=adjacency,
            room_index=room_index,
            exterior_rooms=exterior_rooms,
            interior_rooms=interior_rooms
        )
    
    def _rooms_adjacent(self, room1: DetectedRoom, room2: DetectedRoom) -> bool:
        """Check if two rooms share a wall"""
        tolerance = 3.0  # 3 feet tolerance
        
        # Check if any walls are shared
        for wall1 in room1.polygon:
            for wall2 in room2.polygon:
                if self._points_close(wall1, wall2, tolerance):
                    return True
        
        return False
    
    def _extract_openings(
        self,
        room_graph: RoomGraph,
        vector_data: Dict,
        text_blocks: List[Dict]
    ):
        """Extract windows and doors for each room"""
        # This would analyze vector data for window/door symbols
        # For now, use heuristics based on room type
        
        for room in room_graph.rooms.values():
            # Windows on exterior walls
            if room.exterior_walls:
                window_count = len(room.exterior_walls)
                for i, wall in enumerate(room.exterior_walls):
                    # Place window in center of wall
                    center = (
                        (wall[0][0] + wall[1][0]) / 2,
                        (wall[0][1] + wall[1][1]) / 2
                    )
                    room.windows.append({
                        'position': center,
                        'width_ft': 4,
                        'height_ft': 5,
                        'area_sqft': 20,
                        'wall_index': i
                    })
            
            # Doors based on room type
            if room.room_type in ['bedroom', 'bathroom', 'kitchen']:
                room.doors.append({
                    'type': 'interior',
                    'width_ft': 3,
                    'height_ft': 7
                })
    
    def _apply_vision_results(self, room_graph: RoomGraph, vision_results: List[Dict]):
        """Apply GPT-4V vision analysis results"""
        for vision_room in vision_results:
            # Match vision room to detected room
            for room in room_graph.rooms.values():
                if (vision_room.get('type') == room.room_type or
                    vision_room.get('name', '').upper() in room.name.upper()):
                    # Update room with vision data
                    if 'area' in vision_room:
                        room.area_sqft = vision_room['area']
                    if 'windows' in vision_room:
                        room.windows = vision_room['windows']
                    room.confidence = 0.95
                    break


# Singleton instance
_room_extractor = None


def get_room_extractor() -> RoomExtractor:
    """Get or create the global room extractor"""
    global _room_extractor
    if _room_extractor is None:
        _room_extractor = RoomExtractor()
    return _room_extractor