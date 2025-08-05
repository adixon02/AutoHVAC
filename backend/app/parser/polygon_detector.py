"""
Polygon-based room detection from wall lines
Detects closed polygons formed by connected wall segments to identify rooms
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict
import cv2

logger = logging.getLogger(__name__)


class PolygonRoomDetector:
    """
    Detects rooms by finding closed polygons formed by wall lines.
    This is how professional architectural software identifies rooms.
    """
    
    def __init__(self):
        # Wall detection thresholds
        self.MIN_WALL_LENGTH = 20  # pixels - minimum length to be considered a wall
        self.MIN_WALL_THICKNESS = 1.5  # pixels - minimum thickness for walls
        self.WALL_MERGE_DISTANCE = 10  # pixels - distance to merge parallel walls
        
        # Room polygon thresholds (now scale-aware)
        self.MIN_ROOM_AREA_SQFT = 10  # Minimum room size in square feet
        self.MAX_ROOM_AREA_SQFT = 1200  # Maximum room size in square feet
        
        # Legacy pixel-based thresholds (for when scale is unknown)
        self.MIN_ROOM_AREA = 10  # square pixels (reduced from 100)
        self.MAX_ROOM_AREA = 1000000  # square pixels (increased from 100000)
        
        # Connection tolerances
        self.ENDPOINT_TOLERANCE = 15  # pixels - max distance to connect wall endpoints
        self.ANGLE_TOLERANCE = 15  # degrees - max angle difference for parallel walls
        
    def detect_rooms(
        self,
        lines: List[Dict[str, Any]],
        page_width: float,
        page_height: float,
        scale_factor: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point - detects rooms from wall lines
        
        Args:
            lines: List of line segments from geometry parser
            page_width: PDF page width in pixels
            page_height: PDF page height in pixels
            scale_factor: Pixels per foot for scaling
            
        Returns:
            List of detected room polygons with metadata
        """
        logger.info(f"Starting polygon room detection with {len(lines)} lines")
        
        # Step 1: Filter and classify lines as walls
        walls = self.extract_wall_segments(lines)
        logger.info(f"Extracted {len(walls)} wall segments from {len(lines)} lines")
        
        if not walls:
            logger.warning("No wall segments found - cannot detect rooms")
            return []
        
        # Step 2: Build wall connectivity graph
        graph = self.build_wall_graph(walls)
        logger.info(f"Built connectivity graph with {len(graph)} nodes")
        
        # Step 3: Find closed polygons (rooms)
        polygons = self.find_closed_polygons(graph, walls)
        logger.info(f"Found {len(polygons)} closed polygons")
        
        # Step 4: Filter and validate polygons as rooms
        rooms = self.filter_valid_rooms(polygons, scale_factor)
        logger.info(f"Validated {len(rooms)} rooms from {len(polygons)} polygons")
        
        # Step 5: Generate debug visualization
        self.save_debug_artifacts(walls, polygons, rooms, page_width, page_height)
        
        return rooms
    
    def extract_wall_segments(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter lines to identify wall segments based on thickness and length
        """
        walls = []
        
        for line in lines:
            # Extract line properties
            x0 = line.get('x0', 0)
            y0 = line.get('y0', 0)
            x1 = line.get('x1', 0)
            y1 = line.get('y1', 0)
            width = line.get('width', 1.0)
            length = line.get('length', 0)
            
            # Calculate length if not provided
            if length == 0:
                length = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
            
            # Filter based on wall characteristics
            if length >= self.MIN_WALL_LENGTH and width >= self.MIN_WALL_THICKNESS:
                # Calculate wall properties
                angle = np.arctan2(y1 - y0, x1 - x0)
                
                walls.append({
                    'x0': x0,
                    'y0': y0,
                    'x1': x1,
                    'y1': y1,
                    'width': width,
                    'length': length,
                    'angle': angle,
                    'type': 'wall',
                    'endpoints': [(x0, y0), (x1, y1)]
                })
        
        # Merge parallel walls that are close together (double walls in blueprints)
        walls = self.merge_parallel_walls(walls)
        
        return walls
    
    def merge_parallel_walls(self, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge parallel walls that are close together (common in architectural drawings)
        """
        if len(walls) < 2:
            return walls
        
        merged = []
        used = set()
        
        for i, wall1 in enumerate(walls):
            if i in used:
                continue
                
            # Check for parallel walls nearby
            merged_wall = wall1.copy()
            
            for j, wall2 in enumerate(walls[i+1:], i+1):
                if j in used:
                    continue
                
                # Check if walls are parallel
                angle_diff = abs(wall1['angle'] - wall2['angle'])
                if angle_diff > np.pi:
                    angle_diff = 2 * np.pi - angle_diff
                
                if angle_diff < np.radians(self.ANGLE_TOLERANCE):
                    # Check if walls are close
                    dist = self.line_to_line_distance(wall1, wall2)
                    if dist < self.WALL_MERGE_DISTANCE:
                        # Merge walls
                        used.add(j)
                        # Keep the longer wall or average position
                        if wall2['length'] > merged_wall['length']:
                            merged_wall = wall2.copy()
            
            merged.append(merged_wall)
        
        return merged
    
    def build_wall_graph(self, walls: List[Dict[str, Any]]) -> Dict[Tuple[float, float], List[int]]:
        """
        Build connectivity graph where nodes are wall endpoints and edges are walls
        """
        graph = defaultdict(list)
        
        for idx, wall in enumerate(walls):
            # Add wall to graph at both endpoints
            p1 = (round(wall['x0'], 1), round(wall['y0'], 1))
            p2 = (round(wall['x1'], 1), round(wall['y1'], 1))
            
            graph[p1].append(idx)
            graph[p2].append(idx)
        
        # Connect nearby endpoints that should be connected
        self.connect_nearby_endpoints(graph, walls)
        
        return graph
    
    def connect_nearby_endpoints(
        self, 
        graph: Dict[Tuple[float, float], List[int]], 
        walls: List[Dict[str, Any]]
    ):
        """
        Connect wall endpoints that are close but not exactly touching
        """
        endpoints = list(graph.keys())
        
        for i, p1 in enumerate(endpoints):
            for p2 in endpoints[i+1:]:
                dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                
                if 0 < dist < self.ENDPOINT_TOLERANCE:
                    # Merge these endpoints
                    walls_at_p2 = graph[p2]
                    graph[p1].extend(walls_at_p2)
                    
                    # Update wall endpoints
                    for wall_idx in walls_at_p2:
                        wall = walls[wall_idx]
                        if abs(wall['x0'] - p2[0]) < 1 and abs(wall['y0'] - p2[1]) < 1:
                            wall['x0'] = p1[0]
                            wall['y0'] = p1[1]
                        if abs(wall['x1'] - p2[0]) < 1 and abs(wall['y1'] - p2[1]) < 1:
                            wall['x1'] = p1[0]
                            wall['y1'] = p1[1]
                    
                    del graph[p2]
    
    def find_closed_polygons(
        self, 
        graph: Dict[Tuple[float, float], List[int]], 
        walls: List[Dict[str, Any]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Find closed polygons (cycles) in the wall graph using DFS
        """
        polygons = []
        visited_edges = set()
        
        def find_cycle(start_point, current_point, path, visited):
            """DFS to find cycles"""
            if len(path) > 3 and current_point == start_point:
                # Found a cycle
                return [path[:]]
            
            if len(path) > 20:  # Max room complexity
                return []
            
            cycles = []
            
            # Get walls at current point
            for wall_idx in graph.get(current_point, []):
                if wall_idx in visited:
                    continue
                
                wall = walls[wall_idx]
                # Get the other endpoint
                p1 = (round(wall['x0'], 1), round(wall['y0'], 1))
                p2 = (round(wall['x1'], 1), round(wall['y1'], 1))
                
                next_point = p2 if current_point == p1 else p1
                
                visited.add(wall_idx)
                path.append(next_point)
                
                cycles.extend(find_cycle(start_point, next_point, path, visited))
                
                path.pop()
                visited.remove(wall_idx)
            
            return cycles
        
        # Try to find cycles starting from each node
        for start_point in graph.keys():
            cycles = find_cycle(start_point, start_point, [start_point], set())
            
            for cycle in cycles:
                # Check if this polygon is new
                polygon = self.order_polygon_points(cycle)
                if polygon and not self.is_duplicate_polygon(polygon, polygons):
                    polygons.append(polygon)
        
        return polygons
    
    def filter_valid_rooms(
        self, 
        polygons: List[List[Tuple[float, float]]], 
        scale_factor: Optional[float]
    ) -> List[Dict[str, Any]]:
        """
        Filter polygons to identify valid rooms based on area and shape
        """
        rooms = []
        
        logger.info(f"Filtering {len(polygons)} polygons with scale factor: {scale_factor}")
        
        for idx, polygon in enumerate(polygons):
            if len(polygon) < 3:
                continue
            
            # Calculate polygon area in pixels
            area_pixels = self.calculate_polygon_area(polygon)
            
            # Calculate room properties
            centroid = self.calculate_centroid(polygon)
            bbox = self.calculate_bounding_box(polygon)
            
            # Convert to feet if scale factor available
            if scale_factor and scale_factor > 0:
                area_sqft = area_pixels / (scale_factor ** 2)
                width_ft = (bbox[2] - bbox[0]) / scale_factor
                height_ft = (bbox[3] - bbox[1]) / scale_factor
                
                # Use scale-aware thresholds
                min_area = self.MIN_ROOM_AREA_SQFT
                max_area = self.MAX_ROOM_AREA_SQFT
                
                # Skip if area is outside reasonable room size range
                if area_sqft < min_area or area_sqft > max_area:
                    logger.debug(f"Polygon {idx} filtered: area {area_sqft:.1f} sq ft outside range {min_area}-{max_area} sq ft")
                    continue
                    
            else:
                # No scale - use pixel-based filtering
                if area_pixels < self.MIN_ROOM_AREA or area_pixels > self.MAX_ROOM_AREA:
                    logger.debug(f"Polygon {idx} filtered: area {area_pixels:.0f} pixels outside range")
                    continue
                    
                # Rough estimates when scale unknown
                area_sqft = area_pixels / 100
                width_ft = (bbox[2] - bbox[0]) / 10
                height_ft = (bbox[3] - bbox[1]) / 10
            
            rooms.append({
                'polygon': polygon,
                'area_pixels': area_pixels,
                'area_sqft': area_sqft,
                'centroid': centroid,
                'bounding_box': bbox,
                'width_ft': width_ft,
                'height_ft': height_ft,
                'vertex_count': len(polygon),
                'detection_method': 'polygon_from_walls',
                'confidence': 0.8  # High confidence for wall-based detection
            })
        
        return rooms
    
    def calculate_polygon_area(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate area of polygon using shoelace formula"""
        if len(polygon) < 3:
            return 0
        
        area = 0
        n = len(polygon)
        
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        
        return abs(area) / 2
    
    def calculate_centroid(self, polygon: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate centroid of polygon"""
        if not polygon:
            return (0, 0)
        
        cx = sum(p[0] for p in polygon) / len(polygon)
        cy = sum(p[1] for p in polygon) / len(polygon)
        
        return (cx, cy)
    
    def calculate_bounding_box(self, polygon: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """Calculate bounding box of polygon"""
        if not polygon:
            return (0, 0, 0, 0)
        
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        
        return (min(xs), min(ys), max(xs), max(ys))
    
    def line_to_line_distance(self, line1: Dict, line2: Dict) -> float:
        """Calculate minimum distance between two line segments"""
        # Simplified - just use endpoint distances
        distances = [
            np.sqrt((line1['x0'] - line2['x0'])**2 + (line1['y0'] - line2['y0'])**2),
            np.sqrt((line1['x0'] - line2['x1'])**2 + (line1['y0'] - line2['y1'])**2),
            np.sqrt((line1['x1'] - line2['x0'])**2 + (line1['y1'] - line2['y0'])**2),
            np.sqrt((line1['x1'] - line2['x1'])**2 + (line1['y1'] - line2['y1'])**2)
        ]
        
        return min(distances)
    
    def order_polygon_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Order polygon points consistently (clockwise)"""
        if len(points) < 3:
            return points
        
        # Find centroid
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        
        # Sort by angle from centroid
        def angle_from_centroid(point):
            return np.arctan2(point[1] - cy, point[0] - cx)
        
        return sorted(points, key=angle_from_centroid)
    
    def is_duplicate_polygon(
        self, 
        polygon: List[Tuple[float, float]], 
        existing: List[List[Tuple[float, float]]]
    ) -> bool:
        """Check if polygon already exists in list"""
        polygon_set = set(polygon)
        
        for existing_polygon in existing:
            if len(polygon) != len(existing_polygon):
                continue
            
            existing_set = set(existing_polygon)
            if polygon_set == existing_set:
                return True
        
        return False
    
    def save_debug_artifacts(
        self,
        walls: List[Dict],
        polygons: List[List[Tuple]],
        rooms: List[Dict],
        page_width: float,
        page_height: float
    ):
        """
        Save debug visualization showing detected walls, polygons, and rooms
        """
        try:
            # Create blank image
            img = np.ones((int(page_height), int(page_width), 3), dtype=np.uint8) * 255
            
            # Draw walls in red
            for wall in walls:
                cv2.line(
                    img,
                    (int(wall['x0']), int(wall['y0'])),
                    (int(wall['x1']), int(wall['y1'])),
                    (0, 0, 255),  # Red
                    max(1, int(wall['width']))
                )
            
            # Draw all polygons in blue
            for polygon in polygons:
                pts = np.array([(int(p[0]), int(p[1])) for p in polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, (255, 0, 0), 2)  # Blue
            
            # Draw valid rooms in green
            for room in rooms:
                polygon = room['polygon']
                pts = np.array([(int(p[0]), int(p[1])) for p in polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.fillPoly(img, [pts], (0, 255, 0))  # Green fill
                cv2.polylines(img, [pts], True, (0, 128, 0), 3)  # Dark green border
                
                # Add room info text
                cx, cy = room['centroid']
                text = f"{room['area_sqft']:.0f} sqft"
                cv2.putText(
                    img, text,
                    (int(cx - 30), int(cy)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 0), 2
                )
            
            # Log that debug image was generated (actual saving would be to S3)
            logger.info(f"Debug visualization generated: {len(walls)} walls, {len(polygons)} polygons, {len(rooms)} rooms")
            
        except Exception as e:
            logger.error(f"Failed to generate debug artifacts: {e}")


# Global instance
polygon_detector = PolygonRoomDetector()