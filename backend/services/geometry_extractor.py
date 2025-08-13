"""
Geometry Extractor - Deterministic room polygon extraction
Single responsibility: Extract room boundaries and calculate areas
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Any
import fitz  # PyMuPDF
import cv2

logger = logging.getLogger(__name__)


class GeometryExtractor:
    """
    Extract room geometry from blueprints using deterministic methods
    No AI, just pure geometric analysis
    """
    
    def __init__(self, scale_px_per_ft: float):
        """
        Initialize with scale factor
        
        Args:
            scale_px_per_ft: Pixels per foot conversion factor
        """
        self.scale_px_per_ft = scale_px_per_ft
        self.min_room_area_sqft = 20  # Minimum room size
        self.max_room_area_sqft = 2000  # Maximum room size
        
    def extract_rooms(
        self,
        pdf_path: str,
        page_num: int
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[float, float]]]:
        """
        Extract room polygons from a PDF page
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            Tuple of (rooms list, building footprint polygon)
        """
        logger.info(f"Extracting geometry from page {page_num + 1}")
        
        # Render page to image
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()
        
        # Convert to OpenCV format
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(img_data))
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Extract walls (black lines)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours (potential room boundaries)
        # Use RETR_TREE to find ALL contours including interior rooms
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        rooms = []
        all_points = []
        
        # Process contours, but skip ones that have a parent (to avoid duplicates)
        for i, contour in enumerate(contours):
            # Skip if this contour has a parent (hierarchy[0][i][3] != -1)
            if hierarchy is not None and hierarchy[0][i][3] != -1:
                continue
            # Calculate area in pixels
            area_px = cv2.contourArea(contour)
            
            # Convert to square feet (accounting for 2x zoom)
            area_sqft = area_px / (self.scale_px_per_ft * 2) ** 2
            
            # Filter by size
            if self.min_room_area_sqft <= area_sqft <= self.max_room_area_sqft:
                # Simplify polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) >= 3:  # Valid polygon
                    # Convert points to feet
                    polygon = []
                    for point in approx:
                        x_ft = point[0][0] / (self.scale_px_per_ft * 2)
                        y_ft = point[0][1] / (self.scale_px_per_ft * 2)
                        polygon.append((x_ft, y_ft))
                        all_points.append((x_ft, y_ft))
                    
                    # Calculate properties
                    center = self._calculate_centroid(polygon)
                    perimeter = self._calculate_perimeter(polygon)
                    bbox = self._calculate_bbox(polygon)
                    
                    rooms.append({
                        'polygon': polygon,
                        'area': area_sqft,
                        'perimeter': perimeter,
                        'center': center,
                        'bbox': bbox
                    })
        
        # Calculate building footprint (convex hull of all points)
        if all_points:
            hull_points = self._convex_hull(all_points)
            building_footprint = hull_points
        else:
            # Fallback: use page bounds
            w_ft = img_cv.shape[1] / (self.scale_px_per_ft * 2)
            h_ft = img_cv.shape[0] / (self.scale_px_per_ft * 2)
            building_footprint = [(0, 0), (w_ft, 0), (w_ft, h_ft), (0, h_ft)]
        
        logger.info(f"Extracted {len(rooms)} rooms")
        
        # If no rooms found, create a single room from largest contour
        if not rooms and contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area_px = cv2.contourArea(largest_contour)
            area_sqft = area_px / (self.scale_px_per_ft * 2) ** 2
            
            # Create simplified polygon
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            polygon = []
            for point in approx[:10]:  # Limit points
                x_ft = point[0][0] / (self.scale_px_per_ft * 2)
                y_ft = point[0][1] / (self.scale_px_per_ft * 2)
                polygon.append((x_ft, y_ft))
            
            if len(polygon) >= 3:
                rooms.append({
                    'polygon': polygon,
                    'area': max(area_sqft, 100),  # Minimum 100 sqft
                    'perimeter': self._calculate_perimeter(polygon),
                    'center': self._calculate_centroid(polygon),
                    'bbox': self._calculate_bbox(polygon)
                })
        
        # Ensure at least one room
        if not rooms:
            logger.warning("No rooms detected, creating default room")
            rooms.append({
                'polygon': [(0, 0), (20, 0), (20, 15), (0, 15)],
                'area': 300,
                'perimeter': 70,
                'center': (10, 7.5),
                'bbox': (0, 0, 20, 15)
            })
        
        return rooms, building_footprint
    
    def calculate_perimeter(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate perimeter of a polygon"""
        return self._calculate_perimeter(polygon)
    
    def _calculate_centroid(self, polygon: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate centroid of a polygon"""
        if not polygon:
            return (0, 0)
        
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        return (sum(x_coords) / len(polygon), sum(y_coords) / len(polygon))
    
    def _calculate_perimeter(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate perimeter of a polygon"""
        if len(polygon) < 2:
            return 0
        
        perimeter = 0
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            distance = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) ** 0.5
            perimeter += distance
        
        return perimeter
    
    def _calculate_bbox(
        self,
        polygon: List[Tuple[float, float]]
    ) -> Tuple[float, float, float, float]:
        """Calculate bounding box of a polygon"""
        if not polygon:
            return (0, 0, 0, 0)
        
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
    
    def _convex_hull(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Calculate convex hull of points"""
        if len(points) < 3:
            return points
        
        # Convert to numpy array for OpenCV
        np_points = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        hull = cv2.convexHull(np_points)
        
        # Convert back to list of tuples
        return [(float(p[0][0]), float(p[0][1])) for p in hull]
    
    def detect_exterior_exposure(
        self,
        room_polygon: List[Tuple[float, float]],
        building_hull: List[Tuple[float, float]],
        tolerance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Count exterior edges by intersecting room edges with building perimeter
        
        Args:
            room_polygon: Room boundary points
            building_hull: Building perimeter points
            tolerance: Distance tolerance for edge matching (feet)
            
        Returns:
            Dictionary with exterior wall info and orientation distribution
        """
        if not room_polygon or not building_hull:
            return {
                'exterior_wall_count': 0,
                'corner_room': False,
                'exterior_wall_length': 0,
                'orientation_distribution': {},
                'exterior_percentage': 0
            }
        
        exterior_edges = []
        total_perimeter = 0
        
        # Check each edge of the room polygon
        for i in range(len(room_polygon)):
            p1 = room_polygon[i]
            p2 = room_polygon[(i + 1) % len(room_polygon)]
            
            edge_length = self._distance(p1, p2)
            total_perimeter += edge_length
            
            # Check if edge is close to hull
            if self._edge_near_hull(p1, p2, building_hull, tolerance):
                orientation = self._compute_edge_orientation(p1, p2)
                exterior_edges.append({
                    'start': p1,
                    'end': p2,
                    'length': edge_length,
                    'orientation': orientation
                })
        
        # Calculate orientation distribution by edge length
        orientation_distribution = {}
        total_exterior_length = sum(e['length'] for e in exterior_edges)
        
        if total_exterior_length > 0:
            for edge in exterior_edges:
                orient = edge['orientation']
                proportion = edge['length'] / total_exterior_length
                orientation_distribution[orient] = orientation_distribution.get(orient, 0) + proportion
        
        return {
            'exterior_wall_count': len(exterior_edges),
            'corner_room': len(exterior_edges) >= 2,
            'exterior_wall_length': total_exterior_length,
            'orientation_distribution': orientation_distribution,
            'exterior_percentage': total_exterior_length / total_perimeter if total_perimeter > 0 else 0,
            'exterior_edges': exterior_edges
        }
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points"""
        return ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) ** 0.5
    
    def _edge_near_hull(
        self,
        edge_start: Tuple[float, float],
        edge_end: Tuple[float, float],
        hull: List[Tuple[float, float]],
        tolerance: float
    ) -> bool:
        """Check if an edge is within tolerance of the hull"""
        # Check if either endpoint is close to hull
        for hull_idx in range(len(hull)):
            hull_p1 = hull[hull_idx]
            hull_p2 = hull[(hull_idx + 1) % len(hull)]
            
            # Check distance from edge to hull segment
            dist = self._segment_to_segment_distance(
                edge_start, edge_end,
                hull_p1, hull_p2
            )
            
            if dist < tolerance:
                return True
        
        return False
    
    def _segment_to_segment_distance(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> float:
        """Calculate minimum distance between two line segments"""
        # Simplified - check endpoint distances
        distances = [
            self._distance(p1, p3),
            self._distance(p1, p4),
            self._distance(p2, p3),
            self._distance(p2, p4)
        ]
        return min(distances)
    
    def _compute_edge_orientation(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> str:
        """Compute cardinal orientation of an edge"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Calculate angle in degrees (0 = East, 90 = North)
        import math
        angle = math.degrees(math.atan2(dy, dx))
        
        # Normalize to 0-360
        if angle < 0:
            angle += 360
        
        # Map to cardinal directions
        if 337.5 <= angle or angle < 22.5:
            return 'E'
        elif 22.5 <= angle < 67.5:
            return 'NE'
        elif 67.5 <= angle < 112.5:
            return 'N'
        elif 112.5 <= angle < 157.5:
            return 'NW'
        elif 157.5 <= angle < 202.5:
            return 'W'
        elif 202.5 <= angle < 247.5:
            return 'SW'
        elif 247.5 <= angle < 292.5:
            return 'S'
        else:  # 292.5 <= angle < 337.5
            return 'SE'