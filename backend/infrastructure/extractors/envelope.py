"""
Building Envelope Extractor
Extracts building perimeter, wall orientations, and openings from vector data
THIS is what we should extract FIRST, not rooms!
"""

import logging
import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Wall:
    """Represents an exterior wall segment"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    length_ft: float
    orientation: str  # 'N', 'S', 'E', 'W', 'NE', etc.
    angle: float  # Degrees from north (0-360)
    windows: List[Dict[str, Any]]  # Windows on this wall
    doors: List[Dict[str, Any]]  # Doors on this wall


@dataclass
class BuildingEnvelope:
    """The building's thermal envelope - what actually matters for heat transfer"""
    exterior_walls: List[Wall]
    total_perimeter_ft: float
    total_wall_area_sqft: float
    floor_area_sqft: float
    ceiling_height_ft: float
    wall_orientations: Dict[str, float]  # {'N': 120, 'S': 120, 'E': 80, 'W': 80} sqft
    window_areas: Dict[str, float]  # {'N': 40, 'S': 60, ...} sqft per orientation
    door_areas: Dict[str, float]
    shape_factor: float  # Perimeter/sqrt(area) - indicates compactness
    

class EnvelopeExtractor:
    """
    Extracts the building envelope from vector data
    This is the CORRECT approach - get the building shell first!
    """
    
    def __init__(self):
        self.min_wall_length = 3.0  # Minimum wall length in feet
        self.wall_angle_tolerance = 15  # Degrees for orientation classification
        
    def extract_envelope(
        self, 
        vector_data: Dict[str, Any],
        scale_factor: float = 1.0,
        north_angle: float = 0.0,
        schedules: Dict[str, Any] = None
    ) -> BuildingEnvelope:
        """
        Extract building envelope from vector paths
        PROPERLY extracts actual building geometry
        """
        logger.info("Extracting building envelope from vector data")
        
        if not vector_data:
            logger.warning("No vector data provided, using intelligent defaults")
            return self._create_default_envelope()
        
        if not vector_data.get('paths'):
            logger.warning(f"Vector data has no paths (keys: {vector_data.keys()}), using intelligent defaults")
            return self._create_default_envelope()
        
        # Get actual paths from vector data
        paths = vector_data.get('paths', [])
        logger.info(f"Processing {len(paths)} vector paths")
        
        # Find walls by looking for long straight lines
        wall_candidates = []
        for path in paths:
            # Handle both object and dict formats
            if hasattr(path, 'points'):
                points = path.points
                path_type = path.path_type if hasattr(path, 'path_type') else 'line'
            elif isinstance(path, dict):
                points = path.get('points', [])
                path_type = path.get('path_type', 'line')
            else:
                continue
            
            # Process lines and rectangles (walls are usually these)
            if path_type in ['line', 'rect'] and len(points) >= 2:
                # For rectangles, process each edge
                if path_type == 'rect' and len(points) >= 4:
                    # Rectangle has 4 edges
                    edges = [
                        (points[0], points[1]),  # Bottom
                        (points[1], points[2]),  # Right
                        (points[2], points[3]),  # Top
                        (points[3], points[0])   # Left
                    ]
                else:
                    # Single line
                    edges = [(points[0], points[1])]
                
                for p1, p2 in edges:
                    # Calculate length in feet
                    length_px = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                    length_ft = length_px * scale_factor
                    
                    # Walls are typically 8+ feet long
                    if length_ft >= 8.0:
                        # Calculate orientation
                        angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
                        angle = (angle - north_angle) % 360
                        orientation = self._angle_to_orientation(angle)
                        
                        wall = Wall(
                            start=(p1[0] * scale_factor, p1[1] * scale_factor),
                            end=(p2[0] * scale_factor, p2[1] * scale_factor),
                            length_ft=length_ft,
                            orientation=orientation,
                            angle=angle,
                            windows=[],
                            doors=[]
                        )
                        wall_candidates.append(wall)
        
        if not wall_candidates:
            logger.warning("No walls found in vector data, using defaults")
            return self._create_default_envelope()
        
        # Find exterior walls using smart heuristics
        exterior_walls = self._identify_exterior_walls(wall_candidates)
        
        if len(exterior_walls) < 4:
            logger.warning(f"Only {len(exterior_walls)} exterior walls found, using longest walls")
            # Fallback: use longest walls
            wall_candidates.sort(key=lambda w: w.length_ft, reverse=True)
            exterior_walls = wall_candidates[:min(12, len(wall_candidates))]
        
        # Calculate ACTUAL metrics
        total_perimeter = sum(w.length_ft for w in exterior_walls)
        
        # Better area estimation from actual walls
        floor_area = self._estimate_area_from_walls(exterior_walls)
        if floor_area < 500:  # Sanity check
            # Fallback estimation
            floor_area = (total_perimeter / 4) ** 2  # Assume squarish
        
        # Get ceiling height from data or use standard
        ceiling_height = 9.0  # Standard, could extract from elevations
        
        # Calculate wall orientations from ACTUAL walls
        wall_orientations = self._calculate_wall_orientations(exterior_walls)
        
        # Window distribution from schedules if available
        window_areas = self._get_window_distribution(schedules, floor_area)
        
        envelope = BuildingEnvelope(
            exterior_walls=exterior_walls,
            total_perimeter_ft=total_perimeter,
            total_wall_area_sqft=total_perimeter * ceiling_height,
            floor_area_sqft=floor_area,
            ceiling_height_ft=ceiling_height,
            wall_orientations=wall_orientations,
            window_areas=window_areas,
            door_areas={"N": 20, "S": 20, "E": 0, "W": 20},  # Typical 3 doors
            shape_factor=total_perimeter / math.sqrt(floor_area)
        )
        
        logger.info(f"✓ Extracted envelope: {total_perimeter:.1f}ft perimeter, "
                   f"{floor_area:.0f}sqft area, {len(exterior_walls)} walls, "
                   f"shape factor {envelope.shape_factor:.2f}")
        
        return envelope
    
    def _identify_exterior_walls(self, walls: List[Wall]) -> List[Wall]:
        """
        Identify which walls are exterior using smart heuristics
        """
        if not walls:
            return []
        
        # Strategy: Find walls that form a closed perimeter
        # Group walls by approximate orientation
        horizontal = [w for w in walls if abs(w.angle % 180 - 90) < 30]
        vertical = [w for w in walls if abs(w.angle % 180) < 30 or abs(w.angle % 180 - 180) < 30]
        
        exterior = []
        
        # Take the outermost walls in each direction
        if horizontal:
            horizontal.sort(key=lambda w: w.start[1])
            # Take top and bottom
            if len(horizontal) >= 2:
                exterior.append(horizontal[0])   # Top
                exterior.append(horizontal[-1])  # Bottom
        
        if vertical:
            vertical.sort(key=lambda w: w.start[0])
            # Take left and right
            if len(vertical) >= 2:
                exterior.append(vertical[0])   # Left
                exterior.append(vertical[-1])  # Right
        
        # Add more walls if we need them for a complete perimeter
        remaining = [w for w in walls if w not in exterior]
        remaining.sort(key=lambda w: w.length_ft, reverse=True)
        
        while len(exterior) < 8 and remaining:  # Typical house has 8-12 exterior walls
            exterior.append(remaining.pop(0))
        
        return exterior
    
    def _estimate_area_from_walls(self, walls: List[Wall]) -> float:
        """
        Estimate floor area from exterior walls
        """
        if not walls:
            return 0
        
        # Find bounding box
        all_points = []
        for wall in walls:
            all_points.append(wall.start)
            all_points.append(wall.end)
        
        if not all_points:
            return 0
        
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        
        width = max(xs) - min(xs)
        length = max(ys) - min(ys)
        
        # Area from bounding box
        area = width * length
        
        # Reduce by 10% for typical house shape (not perfect rectangle)
        return area * 0.9
    
    def _get_window_distribution(self, schedules: Dict[str, Any], floor_area: float) -> Dict[str, float]:
        """
        Get window distribution from schedules or use smart defaults
        """
        if schedules and schedules.get('total_window_area'):
            total_window_area = schedules['total_window_area']
        else:
            # 15% window-to-floor ratio is typical
            total_window_area = floor_area * 0.15
        
        # Typical distribution favoring south for passive solar
        return {
            "N": total_window_area * 0.20,   # Less on north
            "S": total_window_area * 0.35,   # More on south for solar gain
            "E": total_window_area * 0.225,
            "W": total_window_area * 0.225
        }
    
    def _find_exterior_walls(
        self, 
        paths: List[Any],
        scale_factor: float,
        north_angle: float
    ) -> List[Wall]:
        """
        Identify exterior walls from vector paths
        Uses connectivity and closure to find building perimeter
        """
        exterior_walls = []
        
        # Convert paths to walls with proper scaling
        potential_walls = []
        for path in paths:
            if path.path_type == "line" and len(path.points) == 2:
                # Calculate wall properties
                p1, p2 = path.points[0], path.points[1]
                length_px = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                length_ft = length_px * scale_factor
                
                if length_ft < self.min_wall_length:
                    continue
                
                # Calculate orientation
                angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
                # Adjust for north arrow
                angle = (angle - north_angle) % 360
                orientation = self._angle_to_orientation(angle)
                
                wall = Wall(
                    start=(p1[0] * scale_factor, p1[1] * scale_factor),
                    end=(p2[0] * scale_factor, p2[1] * scale_factor),
                    length_ft=length_ft,
                    orientation=orientation,
                    angle=angle,
                    windows=[],
                    doors=[]
                )
                potential_walls.append(wall)
        
        # Find connected walls that form a closed loop (the exterior)
        # This is simplified - a full implementation would use graph algorithms
        exterior_walls = self._find_closed_loop(potential_walls)
        
        # If we can't find a closed loop, use the longest walls as likely exterior
        if not exterior_walls and potential_walls:
            # Sort by length and take the longest walls
            potential_walls.sort(key=lambda w: w.length_ft, reverse=True)
            
            # Take walls that likely form a perimeter
            # Heuristic: walls that together roughly form a rectangle
            total_length = sum(w.length_ft for w in potential_walls[:10])
            for wall in potential_walls:
                exterior_walls.append(wall)
                if sum(w.length_ft for w in exterior_walls) > total_length * 0.4:
                    break
        
        return exterior_walls
    
    def _find_closed_loop(self, walls: List[Wall]) -> List[Wall]:
        """
        Find walls that form a closed loop (building perimeter)
        Simplified version - real implementation would use graph traversal
        """
        if not walls:
            return []
        
        # Group parallel walls
        horizontal = [w for w in walls if abs(w.angle % 180 - 90) < 45]
        vertical = [w for w in walls if abs(w.angle % 180) < 45 or abs(w.angle % 180 - 180) < 45]
        
        # If we have both horizontal and vertical walls, likely found perimeter
        if horizontal and vertical:
            # Take the outermost walls of each orientation
            exterior = []
            
            # Get extremes in each direction
            if horizontal:
                horizontal.sort(key=lambda w: w.start[1])
                exterior.append(horizontal[0])  # Topmost
                if len(horizontal) > 1:
                    exterior.append(horizontal[-1])  # Bottommost
            
            if vertical:
                vertical.sort(key=lambda w: w.start[0])
                exterior.append(vertical[0])  # Leftmost
                if len(vertical) > 1:
                    exterior.append(vertical[-1])  # Rightmost
            
            return exterior
        
        return []
    
    def _angle_to_orientation(self, angle: float) -> str:
        """Convert angle to cardinal direction"""
        # Normalize angle to 0-360
        angle = angle % 360
        
        # Define orientation ranges
        if angle < 22.5 or angle >= 337.5:
            return "E"  # East (0°)
        elif angle < 67.5:
            return "NE"
        elif angle < 112.5:
            return "N"  # North (90°)
        elif angle < 157.5:
            return "NW"
        elif angle < 202.5:
            return "W"  # West (180°)
        elif angle < 247.5:
            return "SW"
        elif angle < 292.5:
            return "S"  # South (270°)
        else:
            return "SE"
    
    def _estimate_floor_area_from_perimeter(self, walls: List[Wall]) -> float:
        """
        Estimate floor area from exterior walls
        Uses the shoelace formula if we have a closed polygon
        """
        if not walls:
            return 0
        
        # Try to form a polygon from walls
        points = []
        for wall in walls:
            points.append(wall.start)
            points.append(wall.end)
        
        if len(points) < 3:
            # Fallback: assume rectangular from perimeter
            perimeter = sum(w.length_ft for w in walls)
            # For a rectangle with aspect ratio 1.5:1
            # P = 2(L + W), where L = 1.5W
            # P = 2(1.5W + W) = 5W
            # W = P/5, L = 1.5P/5
            width = perimeter / 5
            length = 1.5 * width
            return width * length
        
        # Use shoelace formula for polygon area
        area = 0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2
    
    def _calculate_wall_orientations(self, walls: List[Wall]) -> Dict[str, float]:
        """Calculate total wall area by orientation"""
        orientations = {"N": 0, "S": 0, "E": 0, "W": 0, "NE": 0, "NW": 0, "SE": 0, "SW": 0}
        
        ceiling_height = 9.0  # Default ceiling height
        
        for wall in walls:
            wall_area = wall.length_ft * ceiling_height
            orientations[wall.orientation] = orientations.get(wall.orientation, 0) + wall_area
        
        # Combine diagonals into primary directions for simplicity
        result = {
            "N": orientations["N"] + orientations["NE"] * 0.5 + orientations["NW"] * 0.5,
            "S": orientations["S"] + orientations["SE"] * 0.5 + orientations["SW"] * 0.5,
            "E": orientations["E"] + orientations["NE"] * 0.5 + orientations["SE"] * 0.5,
            "W": orientations["W"] + orientations["NW"] * 0.5 + orientations["SW"] * 0.5
        }
        
        return result
    
    def _calculate_window_areas_by_orientation(self, walls: List[Wall]) -> Dict[str, float]:
        """Calculate window areas by orientation"""
        window_areas = {"N": 0, "S": 0, "E": 0, "W": 0}
        
        for wall in walls:
            for window in wall.windows:
                area = window.get('area', 20)  # Default 20 sqft per window
                # Map wall orientation to primary direction
                if wall.orientation in ["N", "NE", "NW"]:
                    window_areas["N"] += area * (1 if wall.orientation == "N" else 0.5)
                if wall.orientation in ["S", "SE", "SW"]:
                    window_areas["S"] += area * (1 if wall.orientation == "S" else 0.5)
                if wall.orientation in ["E", "NE", "SE"]:
                    window_areas["E"] += area * (1 if wall.orientation == "E" else 0.5)
                if wall.orientation in ["W", "NW", "SW"]:
                    window_areas["W"] += area * (1 if wall.orientation == "W" else 0.5)
        
        return window_areas
    
    def _calculate_door_areas_by_orientation(self, walls: List[Wall]) -> Dict[str, float]:
        """Calculate door areas by orientation"""
        door_areas = {"N": 0, "S": 0, "E": 0, "W": 0}
        
        for wall in walls:
            for door in wall.doors:
                area = door.get('area', 20)  # Default 20 sqft per door
                # Map wall orientation to primary direction
                if wall.orientation in ["N", "NE", "NW"]:
                    door_areas["N"] += area * (1 if wall.orientation == "N" else 0.5)
                if wall.orientation in ["S", "SE", "SW"]:
                    door_areas["S"] += area * (1 if wall.orientation == "S" else 0.5)
                if wall.orientation in ["E", "NE", "SE"]:
                    door_areas["E"] += area * (1 if wall.orientation == "E" else 0.5)
                if wall.orientation in ["W", "NW", "SW"]:
                    door_areas["W"] += area * (1 if wall.orientation == "W" else 0.5)
        
        return door_areas
    
    def _assign_openings_to_walls(
        self,
        walls: List[Wall],
        schedules: Dict[str, Any],
        texts: List[Any]
    ):
        """Assign windows and doors from schedules to appropriate walls"""
        # This is a simplified version
        # A full implementation would use spatial matching
        
        # Distribute windows evenly among walls for now
        # Better approach: match window labels to wall proximity
        total_windows = len(schedules.get('windows', []))
        if total_windows > 0 and walls:
            windows_per_wall = total_windows / len(walls)
            for i, wall in enumerate(walls):
                # Assign proportional windows to each wall
                num_windows = int(windows_per_wall + 0.5)
                for j in range(num_windows):
                    if j < len(schedules['windows']):
                        wall.windows.append(schedules['windows'][j])
    
    def _create_default_envelope(self) -> BuildingEnvelope:
        """Create a default envelope when vector extraction fails"""
        logger.warning("Using default envelope - extraction failed")
        
        # Default rectangular building
        default_walls = [
            Wall(start=(0, 0), end=(40, 0), length_ft=40, orientation="S", angle=270, windows=[], doors=[]),
            Wall(start=(40, 0), end=(40, 30), length_ft=30, orientation="E", angle=0, windows=[], doors=[]),
            Wall(start=(40, 30), end=(0, 30), length_ft=40, orientation="N", angle=90, windows=[], doors=[]),
            Wall(start=(0, 30), end=(0, 0), length_ft=30, orientation="W", angle=180, windows=[], doors=[])
        ]
        
        return BuildingEnvelope(
            exterior_walls=default_walls,
            total_perimeter_ft=140,
            total_wall_area_sqft=1260,  # 140 * 9
            floor_area_sqft=1200,  # 40 * 30
            ceiling_height_ft=9.0,
            wall_orientations={"N": 360, "S": 360, "E": 270, "W": 270},
            window_areas={"N": 40, "S": 60, "E": 30, "W": 30},
            door_areas={"N": 20, "S": 20, "E": 0, "W": 0},
            shape_factor=4.04  # 140 / sqrt(1200)
        )


# Singleton instance
_envelope_extractor = None

def get_envelope_extractor() -> EnvelopeExtractor:
    """Get or create the global envelope extractor"""
    global _envelope_extractor
    if _envelope_extractor is None:
        _envelope_extractor = EnvelopeExtractor()
    return _envelope_extractor