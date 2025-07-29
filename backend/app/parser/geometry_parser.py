"""
Elite geometry parser for architectural PDFs
Extracts walls, rooms, and duct outlines using pdfplumber + PyMuPDF
"""

import pdfplumber
import fitz  # PyMuPDF
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import re
from .schema import RawGeometry


class GeometryParser:
    """Advanced PDF geometry extraction for HVAC blueprints"""
    
    def __init__(self):
        self.scale_patterns = [
            r'1"?\s*=\s*(\d+)\'?-?(\d+)?"?',  # 1" = 20'-0"
            r'(\d+)\s*:\s*(\d+)',              # 1:240
            r'SCALE\s*[:\-]\s*(.+)',           # SCALE: 1/4" = 1'-0"
        ]
    
    def parse(self, pdf_path: str) -> RawGeometry:
        """
        Extract comprehensive geometry from architectural PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            RawGeometry with all extracted elements
        """
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # Process first page
            
            # Extract basic page info
            page_width = float(page.width)
            page_height = float(page.height)
            
            # Detect scale
            scale_factor = self._detect_scale(page)
            
            # Extract geometry elements
            lines = self._extract_lines(page)
            rectangles = self._extract_rectangles(page)
            polylines = self._extract_polylines_pymupdf(pdf_path)
            
            return RawGeometry(
                page_width=page_width,
                page_height=page_height,
                scale_factor=scale_factor,
                lines=lines,
                rectangles=rectangles,
                polylines=polylines
            )
    
    def _detect_scale(self, page) -> Optional[float]:
        """Detect scale markers in the blueprint"""
        words = page.extract_words()
        text = ' '.join([w['text'] for w in words])
        
        for pattern in self.scale_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Parse scale ratio (simplified)
                    if ':' in match.group():
                        parts = match.group().split(':')
                        return float(parts[1]) / float(parts[0])
                    else:
                        # Parse architectural scale like 1/4" = 1'-0"
                        return 48.0  # Default to 1/4" scale
                except:
                    continue
        
        return None
    
    def _extract_lines(self, page) -> List[Dict[str, Any]]:
        """Extract line segments (walls, dimensions)"""
        lines = []
        raw_lines = page.lines
        
        for line in raw_lines:
            x0, y0, x1, y1 = line['x0'], line['y0'], line['x1'], line['y1']
            length = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
            
            # Classify line type
            line_type = self._classify_line(line, length)
            
            lines.append({
                'type': 'line',
                'coords': [float(x0), float(y0), float(x1), float(y1)],
                'x0': float(x0),
                'y0': float(y0),
                'x1': float(x1),
                'y1': float(y1),
                'width': float(line.get('width', 1.0)),
                'length': float(length),
                'line_type': line_type,
                'orientation': self._get_orientation(x0, y0, x1, y1),
                'wall_probability': self._calculate_wall_probability(line, length)
            })
        
        return self._group_parallel_lines(lines)
    
    def _extract_rectangles(self, page) -> List[Dict[str, Any]]:
        """Extract rectangles (likely rooms)"""
        rectangles = []
        raw_rects = page.rects
        
        for rect in raw_rects:
            width = float(rect['x1'] - rect['x0'])
            height = float(rect['y1'] - rect['y0'])
            area = width * height
            
            # Filter meaningful rectangles
            if area > 500:  # Minimum room size
                rectangles.append({
                    'type': 'rect',
                    'coords': [float(rect['x0']), float(rect['y0']), float(rect['x1']), float(rect['y1'])],
                    'x0': float(rect['x0']),
                    'y0': float(rect['y0']),
                    'x1': float(rect['x1']),
                    'y1': float(rect['y1']),
                    'width': width,
                    'height': height,
                    'area': area,
                    'center_x': float(rect['x0'] + width / 2),
                    'center_y': float(rect['y0'] + height / 2),
                    'aspect_ratio': width / height if height > 0 else 0,
                    'room_probability': self._calculate_room_probability(width, height, area)
                })
        
        return sorted(rectangles, key=lambda r: r['area'], reverse=True)
    
    def _extract_polylines_pymupdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract polylines and complex paths using PyMuPDF"""
        polylines = []
        
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Get all drawing paths
            drawings = page.get_drawings()
            
            for drawing in drawings:
                if drawing and 'items' in drawing and len(drawing['items']) > 2:
                    # Extract path points
                    points = []
                    for item in drawing['items']:
                        if item and len(item) >= 3:  # Has coordinates
                            # Safely extract coordinates with null checks
                            try:
                                x, y = item[1], item[2]
                                if x is not None and y is not None:
                                    points.extend([float(x), float(y)])
                            except (TypeError, ValueError, IndexError):
                                continue  # Skip invalid coordinates
                    
                    if len(points) >= 6:  # At least 3 points
                        try:
                            stroke_width = float(drawing.get('width', 1.0)) if drawing.get('width') is not None else 1.0
                            color = drawing.get('stroke', {}).get('color', 0) if drawing.get('stroke') else 0
                            closed = bool(drawing.get('closePath', False))
                            
                            polylines.append({
                                'points': points,
                                'stroke_width': stroke_width,
                                'color': color,
                                'closed': closed,
                                'duct_probability': self._calculate_duct_probability(points, drawing)
                            })
                        except (TypeError, ValueError) as e:
                            print(f"Error processing drawing properties: {e}")
                            continue
            
            doc.close()
            
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        return polylines
    
    def _classify_line(self, line: Dict, length: float) -> str:
        """Classify line as wall, dimension, or other"""
        width = float(line.get('width', 1.0))
        
        if width > 2.0 and length > 50:
            return 'wall'
        elif length > 100 and width < 1.5:
            return 'dimension'
        else:
            return 'other'
    
    def _get_orientation(self, x0: float, y0: float, x1: float, y1: float) -> str:
        """Get line orientation"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        if dx < 2:
            return 'vertical'
        elif dy < 2:
            return 'horizontal'
        else:
            angle = np.arctan2(dy, dx) * 180 / np.pi
            if 22.5 <= angle <= 67.5:
                return 'diagonal'
            else:
                return 'horizontal' if dx > dy else 'vertical'
    
    def _calculate_wall_probability(self, line: Dict, length: float) -> float:
        """Calculate probability that line represents a wall"""
        width = float(line.get('width', 1.0))
        
        # Longer, thicker lines are more likely walls
        length_score = min(length / 200, 1.0)
        width_score = min(width / 3.0, 1.0)
        
        return (length_score + width_score) / 2
    
    def _calculate_room_probability(self, width: float, height: float, area: float) -> float:
        """Calculate probability that rectangle is a room"""
        # Reasonable room proportions
        aspect_ratio = width / height if height > 0 else 0
        aspect_score = 1.0 - abs(aspect_ratio - 1.5) / 3.0  # Prefer ~1.5:1 ratio
        aspect_score = max(0, min(1, aspect_score))
        
        # Reasonable room size
        area_score = 1.0 if 100 <= area <= 10000 else 0.5
        
        return (aspect_score + area_score) / 2
    
    def _calculate_duct_probability(self, points: List[float], drawing: Dict) -> float:
        """Calculate probability that polyline is ductwork"""
        # Ductwork is typically thin, curved paths
        width = drawing.get('width', 1.0)
        
        if width < 2.0 and len(points) > 6:
            return 0.8
        return 0.2
    
    def _group_parallel_lines(self, lines: List[Dict]) -> List[Dict]:
        """Group parallel lines that might form walls"""
        # Simple implementation - could be enhanced with clustering
        grouped = []
        
        for line in lines:
            # Find nearby parallel lines
            parallel_count = 0
            for other in lines:
                if (line != other and 
                    line['orientation'] == other['orientation'] and
                    self._lines_parallel(line, other)):
                    parallel_count += 1
            
            line['parallel_count'] = parallel_count
            grouped.append(line)
        
        return grouped
    
    def _lines_parallel(self, line1: Dict, line2: Dict, tolerance: float = 10.0) -> bool:
        """Check if two lines are parallel and nearby"""
        # Simplified parallel check based on distance
        dist1 = np.sqrt((line1['x0'] - line2['x0'])**2 + (line1['y0'] - line2['y0'])**2)
        dist2 = np.sqrt((line1['x1'] - line2['x1'])**2 + (line1['y1'] - line2['y1'])**2)
        
        return min(dist1, dist2) < tolerance