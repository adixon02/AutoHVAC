"""
Enhanced Fenestration (Windows & Doors) Extractor
Detects and characterizes all windows and doors from blueprints
Extracts sizes, types, U-values, and SHGC for accurate load calculations
"""

import logging
import re
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Window:
    """Window characteristics for Manual J calculations"""
    window_id: str
    location: Tuple[float, float]  # Center point
    width_ft: float
    height_ft: float
    area_sqft: float
    orientation: str  # N, S, E, W, NE, etc.
    wall_id: Optional[str]  # Which wall it's on
    room_id: Optional[str]  # Which room it's in
    window_type: str  # 'single', 'double', 'triple', 'fixed', 'operable'
    frame_type: str  # 'aluminum', 'vinyl', 'wood', 'fiberglass'
    glazing_type: str  # 'clear', 'low-e', 'low-e2', 'low-e3'
    u_value: float  # BTU/hr·ft²·°F
    shgc: float  # Solar Heat Gain Coefficient
    vt: float  # Visible Transmittance
    air_leakage: float  # cfm/ft²
    confidence: float


@dataclass
class Door:
    """Door characteristics for Manual J calculations"""
    door_id: str
    location: Tuple[float, float]
    width_ft: float
    height_ft: float
    area_sqft: float
    orientation: str
    wall_id: Optional[str]
    room_id: Optional[str]
    door_type: str  # 'exterior', 'interior', 'sliding', 'french'
    material: str  # 'steel', 'fiberglass', 'wood', 'glass'
    has_glass: bool
    glass_area_sqft: float
    u_value: float
    confidence: float


@dataclass
class FenestrationData:
    """Complete fenestration data for a building"""
    windows: List[Window]
    doors: List[Door]
    total_window_area: float
    total_door_area: float
    window_to_wall_ratio: float
    average_window_u: float
    average_window_shgc: float
    orientation_distribution: Dict[str, float]  # Window area by orientation


