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
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rooms = []
        all_points = []
        
        for contour in contours:
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