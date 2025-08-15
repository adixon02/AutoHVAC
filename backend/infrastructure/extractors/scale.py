"""
RANSAC Scale Detector with Edge Pairing
Uses vector extraction and dimension clustering for robust scale detection
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from sklearn.neighbors import KDTree
import re

from infrastructure.extractors.vector import (
    VectorExtractor, 
    VectorData, 
    VectorPath, 
    DimensionLabel,
    get_vector_extractor
)

logger = logging.getLogger(__name__)


@dataclass
class ScaleHypothesis:
    """A scale hypothesis from dimension-edge pairing"""
    scale_px_per_ft: float
    confidence: float
    support_count: int
    dimension_pairs: List[Tuple[DimensionLabel, VectorPath]]
    error_distribution: List[float]
    

@dataclass
class ScaleResult:
    """Final scale detection result"""
    scale_px_per_ft: float
    confidence: float
    method: str  # 'ransac', 'explicit', 'default'
    details: Dict[str, Any]


class RANSACScaleDetector:
    """
    Robust scale detection using RANSAC with edge pairing
    Geometry-first approach - no LLM involvement
    """
    
    def __init__(self):
        self.vector_extractor = get_vector_extractor()
        
        # RANSAC parameters
        self.min_samples = 3  # Minimum dimension-edge pairs for hypothesis
        self.ransac_iterations = 100
        self.inlier_threshold = 0.05  # 5% error tolerance
        self.min_confidence = 0.95  # Required confidence for Gate A
        
        # Common architectural scales (pixels per foot)
        self.common_scales = [
            48.0,   # 1/4" = 1' (most common)
            96.0,   # 1/8" = 1'
            24.0,   # 1/2" = 1'
            192.0,  # 1/16" = 1'
            32.0,   # 3/8" = 1'
        ]
        
        # Scale notation patterns
        self.scale_patterns = [
            r"1/(\d+)[\"']?\s*=\s*1'",  # 1/4" = 1'
            r"(\d+)[\"']?\s*=\s*(\d+)'",  # 1" = 4'
            r"scale\s*:\s*1/(\d+)",  # Scale: 1/4
            r"(\d+):(\d+)",  # 1:48
        ]
    
    def detect_scale(
        self, 
        pdf_path: str, 
        page_num: int = 0,
        override_scale: Optional[float] = None
    ) -> ScaleResult:
        """
        Main scale detection entry point
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to analyze
            override_scale: Manual scale override if known
            
        Returns:
            ScaleResult with detected scale and confidence
        """
        logger.info(f"Starting RANSAC scale detection for page {page_num + 1}")
        
        # Check for override first
        if override_scale and override_scale > 0:
            logger.info(f"Using scale override: {override_scale} px/ft")
            return ScaleResult(
                scale_px_per_ft=override_scale,
                confidence=1.0,
                method='override',
                details={'source': 'manual_override'}
            )
        
        # Extract vector data
        vector_data = self.vector_extractor.extract_vectors(pdf_path, page_num)
        
        # Try multiple detection methods in order
        
        # 1. Try explicit scale notation
        scale_result = self._detect_explicit_scale(vector_data)
        if scale_result and scale_result.confidence >= self.min_confidence:
            logger.info(f"Found explicit scale: {scale_result.scale_px_per_ft} px/ft")
            return scale_result
        
        # 2. Try RANSAC with edge pairing
        scale_result = self._detect_ransac_scale(vector_data)
        if scale_result and scale_result.confidence >= self.min_confidence:
            logger.info(f"RANSAC scale detected: {scale_result.scale_px_per_ft} px/ft")
            return scale_result
        
        # 3. Try dimension clustering
        scale_result = self._detect_clustered_scale(vector_data)
        if scale_result and scale_result.confidence >= 0.8:  # Lower threshold for clustering
            logger.info(f"Clustered scale detected: {scale_result.scale_px_per_ft} px/ft")
            return scale_result
        
        # 4. Default to most common scale
        logger.warning("Scale detection failed, using default 1/4\" = 1' scale")
        return ScaleResult(
            scale_px_per_ft=48.0,
            confidence=0.3,
            method='default',
            details={'reason': 'All detection methods failed'}
        )
    
    def _detect_explicit_scale(self, vector_data: VectorData) -> Optional[ScaleResult]:
        """
        Detect explicit scale notation in text
        """
        for text_elem in vector_data.texts:
            text_lower = text_elem.text.lower()
            
            # Check for scale keywords
            if 'scale' not in text_lower and '=' not in text_elem.text and ':' not in text_elem.text:
                continue
            
            # Try each pattern
            for pattern in self.scale_patterns:
                match = re.search(pattern, text_elem.text, re.IGNORECASE)
                if match:
                    scale_px_per_ft = self._parse_scale_notation(match)
                    if scale_px_per_ft > 0:
                        return ScaleResult(
                            scale_px_per_ft=scale_px_per_ft,
                            confidence=0.98,
                            method='explicit',
                            details={
                                'notation': text_elem.text,
                                'pattern': pattern
                            }
                        )
        
        return None
    
    def _parse_scale_notation(self, match) -> float:
        """Parse scale notation match to pixels per foot"""
        groups = match.groups()
        
        if len(groups) == 1:
            # Format: 1/4" = 1' -> denominator only
            denominator = float(groups[0])
            if denominator > 0:
                # 1/4" = 1' means 4 inches per foot, so 12/0.25 = 48 px/ft at standard DPI
                return 192.0 / denominator  # Assuming 192 DPI base
        
        elif len(groups) == 2:
            # Format: 1" = 4' or ratio format
            val1 = float(groups[0])
            val2 = float(groups[1])
            
            if val1 > 0 and val2 > 0:
                if val2 > val1:
                    # Likely inches to feet
                    return 48.0 * (val2 / val1)  # Base 48 px/ft for 1/4" scale
                else:
                    # Likely a ratio
                    return val1 / val2 * 48.0
        
        return 0
    
    def _detect_ransac_scale(self, vector_data: VectorData) -> Optional[ScaleResult]:
        """
        RANSAC-based scale detection with edge pairing
        """
        if not vector_data.dimensions or not vector_data.paths:
            return None
        
        # Cluster dimensions to edges
        dim_edge_pairs = self.vector_extractor.cluster_dimensions_to_edges(
            vector_data.dimensions,
            vector_data.paths,
            max_distance=30  # pixels
        )
        
        if len(dim_edge_pairs) < self.min_samples:
            logger.warning(f"Not enough dimension-edge pairs: {len(dim_edge_pairs)}")
            return None
        
        best_hypothesis = None
        best_inlier_ratio = 0
        
        # RANSAC iterations
        for iteration in range(self.ransac_iterations):
            # Random sample
            sample_indices = np.random.choice(
                len(dim_edge_pairs), 
                min(self.min_samples, len(dim_edge_pairs)), 
                replace=False
            )
            sample_pairs = [dim_edge_pairs[i] for i in sample_indices]
            
            # Generate hypothesis from sample
            hypothesis = self._generate_hypothesis(sample_pairs)
            if not hypothesis:
                continue
            
            # Test hypothesis against all pairs
            inliers, errors = self._test_hypothesis(hypothesis, dim_edge_pairs)
            inlier_ratio = len(inliers) / len(dim_edge_pairs)
            
            # Update best if better
            if inlier_ratio > best_inlier_ratio:
                best_inlier_ratio = inlier_ratio
                best_hypothesis = ScaleHypothesis(
                    scale_px_per_ft=hypothesis,
                    confidence=inlier_ratio,
                    support_count=len(inliers),
                    dimension_pairs=inliers,
                    error_distribution=errors
                )
        
        if best_hypothesis and best_hypothesis.confidence >= 0.5:
            # Refine using all inliers
            refined_scale = self._refine_scale(best_hypothesis)
            
            return ScaleResult(
                scale_px_per_ft=refined_scale,
                confidence=best_hypothesis.confidence,
                method='ransac',
                details={
                    'support_count': best_hypothesis.support_count,
                    'total_pairs': len(dim_edge_pairs),
                    'mean_error': np.mean(best_hypothesis.error_distribution)
                }
            )
        
        return None
    
    def _generate_hypothesis(
        self, 
        sample_pairs: List[Tuple[DimensionLabel, VectorPath]]
    ) -> Optional[float]:
        """Generate scale hypothesis from sample pairs"""
        scales = []
        
        for dim, path in sample_pairs:
            # Calculate edge length in pixels
            if path.path_type == "line" and len(path.points) == 2:
                p1, p2 = path.points[0], path.points[1]
                edge_length_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                
                # Calculate scale
                if dim.value_ft > 0 and edge_length_px > 0:
                    scale = edge_length_px / dim.value_ft
                    scales.append(scale)
        
        if scales:
            # Use median for robustness
            return np.median(scales)
        
        return None
    
    def _test_hypothesis(
        self,
        hypothesis_scale: float,
        dim_edge_pairs: List[Tuple[DimensionLabel, VectorPath]]
    ) -> Tuple[List[Tuple[DimensionLabel, VectorPath]], List[float]]:
        """Test hypothesis against all dimension-edge pairs"""
        inliers = []
        errors = []
        
        for dim, path in dim_edge_pairs:
            if path.path_type == "line" and len(path.points) == 2:
                # Calculate edge length
                p1, p2 = path.points[0], path.points[1]
                edge_length_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                
                # Expected length based on hypothesis
                expected_px = dim.value_ft * hypothesis_scale
                
                # Calculate error
                if expected_px > 0:
                    error = abs(edge_length_px - expected_px) / expected_px
                    errors.append(error)
                    
                    # Check if inlier
                    if error < self.inlier_threshold:
                        inliers.append((dim, path))
        
        return inliers, errors
    
    def _refine_scale(self, hypothesis: ScaleHypothesis) -> float:
        """Refine scale using all inliers"""
        scales = []
        
        for dim, path in hypothesis.dimension_pairs:
            if path.path_type == "line" and len(path.points) == 2:
                p1, p2 = path.points[0], path.points[1]
                edge_length_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                
                if dim.value_ft > 0:
                    scales.append(edge_length_px / dim.value_ft)
        
        if scales:
            # Use trimmed mean for robustness
            scales_sorted = sorted(scales)
            trim_count = max(1, len(scales) // 10)  # Trim 10% from each end
            if len(scales_sorted) > 2 * trim_count:
                trimmed = scales_sorted[trim_count:-trim_count]
            else:
                trimmed = scales_sorted
            
            return np.mean(trimmed)
        
        return hypothesis.scale_px_per_ft
    
    def _detect_clustered_scale(self, vector_data: VectorData) -> Optional[ScaleResult]:
        """
        Detect scale using KD-tree clustering of dimensions
        """
        if not vector_data.dimensions:
            return None
        
        # Extract all dimension values
        dim_values = [d.value_ft for d in vector_data.dimensions if d.value_ft > 0]
        
        if len(dim_values) < 5:
            return None
        
        # Find parallel edges
        parallel_pairs = self.vector_extractor.find_parallel_edges(
            vector_data.paths,
            tolerance=3.0  # degrees
        )
        
        if not parallel_pairs:
            return None
        
        # Calculate edge distances
        edge_distances = []
        for path1, path2 in parallel_pairs:
            if path1.path_type == "line" and path2.path_type == "line":
                # Calculate perpendicular distance between parallel lines
                dist = self._parallel_edge_distance(path1, path2)
                if dist > 0:
                    edge_distances.append(dist)
        
        if not edge_distances:
            return None
        
        # Use KD-tree to find dimension-distance matches
        dim_tree = KDTree(np.array(dim_values).reshape(-1, 1))
        
        best_scale = None
        best_matches = 0
        
        for scale in self.common_scales:
            matches = 0
            for edge_dist in edge_distances:
                # Expected dimension for this edge distance at this scale
                expected_dim = edge_dist / scale
                
                # Find nearest dimension
                dist, idx = dim_tree.query([[expected_dim]], k=1)
                
                # Check if close enough (within 10%)
                if dist[0][0] / expected_dim < 0.1:
                    matches += 1
            
            if matches > best_matches:
                best_matches = matches
                best_scale = scale
        
        if best_scale and best_matches >= 3:
            confidence = min(0.95, best_matches / len(edge_distances))
            
            return ScaleResult(
                scale_px_per_ft=best_scale,
                confidence=confidence,
                method='clustering',
                details={
                    'matched_edges': best_matches,
                    'total_edges': len(edge_distances),
                    'dimension_count': len(dim_values)
                }
            )
        
        return None
    
    def _parallel_edge_distance(
        self,
        path1: VectorPath,
        path2: VectorPath
    ) -> float:
        """Calculate perpendicular distance between parallel edges"""
        if len(path1.points) != 2 or len(path2.points) != 2:
            return 0
        
        # Get line points
        p1_start, p1_end = path1.points[0], path1.points[1]
        p2_start, p2_end = path2.points[0], path2.points[1]
        
        # Calculate perpendicular distance from p2_start to line p1
        # Using point-to-line distance formula
        A = p1_end[1] - p1_start[1]
        B = p1_start[0] - p1_end[0]
        C = p1_end[0] * p1_start[1] - p1_start[0] * p1_end[1]
        
        if A*A + B*B == 0:
            return 0
        
        distance = abs(A * p2_start[0] + B * p2_start[1] + C) / np.sqrt(A*A + B*B)
        
        return distance
    
    def validate_scale(
        self,
        scale_px_per_ft: float,
        vector_data: VectorData
    ) -> Tuple[bool, str]:
        """
        Validate detected scale against blueprint content
        
        Returns:
            (is_valid, error_message)
        """
        # Check if scale is reasonable
        if scale_px_per_ft < 10 or scale_px_per_ft > 500:
            return False, f"Scale {scale_px_per_ft} px/ft is outside reasonable range [10, 500]"
        
        # Check against common scales
        closest_common = min(self.common_scales, key=lambda x: abs(x - scale_px_per_ft))
        deviation = abs(scale_px_per_ft - closest_common) / closest_common
        
        if deviation > 0.2:  # More than 20% off from common scale
            logger.warning(f"Scale {scale_px_per_ft} deviates {deviation*100:.1f}% from nearest common scale {closest_common}")
        
        # Validate against dimension-edge pairs
        dim_edge_pairs = self.vector_extractor.cluster_dimensions_to_edges(
            vector_data.dimensions,
            vector_data.paths
        )
        
        if dim_edge_pairs:
            errors = []
            for dim, path in dim_edge_pairs[:10]:  # Check first 10 pairs
                if path.path_type == "line" and len(path.points) == 2:
                    p1, p2 = path.points[0], path.points[1]
                    edge_length_px = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                    expected_px = dim.value_ft * scale_px_per_ft
                    
                    if expected_px > 0:
                        error = abs(edge_length_px - expected_px) / expected_px
                        errors.append(error)
            
            if errors:
                mean_error = np.mean(errors)
                if mean_error > 0.15:  # More than 15% average error
                    return False, f"Scale validation failed: {mean_error*100:.1f}% average error"
        
        return True, ""


# Singleton instance
_scale_detector = None

def get_scale_detector() -> RANSACScaleDetector:
    """Get or create the global scale detector"""
    global _scale_detector
    if _scale_detector is None:
        _scale_detector = RANSACScaleDetector()
    return _scale_detector