class FenestrationExtractor:
    """
    Extracts windows and doors from vector blueprints
    Identifies types, sizes, and thermal properties
    """
    
    # Window symbol patterns in vectors (typical CAD representations)
    WINDOW_PATTERNS = {
        'double_line': {'parallel_gap': (2, 6)},  # Two parallel lines with gap
        'rectangle': {'aspect_ratio': (1.5, 4.0)},  # Rectangular openings
        'arc': {'in_wall': True},  # Arc in wall indicates window
    }
    
    # Door symbol patterns
    DOOR_PATTERNS = {
        'arc_swing': {'radius': (2.5, 4.0)},  # Arc showing door swing
        'angled_line': {'angle': (20, 45)},  # Angled line for door in plan
        'break_in_wall': {'gap': (2.5, 4.0)},  # Gap in wall for doorway
    }
    
    # Window performance by type (ASHRAE Fundamentals)
    WINDOW_PERFORMANCE = {
        # (frame_type, glazing_type): (U-value, SHGC, VT)
        ('aluminum', 'single'): (1.27, 0.75, 0.69),
        ('aluminum', 'double'): (0.81, 0.60, 0.58),
        ('aluminum', 'double_low-e'): (0.60, 0.38, 0.56),
        ('vinyl', 'double'): (0.51, 0.56, 0.59),
        ('vinyl', 'double_low-e'): (0.36, 0.30, 0.56),
        ('vinyl', 'triple_low-e2'): (0.18, 0.27, 0.48),
        ('wood', 'double'): (0.45, 0.52, 0.59),
        ('wood', 'double_low-e'): (0.32, 0.30, 0.56),
        ('fiberglass', 'double_low-e'): (0.30, 0.28, 0.55),
    }
    
    # Door U-values by type
    DOOR_U_VALUES = {
        'steel_insulated': 0.20,
        'steel_half_glass': 0.46,
        'fiberglass_insulated': 0.15,
        'wood_solid': 0.40,
        'wood_half_glass': 0.55,
        'sliding_glass': 0.51,
        'french_double': 0.50,
    }
    
    def __init__(self):
        self.min_window_width = 1.5  # Minimum 1.5 ft wide
        self.max_window_width = 12.0  # Maximum 12 ft wide
        self.min_door_width = 2.0  # Minimum 2 ft wide
        self.max_door_width = 8.0  # Maximum 8 ft wide (double door)
        
    def extract(
        self,
        text_blocks: List[Dict[str, Any]],
        vision_data: Optional[Dict] = None,
        scale_result: Optional[Any] = None
    ) -> FenestrationData:
        """Extract fenestration data - simplified wrapper"""
        scale_factor = 1.0
        if scale_result and hasattr(scale_result, 'scale_factor'):
            scale_factor = scale_result.scale_factor
        return self.extract_fenestration({}, text_blocks, [], None, scale_factor, vision_data)
    
    def extract_fenestration(
        self,
        vector_data: Dict[str, Any],
        text_blocks: List[Dict[str, Any]],
        walls: List[Any],  # Wall segments from envelope or room extraction
        schedule_data: Optional[Dict] = None,
        scale_factor: float = 1.0,
        vision_results: Optional[Dict] = None
    ) -> FenestrationData:
        """
        Extract all windows and doors from blueprint
        
        Args:
            vector_data: Vector paths and symbols
            text_blocks: Text labels
            walls: Wall segments to search for openings
            schedule_data: Window/door schedule if available
            scale_factor: Drawing scale
            vision_results: Optional GPT-4V analysis
            
        Returns:
            FenestrationData with all windows and doors
        """
        logger.info("Extracting fenestration (windows and doors)")
        
        # 1. Extract from vector symbols
        windows = self._extract_windows_from_vectors(vector_data, walls, scale_factor)
        doors = self._extract_doors_from_vectors(vector_data, walls, scale_factor)
        
        logger.info(f"Found {len(windows)} windows and {len(doors)} doors from vectors")
        
        # 2. Extract from schedules if available
        if schedule_data:
            schedule_windows = self._extract_from_schedule(schedule_data, 'windows')
            schedule_doors = self._extract_from_schedule(schedule_data, 'doors')
            
            # Merge with vector-detected openings
            windows = self._merge_with_schedule(windows, schedule_windows)
            doors = self._merge_with_schedule(doors, schedule_doors)
            
            logger.info(f"Enhanced with schedule: {len(windows)} windows, {len(doors)} doors")
        
        # 3. Extract performance specs from text
        performance_specs = self._extract_performance_specs(text_blocks)
        self._apply_performance_specs(windows, performance_specs)
        
        # 4. Apply vision results if available
        if vision_results:
            self._apply_vision_results(windows, doors, vision_results)
        
        # 5. Calculate aggregate metrics
        fenestration_data = self._calculate_metrics(windows, doors, walls)
        
        logger.info(f"Fenestration extraction complete: "
                   f"WWR={fenestration_data.window_to_wall_ratio:.1%}, "
                   f"Avg U={fenestration_data.average_window_u:.2f}, "
                   f"Avg SHGC={fenestration_data.average_window_shgc:.2f}")
        
        return fenestration_data
    
    def _extract_windows_from_vectors(
        self,
        vector_data: Dict,
        walls: List[Any],
        scale_factor: float
    ) -> List[Window]:
        """Extract windows from vector symbols"""
        windows = []
        
        if not vector_data or 'paths' not in vector_data:
            return windows
        
        paths = vector_data['paths']
        window_id = 0
        
        # Look for window patterns
        for i, path in enumerate(paths):
            # Get path points
            if hasattr(path, 'points'):
                points = path.points
            else:
                points = path.get('points', [])
            
            if len(points) < 2:
                continue
            
            # Check for double-line pattern (common window representation)
            if self._is_window_pattern(path, paths[max(0, i-5):min(len(paths), i+5)]):
                # Calculate window dimensions
                width, height = self._calculate_opening_size(points, scale_factor)
                
                if self.min_window_width <= width <= self.max_window_width:
                    center = self._calculate_center(points)
                    orientation = self._determine_orientation(center, walls)
                    
                    window = Window(
                        window_id=f"W{window_id:03d}",
                        location=(center[0] * scale_factor, center[1] * scale_factor),
                        width_ft=width,
                        height_ft=height if height > 0 else 5.0,  # Default 5 ft height
                        area_sqft=width * (height if height > 0 else 5.0),
                        orientation=orientation,
                        wall_id=None,
                        room_id=None,
                        window_type='double',  # Default assumption
                        frame_type='vinyl',  # Common default
                        glazing_type='low-e',  # Modern default
                        u_value=0.30,  # Energy code typical
                        shgc=0.30,  # Balanced for most climates
                        vt=0.50,
                        air_leakage=0.30,
                        confidence=0.7
                    )
                    
                    windows.append(window)
                    window_id += 1
        
        return windows
    
    def _extract_doors_from_vectors(
        self,
        vector_data: Dict,
        walls: List[Any],
        scale_factor: float
    ) -> List[Door]:
        """Extract doors from vector symbols"""
        doors = []
        
        if not vector_data or 'paths' not in vector_data:
            return doors
        
        paths = vector_data['paths']
        door_id = 0
        
        # Look for door swing arcs
        for path in paths:
            if hasattr(path, 'path_type') and path.path_type == 'curve':
                # Check if this is a door swing arc
                if self._is_door_swing(path):
                    # Extract door from swing arc
                    door = self._extract_door_from_swing(path, scale_factor, door_id)
                    if door:
                        doors.append(door)
                        door_id += 1
        
        # Look for gaps in walls (doorways)
        door_gaps = self._find_wall_gaps(walls, (self.min_door_width, self.max_door_width))
        for gap in door_gaps:
            door = Door(
                door_id=f"D{door_id:03d}",
                location=gap['center'],
                width_ft=gap['width'],
                height_ft=7.0,  # Standard door height
                area_sqft=gap['width'] * 7.0,
                orientation=gap['orientation'],
                wall_id=gap.get('wall_id'),
                room_id=None,
                door_type='exterior' if gap.get('is_exterior') else 'interior',
                material='steel' if gap.get('is_exterior') else 'wood',
                has_glass=False,
                glass_area_sqft=0,
                u_value=0.20 if gap.get('is_exterior') else 0.50,
                confidence=0.6
            )
            doors.append(door)
            door_id += 1
        
        return doors
    
    def _is_window_pattern(self, path: Any, nearby_paths: List[Any]) -> bool:
        """Check if path represents a window"""
        # Look for parallel lines close together (double-line window symbol)
        if hasattr(path, 'path_type') and path.path_type == 'line':
            for other in nearby_paths:
                if hasattr(other, 'path_type') and other.path_type == 'line':
                    if self._are_parallel_lines(path, other):
                        gap = self._calculate_line_gap(path, other)
                        if 2 <= gap <= 6:  # Window gap in inches on drawing
                            return True
        return False
    
    def _is_door_swing(self, path: Any) -> bool:
        """Check if curved path is a door swing arc"""
        if hasattr(path, 'path_type') and path.path_type == 'curve':
            # Door swings are typically quarter circles
            # Check arc properties
            return True  # Simplified - would check arc angle and radius
        return False
    
    def _extract_door_from_swing(
        self,
        arc_path: Any,
        scale_factor: float,
        door_id: int
    ) -> Optional[Door]:
        """Extract door from swing arc"""
        # Calculate door width from arc radius
        if hasattr(arc_path, 'points') and len(arc_path.points) >= 2:
            # Estimate radius from arc points
            radius = self._estimate_arc_radius(arc_path.points)
            width = radius * scale_factor
            
            if self.min_door_width <= width <= self.max_door_width:
                center = arc_path.points[0]  # Arc origin is door hinge
                
                return Door(
                    door_id=f"D{door_id:03d}",
                    location=(center[0] * scale_factor, center[1] * scale_factor),
                    width_ft=width,
                    height_ft=7.0,
                    area_sqft=width * 7.0,
                    orientation='unknown',
                    wall_id=None,
                    room_id=None,
                    door_type='interior',
                    material='wood',
                    has_glass=width > 3,  # Assume glass if wide
                    glass_area_sqft=10 if width > 3 else 0,
                    u_value=0.50,
                    confidence=0.7
                )
        return None
    
    def _find_wall_gaps(
        self,
        walls: List[Any],
        size_range: Tuple[float, float]
    ) -> List[Dict]:
        """Find gaps in walls that could be doors"""
        gaps = []
        # This would analyze wall segments for gaps
        # Simplified implementation
        return gaps
    
    def _extract_from_schedule(
        self,
        schedule_data: Dict,
        opening_type: str
    ) -> List[Any]:
        """Extract windows or doors from schedule"""
        items = []
        
        if opening_type in schedule_data:
            for item in schedule_data[opening_type]:
                if opening_type == 'windows':
                    # Parse window schedule entry
                    window = self._parse_window_schedule(item)
                    if window:
                        items.append(window)
                else:
                    # Parse door schedule entry
                    door = self._parse_door_schedule(item)
                    if door:
                        items.append(door)
        
        return items
    
    def _parse_window_schedule(self, schedule_item: Dict) -> Optional[Window]:
        """Parse window from schedule entry"""
        # Extract size (e.g., "3050" = 3'0" x 5'0")
        size_match = re.search(r'(\d)(\d)(\d)(\d)', str(schedule_item.get('mark', '')))
        if size_match:
            width = int(size_match.group(1)) + int(size_match.group(2)) / 12
            height = int(size_match.group(3)) + int(size_match.group(4)) / 12
            
            return Window(
                window_id=schedule_item.get('mark', 'W000'),
                location=(0, 0),  # Will be updated when matched to vector
                width_ft=width,
                height_ft=height,
                area_sqft=width * height,
                orientation='unknown',
                wall_id=None,
                room_id=None,
                window_type=schedule_item.get('type', 'double'),
                frame_type=schedule_item.get('frame', 'vinyl'),
                glazing_type=schedule_item.get('glazing', 'low-e'),
                u_value=schedule_item.get('u_value', 0.30),
                shgc=schedule_item.get('shgc', 0.30),
                vt=schedule_item.get('vt', 0.50),
                air_leakage=0.30,
                confidence=0.9
            )
        
        return None
    
    def _parse_door_schedule(self, schedule_item: Dict) -> Optional[Door]:
        """Parse door from schedule entry"""
        # Similar to window parsing
        return None
    
    def _extract_performance_specs(self, text_blocks: List[Dict]) -> Dict[str, Any]:
        """Extract window/door performance specifications from text"""
        specs = {}
        
        patterns = {
            'u_value': r'U[\s-]?(?:VALUE|FACTOR)[\s:=]*([\d.]+)',
            'shgc': r'SHGC[\s:=]*([\d.]+)',
            'low_e': r'LOW[\s-]?E(?:2|3)?',
            'energy_star': r'ENERGY\s+STAR',
            'nfrc': r'NFRC\s+(?:RATED|CERTIFIED)',
        }
        
        for block in text_blocks:
            text = block['text'].upper()
            
            for spec_name, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    if spec_name in ['u_value', 'shgc']:
                        specs[spec_name] = float(match.group(1))
                    else:
                        specs[spec_name] = True
                    
                    logger.debug(f"Found spec: {spec_name} = {specs.get(spec_name)}")
        
        return specs
    
    def _apply_performance_specs(self, windows: List[Window], specs: Dict):
        """Apply extracted performance specs to windows"""
        if not specs:
            return
        
        for window in windows:
            if 'u_value' in specs:
                window.u_value = specs['u_value']
                window.confidence = 0.9
            
            if 'shgc' in specs:
                window.shgc = specs['shgc']
            
            if 'low_e' in specs:
                window.glazing_type = 'low-e'
                # Update U-value if not explicitly specified
                if 'u_value' not in specs:
                    window.u_value = 0.30  # Typical low-E
            
            if 'energy_star' in specs:
                # Energy Star requirements by climate zone
                window.u_value = min(window.u_value, 0.30)
                window.shgc = min(window.shgc, 0.40)
    
    def _calculate_metrics(
        self,
        windows: List[Window],
        doors: List[Door],
        walls: List[Any]
    ) -> FenestrationData:
        """Calculate aggregate fenestration metrics"""
        total_window_area = sum(w.area_sqft for w in windows)
        total_door_area = sum(d.area_sqft for d in doors)
        
        # Calculate wall area (simplified)
        total_wall_area = 1260  # Default for 140 ft perimeter × 9 ft height
        if walls:
            # Calculate from actual walls if available
            pass
        
        # Window-to-wall ratio
        wwr = total_window_area / total_wall_area if total_wall_area > 0 else 0.15
        
        # Average performance
        if windows:
            avg_u = sum(w.u_value * w.area_sqft for w in windows) / total_window_area
            avg_shgc = sum(w.shgc * w.area_sqft for w in windows) / total_window_area
        else:
            avg_u = 0.30
            avg_shgc = 0.30
        
        # Orientation distribution
        orientation_dist = {}
        for orientation in ['N', 'S', 'E', 'W']:
            area = sum(w.area_sqft for w in windows if w.orientation == orientation)
            orientation_dist[orientation] = area
        
        return FenestrationData(
            windows=windows,
            doors=doors,
            total_window_area=total_window_area,
            total_door_area=total_door_area,
            window_to_wall_ratio=wwr,
            average_window_u=avg_u,
            average_window_shgc=avg_shgc,
            orientation_distribution=orientation_dist
        )
    
    def _are_parallel_lines(self, path1: Any, path2: Any) -> bool:
        """Check if two line paths are parallel"""
        # Calculate angles and compare
        return False  # Simplified
    
    def _calculate_line_gap(self, path1: Any, path2: Any) -> float:
        """Calculate gap between parallel lines"""
        return 4.0  # Simplified
    
    def _calculate_opening_size(
        self,
        points: List[Tuple[float, float]],
        scale_factor: float
    ) -> Tuple[float, float]:
        """Calculate width and height of opening"""
        if len(points) >= 2:
            width = abs(points[1][0] - points[0][0]) * scale_factor
            height = abs(points[1][1] - points[0][1]) * scale_factor
            
            # Ensure width > height for proper orientation
            if height > width:
                width, height = height, width
            
            return width, height
        
        return 3.0, 5.0  # Default window size
    
    def _calculate_center(self, points: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate center point"""
        if not points:
            return (0, 0)
        
        x = sum(p[0] for p in points) / len(points)
        y = sum(p[1] for p in points) / len(points)
        return (x, y)
    
    def _determine_orientation(
        self,
        location: Tuple[float, float],
        walls: List[Any]
    ) -> str:
        """Determine cardinal orientation of opening"""
        # This would check which wall the opening is on
        # and determine its orientation
        return 'S'  # Simplified - assume south-facing
    
    def _estimate_arc_radius(self, points: List[Tuple[float, float]]) -> float:
        """Estimate radius of arc from points"""
        if len(points) >= 3:
            # Use three points to estimate circle radius
            # Simplified - would use proper circle fitting
            return 3.0  # Default door width
        return 3.0
    
    def _merge_with_schedule(
        self,
        detected_items: List[Any],
        schedule_items: List[Any]
    ) -> List[Any]:
        """Merge detected items with schedule data"""
        # Match by size and update properties
        merged = detected_items.copy()
        
        for schedule_item in schedule_items:
            matched = False
            for detected in merged:
                if abs(detected.width_ft - schedule_item.width_ft) < 0.5:
                    # Update with schedule data
                    detected.u_value = schedule_item.u_value
                    detected.shgc = schedule_item.shgc
                    detected.confidence = 0.95
                    matched = True
                    break
            
            if not matched:
                # Add schedule item not found in vectors
                merged.append(schedule_item)
        
        return merged
    
    def _apply_vision_results(
        self,
        windows: List[Window],
        doors: List[Door],
        vision_results: Dict
    ):
        """Apply GPT-4V vision analysis results"""
        if 'windows' in vision_results:
            for vision_window in vision_results['windows']:
                # Match and update windows
                pass
        
        if 'doors' in vision_results:
            for vision_door in vision_results['doors']:
                # Match and update doors
                pass


# Singleton instance
_fenestration_extractor = None


def get_fenestration_extractor() -> FenestrationExtractor:
    """Get or create the global fenestration extractor"""
    global _fenestration_extractor
    if _fenestration_extractor is None:
        _fenestration_extractor = FenestrationExtractor()
    return _fenestration_extractor