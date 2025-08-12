"""
Vector-First PDF Extractor
Extracts vector paths, text, and dimensions directly from PDF
Only falls back to OCR when content is rasterized
"""

import logging
import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VectorPath:
    """A vector path from the PDF"""
    points: List[Tuple[float, float]]
    is_closed: bool
    stroke_width: float
    color: str
    path_type: str  # 'line', 'rect', 'curve'
    

@dataclass
class VectorText:
    """Text element from the PDF"""
    text: str
    position: Tuple[float, float]
    font_size: float
    font_name: str
    rotation: float
    

@dataclass
class DimensionLabel:
    """A dimension label extracted from the PDF"""
    text: str
    value_ft: float
    position: Tuple[float, float]
    confidence: float
    

@dataclass
class VectorData:
    """Complete vector data from a PDF page"""
    paths: List[VectorPath]
    texts: List[VectorText]
    dimensions: List[DimensionLabel]
    page_width: float
    page_height: float
    has_vector_content: bool
    has_raster_content: bool


class VectorExtractor:
    """
    Extracts vector content directly from PDF
    This is much more accurate than OCR for vector PDFs
    """
    
    # Dimension patterns (imperial)
    DIMENSION_PATTERNS = [
        r"(\d+)'\s*-?\s*(\d+)(?:\s*(\d+)/(\d+))?\"?",  # 10'-6" or 10' 6 3/4"
        r"(\d+)'-(\d+)\"",  # 10'-6"
        r"(\d+)'",  # 10'
        r"(\d+)\"",  # 6"
        r"(\d+)\s*ft",  # 10 ft
        r"(\d+)\s*feet",  # 10 feet
    ]
    
    def __init__(self):
        self.min_path_length = 10  # Minimum path length in points
        self.dimension_keywords = ['dim', 'length', 'width', 'height', 'depth']
        
    def extract_vectors(self, pdf_path: str, page_num: int = 0) -> VectorData:
        """
        Extract all vector content from a PDF page
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            VectorData with all extracted content
        """
        logger.info(f"Extracting vectors from page {page_num + 1} of {pdf_path}")
        
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Extract all components
        paths = self._extract_paths(page)
        texts = self._extract_texts(page)
        dimensions = self._extract_dimensions(texts)
        
        # Check content types
        has_vector = len(paths) > 0 or len(texts) > 0
        has_raster = self._has_raster_content(page)
        
        vector_data = VectorData(
            paths=paths,
            texts=texts,
            dimensions=dimensions,
            page_width=page.rect.width,
            page_height=page.rect.height,
            has_vector_content=has_vector,
            has_raster_content=has_raster
        )
        
        doc.close()
        
        logger.info(f"Extracted {len(paths)} paths, {len(texts)} texts, {len(dimensions)} dimensions")
        logger.info(f"Content types - Vector: {has_vector}, Raster: {has_raster}")
        
        return vector_data
    
    def _extract_paths(self, page: fitz.Page) -> List[VectorPath]:
        """Extract vector paths from the page"""
        paths = []
        
        # Get page drawings
        drawings = page.get_drawings()
        
        for drawing in drawings:
            # Extract path items
            for item in drawing.get("items", []):
                if item[0] == "l":  # Line
                    p1, p2 = item[1], item[2]
                    paths.append(VectorPath(
                        points=[p1, p2],
                        is_closed=False,
                        stroke_width=drawing.get("width", 1.0),
                        color=self._color_to_hex(drawing.get("color")),
                        path_type="line"
                    ))
                elif item[0] == "re":  # Rectangle
                    rect = item[1]
                    points = [
                        (rect.x0, rect.y0),
                        (rect.x1, rect.y0),
                        (rect.x1, rect.y1),
                        (rect.x0, rect.y1)
                    ]
                    paths.append(VectorPath(
                        points=points,
                        is_closed=True,
                        stroke_width=drawing.get("width", 1.0),
                        color=self._color_to_hex(drawing.get("color")),
                        path_type="rect"
                    ))
                elif item[0] == "c":  # Curve
                    # Bezier curve - store control points
                    points = [item[1], item[2], item[3], item[4]]
                    paths.append(VectorPath(
                        points=points,
                        is_closed=False,
                        stroke_width=drawing.get("width", 1.0),
                        color=self._color_to_hex(drawing.get("color")),
                        path_type="curve"
                    ))
        
        # Filter out very small paths
        paths = [p for p in paths if self._calculate_path_length(p) > self.min_path_length]
        
        return paths
    
    def _extract_texts(self, page: fitz.Page) -> List[VectorText]:
        """Extract text elements from the page"""
        texts = []
        
        # Get text with detailed information
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            texts.append(VectorText(
                                text=text,
                                position=(span["bbox"][0], span["bbox"][1]),
                                font_size=span.get("size", 0),
                                font_name=span.get("font", ""),
                                rotation=span.get("rotation", 0)
                            ))
        
        return texts
    
    def _extract_dimensions(self, texts: List[VectorText]) -> List[DimensionLabel]:
        """Extract dimension labels from text elements"""
        dimensions = []
        
        for text_elem in texts:
            # Try to parse as dimension
            for pattern in self.DIMENSION_PATTERNS:
                match = re.search(pattern, text_elem.text)
                if match:
                    try:
                        value_ft = self._parse_dimension_to_feet(match)
                        if value_ft > 0:
                            dimensions.append(DimensionLabel(
                                text=text_elem.text,
                                value_ft=value_ft,
                                position=text_elem.position,
                                confidence=0.95  # High confidence for vector text
                            ))
                            break
                    except:
                        continue
        
        return dimensions
    
    def _parse_dimension_to_feet(self, match) -> float:
        """Parse dimension match to feet"""
        groups = match.groups()
        
        if len(groups) >= 4 and groups[2] and groups[3]:
            # Format: feet-inches fraction (e.g., 10'-6 3/4")
            feet = float(groups[0])
            inches = float(groups[1])
            fraction = float(groups[2]) / float(groups[3])
            return feet + (inches + fraction) / 12.0
        elif len(groups) >= 2 and groups[1]:
            # Format: feet-inches (e.g., 10'-6")
            feet = float(groups[0])
            inches = float(groups[1])
            return feet + inches / 12.0
        elif "'" in match.group() or "ft" in match.group().lower() or "feet" in match.group().lower():
            # Format: feet only
            return float(groups[0])
        elif '"' in match.group():
            # Format: inches only
            return float(groups[0]) / 12.0
        
        return 0
    
    def _has_raster_content(self, page: fitz.Page) -> bool:
        """Check if page has raster/image content"""
        # Check for embedded images
        image_list = page.get_images()
        return len(image_list) > 0
    
    def _calculate_path_length(self, path: VectorPath) -> float:
        """Calculate the length of a path"""
        if len(path.points) < 2:
            return 0
        
        length = 0
        for i in range(len(path.points) - 1):
            p1, p2 = path.points[i], path.points[i + 1]
            length += np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        return length
    
    def _color_to_hex(self, color) -> str:
        """Convert color to hex string"""
        if not color:
            return "#000000"
        
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            r = int(color[0] * 255)
            g = int(color[1] * 255)
            b = int(color[2] * 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        
        return "#000000"
    
    def find_parallel_edges(self, paths: List[VectorPath], tolerance: float = 5.0) -> List[Tuple[VectorPath, VectorPath]]:
        """
        Find parallel edges for scale detection
        
        Args:
            paths: List of vector paths
            tolerance: Angle tolerance in degrees
            
        Returns:
            List of parallel path pairs
        """
        parallel_pairs = []
        
        for i, path1 in enumerate(paths):
            if path1.path_type != "line" or len(path1.points) != 2:
                continue
                
            angle1 = self._calculate_angle(path1.points[0], path1.points[1])
            
            for j, path2 in enumerate(paths[i+1:], i+1):
                if path2.path_type != "line" or len(path2.points) != 2:
                    continue
                
                angle2 = self._calculate_angle(path2.points[0], path2.points[1])
                
                # Check if parallel (same angle or 180° different)
                angle_diff = abs(angle1 - angle2) % 180
                if angle_diff < tolerance or angle_diff > (180 - tolerance):
                    parallel_pairs.append((path1, path2))
        
        return parallel_pairs
    
    def _calculate_angle(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate angle of a line in degrees"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return np.degrees(np.arctan2(dy, dx)) % 360
    
    def cluster_dimensions_to_edges(
        self, 
        dimensions: List[DimensionLabel],
        paths: List[VectorPath],
        max_distance: float = 50
    ) -> List[Tuple[DimensionLabel, VectorPath]]:
        """
        Cluster dimension labels to their nearest edges
        
        Args:
            dimensions: List of dimension labels
            paths: List of vector paths
            max_distance: Maximum distance to associate dimension with edge
            
        Returns:
            List of (dimension, path) pairs
        """
        pairs = []
        
        for dim in dimensions:
            min_dist = float('inf')
            nearest_path = None
            
            for path in paths:
                if path.path_type != "line":
                    continue
                
                # Calculate distance from dimension to line
                dist = self._point_to_line_distance(
                    dim.position,
                    path.points[0],
                    path.points[1]
                )
                
                if dist < min_dist and dist < max_distance:
                    min_dist = dist
                    nearest_path = path
            
            if nearest_path:
                pairs.append((dim, nearest_path))
        
        return pairs
    
    def _point_to_line_distance(
        self,
        point: Tuple[float, float],
        line_p1: Tuple[float, float],
        line_p2: Tuple[float, float]
    ) -> float:
        """Calculate distance from point to line segment"""
        # Vector from p1 to p2
        line_vec = np.array(line_p2) - np.array(line_p1)
        # Vector from p1 to point
        point_vec = np.array(point) - np.array(line_p1)
        
        # Project point onto line
        line_len = np.linalg.norm(line_vec)
        if line_len == 0:
            return np.linalg.norm(point_vec)
        
        line_unitvec = line_vec / line_len
        proj_length = np.dot(point_vec, line_unitvec)
        
        # Clamp to line segment
        proj_length = max(0.0, min(line_len, proj_length))
        
        # Calculate nearest point on line
        nearest = np.array(line_p1) + line_unitvec * proj_length
        
        # Return distance
        return np.linalg.norm(np.array(point) - nearest)


# Singleton instance
_vector_extractor = None

def get_vector_extractor() -> VectorExtractor:
    """Get or create the global vector extractor"""
    global _vector_extractor
    if _vector_extractor is None:
        _vector_extractor = VectorExtractor()
    return _vector_extractor