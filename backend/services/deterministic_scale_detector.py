"""
Deterministic Scale Detection for Architectural Blueprints
Implements multiple corroborating methods to ensure accurate scale detection
"""

import re
import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ScaleEstimate:
    """Individual scale estimate from a specific method"""
    pixels_per_foot: float
    confidence: float
    method: str  # 'title_block', 'dimension', 'door_width', 'grid_bubble', etc.
    evidence: str  # What was found/measured
    location: Optional[Tuple[float, float]] = None  # (x, y) if applicable


@dataclass 
class ScaleResult:
    """Final scale determination with multiple corroborating estimates"""
    pixels_per_foot: float
    scale_notation: str  # e.g., "1/4\"=1'"
    confidence: float
    estimates: List[ScaleEstimate] = field(default_factory=list)
    corroborations: int = 0
    tolerance_percent: float = 0.0
    needs_override: bool = False
    recommendation: Optional[str] = None


class DeterministicScaleDetector:
    """
    Deterministic scale detection using multiple validation methods.
    Never uses AI/Vision for measurements - only OCR and geometry.
    """
    
    # Common architectural scales
    STANDARD_SCALES = {
        "1\"=1'": 12.0,      # 1 inch = 1 foot (rare)
        "3/4\"=1'": 18.0,    # 3/4 inch = 1 foot
        "1/2\"=1'": 24.0,    # 1/2 inch = 1 foot
        "3/8\"=1'": 32.0,    # 3/8 inch = 1 foot
        "1/4\"=1'": 48.0,    # 1/4 inch = 1 foot (MOST COMMON)
        "3/16\"=1'": 64.0,   # 3/16 inch = 1 foot
        "1/8\"=1'": 96.0,    # 1/8 inch = 1 foot (large buildings)
        "3/32\"=1'": 128.0,  # 3/32 inch = 1 foot
        "1/16\"=1'": 192.0,  # 1/16 inch = 1 foot (site plans)
    }
    
    # Typical object dimensions for validation
    KNOWN_OBJECTS = {
        'door_width': (2.5, 3.0),      # Standard door: 2'6" to 3'0"
        'door_height': (6.67, 7.0),    # Standard door: 6'8" to 7'0"
        'hallway_width': (3.0, 6.0),   # Hallways: 3' to 6'
        'stair_width': (3.0, 4.0),     # Stairs: 3' to 4'
        'toilet_width': (2.5, 3.5),    # Toilet room: 2'6" to 3'6"
        'grid_spacing': (10.0, 30.0),  # Structural grid: 10' to 30'
    }
    
    def detect_scale(
        self,
        ocr_text: str,
        dimensions: List[Dict[str, Any]],
        geometric_elements: List[Dict[str, Any]],
        page_size: Tuple[float, float],
        override: Optional[float] = None
    ) -> ScaleResult:
        """
        Detect scale using multiple deterministic methods.
        
        Args:
            ocr_text: Full OCR text from the page
            dimensions: List of parsed dimension annotations
            geometric_elements: List of geometric elements (lines, rects, etc.)
            page_size: (width, height) in pixels
            override: User-provided scale override (if any)
            
        Returns:
            ScaleResult with confidence and corroborating estimates
        """
        estimates = []
        
        # Check for user override first
        if override:
            logger.info(f"Using user-provided scale override: {override} px/ft")
            return self._create_result_from_override(override)
        
        # Method 1: Title block OCR
        title_block_scale = self._extract_from_title_block(ocr_text)
        if title_block_scale:
            estimates.append(title_block_scale)
            logger.info(f"Title block scale: {title_block_scale.pixels_per_foot} px/ft "
                       f"({title_block_scale.evidence})")
        
        # Method 2: Dimension text parsing
        dimension_scales = self._extract_from_dimensions(dimensions, geometric_elements)
        estimates.extend(dimension_scales)
        for ds in dimension_scales:
            logger.info(f"Dimension scale: {ds.pixels_per_foot} px/ft ({ds.evidence})")
        
        # Method 3: Known object measurements
        object_scales = self._extract_from_objects(geometric_elements)
        estimates.extend(object_scales)
        for os in object_scales:
            logger.info(f"Object scale: {os.pixels_per_foot} px/ft ({os.evidence})")
        
        # Method 4: Grid analysis (if grid lines present)
        grid_scale = self._extract_from_grid(geometric_elements)
        if grid_scale:
            estimates.append(grid_scale)
            logger.info(f"Grid scale: {grid_scale.pixels_per_foot} px/ft ({grid_scale.evidence})")
        
        # Consolidate estimates and find consensus
        result = self._consolidate_estimates(estimates)
        
        # Check if we need user input
        if result.corroborations < 2 or result.confidence < 0.7:
            result.needs_override = True
            result.recommendation = self._generate_recommendation(estimates, page_size)
            logger.warning(f"Scale detection uncertain. Recommendation: {result.recommendation}")
        
        return result
    
    def _extract_from_title_block(self, ocr_text: str) -> Optional[ScaleEstimate]:
        """Extract scale from title block text using regex patterns."""
        if not ocr_text:
            return None
        
        text = ocr_text.upper()
        
        # Comprehensive regex patterns for scale notation
        patterns = [
            # SCALE: 1/4" = 1'-0"
            (r'SCALE[:\s]+(\d+)/(\d+)["\']\s*=\s*1[\'"\-](?:0["\'])?', 
             lambda m: f"{m.group(1)}/{m.group(2)}\"=1'"),
            # SCALE: 1/4 INCH = 1 FOOT
            (r'SCALE[:\s]+(\d+)/(\d+)\s*INCH(?:ES)?\s*=\s*1\s*FOOT',
             lambda m: f"{m.group(1)}/{m.group(2)}\"=1'"),
            # Simple: 1/4"=1'
            (r'(?:^|\s)(\d+)/(\d+)["\']\s*=\s*1[\'"\-]',
             lambda m: f"{m.group(1)}/{m.group(2)}\"=1'"),
            # Metric: SCALE 1:48
            (r'SCALE[:\s]+1:(\d+)', 
             lambda m: self._metric_to_imperial(int(m.group(1)))),
            # SCALE = 1/4
            (r'SCALE[:\s]*=?\s*(\d+)/(\d+)',
             lambda m: f"{m.group(1)}/{m.group(2)}\"=1'"),
        ]
        
        for pattern, formatter in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    notation = formatter(match)
                    if notation in self.STANDARD_SCALES:
                        return ScaleEstimate(
                            pixels_per_foot=self.STANDARD_SCALES[notation],
                            confidence=0.95 if "SCALE" in match.group() else 0.85,
                            method='title_block',
                            evidence=f"Found '{match.group()}' in title block"
                        )
                except Exception as e:
                    logger.debug(f"Failed to parse scale match: {e}")
        
        return None
    
    def _extract_from_dimensions(
        self, 
        dimensions: List[Dict[str, Any]], 
        geometric_elements: List[Dict[str, Any]]
    ) -> List[ScaleEstimate]:
        """
        Extract scale by comparing dimension text to measured distances.
        E.g., if "12'-0"" text is anchored to lines 576 pixels apart, scale = 576/12 = 48 px/ft
        """
        estimates = []
        
        for dim in dimensions:
            if not dim.get('value') or not dim.get('anchor_points'):
                continue
            
            # Parse dimension value (e.g., "12'-6"" -> 12.5 feet)
            feet_value = self._parse_dimension_text(dim['value'])
            if not feet_value or feet_value < 2 or feet_value > 100:
                continue  # Skip unreasonable dimensions
            
            # Find the distance between anchor points
            anchors = dim['anchor_points']
            if len(anchors) >= 2:
                x1, y1 = anchors[0]
                x2, y2 = anchors[-1]
                pixel_distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                if pixel_distance > 50:  # Minimum pixel distance for accuracy
                    scale = pixel_distance / feet_value
                    
                    # Check if this matches a standard scale (within 5%)
                    for notation, standard_scale in self.STANDARD_SCALES.items():
                        if abs(scale - standard_scale) / standard_scale < 0.05:
                            estimates.append(ScaleEstimate(
                                pixels_per_foot=scale,
                                confidence=0.9,
                                method='dimension',
                                evidence=f"Dimension '{dim['value']}' measures {pixel_distance:.0f}px",
                                location=(x1, y1)
                            ))
                            break
        
        return estimates
    
    def _extract_from_objects(self, geometric_elements: List[Dict[str, Any]]) -> List[ScaleEstimate]:
        """
        Detect scale from known objects like doors, hallways, stairs.
        """
        estimates = []
        
        # Find door-like rectangles (width ~2.5-3ft, height ~6.67-7ft)
        door_candidates = []
        for elem in geometric_elements:
            if elem.get('type') != 'rectangle':
                continue
            
            width = elem.get('width', 0)
            height = elem.get('height', 0)
            
            if width > 0 and height > 0:
                aspect_ratio = height / width
                # Door aspect ratio: ~2.3 to 2.8
                if 2.0 <= aspect_ratio <= 3.0:
                    door_candidates.append((width, height))
        
        if door_candidates:
            # Cluster similar sizes
            width_clusters = self._cluster_values([w for w, h in door_candidates])
            
            for cluster_center, cluster_size in width_clusters:
                if cluster_size >= 3:  # Need at least 3 similar doors
                    # Assume standard door width of 2'8" (2.67 ft)
                    scale = cluster_center / 2.67
                    
                    # Validate against standard scales
                    for notation, standard_scale in self.STANDARD_SCALES.items():
                        if abs(scale - standard_scale) / standard_scale < 0.1:
                            estimates.append(ScaleEstimate(
                                pixels_per_foot=scale,
                                confidence=0.8,
                                method='door_width',
                                evidence=f"Found {cluster_size} doors at ~{cluster_center:.0f}px width"
                            ))
                            break
        
        return estimates
    
    def _extract_from_grid(self, geometric_elements: List[Dict[str, Any]]) -> Optional[ScaleEstimate]:
        """
        Detect scale from structural grid spacing (if present).
        """
        # Find grid lines (regularly spaced parallel lines)
        h_lines = []
        v_lines = []
        
        for elem in geometric_elements:
            if elem.get('type') != 'line':
                continue
            
            x1, y1, x2, y2 = elem.get('coords', [0, 0, 0, 0])
            
            # Horizontal lines
            if abs(y2 - y1) < 5:  # Nearly horizontal
                h_lines.append(y1)
            # Vertical lines
            elif abs(x2 - x1) < 5:  # Nearly vertical
                v_lines.append(x1)
        
        # Find regular spacing
        h_spacing = self._find_regular_spacing(sorted(h_lines))
        v_spacing = self._find_regular_spacing(sorted(v_lines))
        
        if h_spacing or v_spacing:
            spacing = h_spacing or v_spacing
            
            # Typical grid spacings: 10', 15', 20', 25', 30'
            for grid_feet in [10, 15, 20, 25, 30]:
                scale = spacing / grid_feet
                
                for notation, standard_scale in self.STANDARD_SCALES.items():
                    if abs(scale - standard_scale) / standard_scale < 0.1:
                        return ScaleEstimate(
                            pixels_per_foot=scale,
                            confidence=0.75,
                            method='grid_spacing',
                            evidence=f"Grid spacing {spacing:.0f}px = {grid_feet}'"
                        )
        
        return None
    
    def _consolidate_estimates(self, estimates: List[ScaleEstimate]) -> ScaleResult:
        """
        Consolidate multiple estimates into a final result.
        Requires at least 2 corroborating estimates within 3% tolerance.
        """
        if not estimates:
            return ScaleResult(
                pixels_per_foot=48.0,  # Default to 1/4"=1'
                scale_notation="1/4\"=1'",
                confidence=0.0,
                estimates=[],
                corroborations=0,
                needs_override=True,
                recommendation="No scale detected. Set SCALE_OVERRIDE=48 for 1/4\"=1'"
            )
        
        # Group estimates by similar values (within 3%)
        groups = defaultdict(list)
        for est in estimates:
            # Find which standard scale this is closest to
            best_match = None
            best_diff = float('inf')
            
            for notation, standard in self.STANDARD_SCALES.items():
                diff = abs(est.pixels_per_foot - standard) / standard
                if diff < best_diff:
                    best_diff = diff
                    best_match = notation
            
            if best_match and best_diff < 0.03:  # Within 3%
                groups[best_match].append(est)
        
        # Find the group with most corroboration
        best_group = None
        max_corroboration = 0
        
        for notation, group_estimates in groups.items():
            # Weight by confidence
            total_confidence = sum(e.confidence for e in group_estimates)
            
            if len(group_estimates) > max_corroboration or \
               (len(group_estimates) == max_corroboration and total_confidence > best_group[1]):
                max_corroboration = len(group_estimates)
                best_group = (notation, total_confidence, group_estimates)
        
        if best_group:
            notation, total_confidence, group_estimates = best_group
            avg_scale = sum(e.pixels_per_foot for e in group_estimates) / len(group_estimates)
            
            # Calculate tolerance
            if len(group_estimates) > 1:
                scales = [e.pixels_per_foot for e in group_estimates]
                tolerance = (max(scales) - min(scales)) / avg_scale * 100
            else:
                tolerance = 0.0
            
            return ScaleResult(
                pixels_per_foot=avg_scale,
                scale_notation=notation,
                confidence=min(1.0, total_confidence / len(group_estimates)),
                estimates=group_estimates,
                corroborations=len(group_estimates),
                tolerance_percent=tolerance,
                needs_override=len(group_estimates) < 2
            )
        
        # No consensus - return highest confidence single estimate
        best_estimate = max(estimates, key=lambda e: e.confidence)
        notation = self._find_closest_notation(best_estimate.pixels_per_foot)
        
        return ScaleResult(
            pixels_per_foot=best_estimate.pixels_per_foot,
            scale_notation=notation,
            confidence=best_estimate.confidence * 0.5,  # Reduce confidence
            estimates=[best_estimate],
            corroborations=1,
            needs_override=True,
            recommendation="Only one scale estimate found. Verify with SCALE_OVERRIDE if needed."
        )
    
    def _parse_dimension_text(self, text: str) -> Optional[float]:
        """Parse dimension text like '12\'-6"' into decimal feet."""
        if not text:
            return None
        
        # Remove spaces and normalize
        text = text.strip().upper()
        
        # Pattern: 12'-6" or 12'-6 1/2"
        match = re.match(r'(\d+)[\'\-]+(\d+)(?:\s+(\d+)/(\d+))?["\']?', text)
        if match:
            feet = int(match.group(1))
            inches = int(match.group(2))
            
            # Handle fractional inches
            if match.group(3) and match.group(4):
                inches += int(match.group(3)) / int(match.group(4))
            
            return feet + inches / 12.0
        
        # Pattern: 12' or 12.5'
        match = re.match(r'(\d+(?:\.\d+)?)[\']', text)
        if match:
            return float(match.group(1))
        
        return None
    
    def _cluster_values(self, values: List[float], tolerance: float = 0.1) -> List[Tuple[float, int]]:
        """Cluster similar values within tolerance."""
        if not values:
            return []
        
        clusters = []
        sorted_values = sorted(values)
        
        current_cluster = [sorted_values[0]]
        
        for val in sorted_values[1:]:
            if abs(val - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(val)
            else:
                # Start new cluster
                center = sum(current_cluster) / len(current_cluster)
                clusters.append((center, len(current_cluster)))
                current_cluster = [val]
        
        # Add last cluster
        if current_cluster:
            center = sum(current_cluster) / len(current_cluster)
            clusters.append((center, len(current_cluster)))
        
        return clusters
    
    def _find_regular_spacing(self, positions: List[float]) -> Optional[float]:
        """Find regular spacing in a list of positions."""
        if len(positions) < 3:
            return None
        
        spacings = []
        for i in range(1, len(positions)):
            spacings.append(positions[i] - positions[i-1])
        
        # Find most common spacing (within 5% tolerance)
        clusters = self._cluster_values(spacings, tolerance=0.05)
        
        if clusters:
            # Return spacing with most occurrences
            best_cluster = max(clusters, key=lambda x: x[1])
            if best_cluster[1] >= 3:  # Need at least 3 regular intervals
                return best_cluster[0]
        
        return None
    
    def _metric_to_imperial(self, ratio: int) -> str:
        """Convert metric scale ratio to imperial notation."""
        metric_map = {
            48: "1/4\"=1'",
            96: "1/8\"=1'",
            24: "1/2\"=1'",
            50: "1/4\"=1'",
            100: "1/8\"=1'",
        }
        
        if ratio in metric_map:
            return metric_map[ratio]
        
        # Approximate
        if ratio < 30:
            return "1/2\"=1'"
        elif ratio < 60:
            return "1/4\"=1'"
        elif ratio < 120:
            return "1/8\"=1'"
        else:
            return "1/16\"=1'"
    
    def _find_closest_notation(self, pixels_per_foot: float) -> str:
        """Find the closest standard scale notation."""
        best_notation = "1/4\"=1'"
        best_diff = float('inf')
        
        for notation, standard in self.STANDARD_SCALES.items():
            diff = abs(pixels_per_foot - standard)
            if diff < best_diff:
                best_diff = diff
                best_notation = notation
        
        return best_notation
    
    def _create_result_from_override(self, override: float) -> ScaleResult:
        """Create result from user override."""
        notation = self._find_closest_notation(override)
        
        return ScaleResult(
            pixels_per_foot=override,
            scale_notation=notation,
            confidence=1.0,
            estimates=[ScaleEstimate(
                pixels_per_foot=override,
                confidence=1.0,
                method='user_override',
                evidence=f"User specified {override} px/ft"
            )],
            corroborations=1,
            tolerance_percent=0.0,
            needs_override=False
        )
    
    def _generate_recommendation(self, estimates: List[ScaleEstimate], page_size: Tuple[float, float]) -> str:
        """Generate recommendation for user when scale is uncertain."""
        if not estimates:
            return "No scale detected. Common scales: SCALE_OVERRIDE=48 (1/4\"=1'), SCALE_OVERRIDE=96 (1/8\"=1')"
        
        # Suggest based on page size and any estimates
        width, height = page_size
        
        if width > 2000 or height > 2000:
            # Large drawing, likely 1/8" or smaller
            return "Large drawing detected. Try SCALE_OVERRIDE=96 for 1/8\"=1' scale"
        else:
            # Standard size, likely 1/4"
            return "Try SCALE_OVERRIDE=48 for 1/4\"=1' scale (most common)"


# Singleton instance
deterministic_scale_detector = DeterministicScaleDetector()