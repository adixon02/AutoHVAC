"""
Room Graph Validator
Validates room polygons and their spatial relationships
Ensures geometric consistency and physical plausibility
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class RoomValidationResult:
    """Result of room validation"""
    is_valid: bool
    confidence: float
    issues: List[str]
    corrections: Dict[str, Any]
    room_graph: Optional[nx.Graph]


@dataclass
class RoomNode:
    """Node in the room adjacency graph"""
    room_id: str
    polygon: Polygon
    area_sqft: float
    room_type: str
    floor: int
    center: Tuple[float, float]


class RoomGraphValidator:
    """
    Validates room geometry and spatial relationships
    Builds adjacency graph for physics calculations
    """
    
    def __init__(self):
        # Validation thresholds
        self.min_room_area_sqft = 20  # Minimum plausible room size
        self.max_room_area_sqft = 2000  # Maximum plausible room size
        self.min_wall_thickness_ft = 0.25  # 3 inches minimum
        self.max_wall_thickness_ft = 2.0  # 2 feet maximum
        self.overlap_tolerance = 0.1  # 10% overlap allowed
        
        # Room type constraints
        self.room_size_constraints = {
            'bedroom': (70, 500),
            'bathroom': (20, 150),
            'kitchen': (70, 400),
            'living': (100, 600),
            'dining': (80, 400),
            'hallway': (20, 200),
            'closet': (10, 100),
            'garage': (200, 1000),
            'utility': (20, 150),
            'storage': (10, 200)
        }
    
    def validate_rooms(
        self,
        rooms: List[Dict[str, Any]],
        building_footprint: List[Tuple[float, float]]
    ) -> RoomValidationResult:
        """
        Validate room polygons and build adjacency graph
        
        Args:
            rooms: List of room dictionaries with polygons
            building_footprint: Building perimeter polygon
            
        Returns:
            Validation result with issues and corrections
        """
        logger.info(f"Validating {len(rooms)} rooms")
        
        issues = []
        corrections = {}
        
        # Convert to Shapely polygons
        room_nodes = []
        for i, room in enumerate(rooms):
            try:
                # Extract polygon
                if 'polygon' in room:
                    poly_points = room['polygon']
                elif 'boundary' in room:
                    poly_points = room['boundary']
                else:
                    issues.append(f"Room {i} missing polygon data")
                    continue
                
                # Create Shapely polygon
                if len(poly_points) >= 3:
                    polygon = Polygon(poly_points)
                    
                    # Fix invalid polygons
                    if not polygon.is_valid:
                        polygon = polygon.buffer(0)  # Common fix for self-intersections
                        corrections[f"room_{i}"] = "Fixed self-intersecting polygon"
                    
                    # Create room node
                    node = RoomNode(
                        room_id=room.get('id', f"room_{i}"),
                        polygon=polygon,
                        area_sqft=room.get('area', polygon.area),
                        room_type=room.get('type', 'unknown'),
                        floor=room.get('floor', 1),
                        center=polygon.centroid.coords[0]
                    )
                    room_nodes.append(node)
                else:
                    issues.append(f"Room {i} has insufficient points ({len(poly_points)})")
                    
            except Exception as e:
                issues.append(f"Room {i} polygon creation failed: {e}")
        
        if not room_nodes:
            return RoomValidationResult(
                is_valid=False,
                confidence=0,
                issues=["No valid room polygons found"],
                corrections={},
                room_graph=None
            )
        
        # Perform validation checks
        
        # 1. Check room sizes
        size_issues = self._validate_room_sizes(room_nodes)
        issues.extend(size_issues)
        
        # 2. Check for overlaps
        overlap_issues, overlap_corrections = self._check_overlaps(room_nodes)
        issues.extend(overlap_issues)
        corrections.update(overlap_corrections)
        
        # 3. Check coverage
        coverage_issues = self._check_building_coverage(room_nodes, building_footprint)
        issues.extend(coverage_issues)
        
        # 4. Check adjacency and gaps
        adjacency_issues = self._check_adjacency(room_nodes)
        issues.extend(adjacency_issues)
        
        # 5. Build room graph
        room_graph = self._build_adjacency_graph(room_nodes)
        
        # 6. Check graph connectivity
        connectivity_issues = self._check_connectivity(room_graph, room_nodes)
        issues.extend(connectivity_issues)
        
        # Calculate confidence
        confidence = self._calculate_confidence(issues, room_nodes)
        
        # Determine validity
        critical_issues = [i for i in issues if 'critical' in i.lower() or 'error' in i.lower()]
        is_valid = len(critical_issues) == 0 and confidence >= 0.6
        
        return RoomValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            corrections=corrections,
            room_graph=room_graph
        )
    
    def _validate_room_sizes(self, room_nodes: List[RoomNode]) -> List[str]:
        """Validate room sizes against constraints"""
        issues = []
        
        for node in room_nodes:
            # Check absolute constraints
            if node.area_sqft < self.min_room_area_sqft:
                issues.append(f"Room {node.room_id} too small: {node.area_sqft:.1f} sqft")
            elif node.area_sqft > self.max_room_area_sqft:
                issues.append(f"Room {node.room_id} too large: {node.area_sqft:.1f} sqft")
            
            # Check type-specific constraints
            if node.room_type in self.room_size_constraints:
                min_size, max_size = self.room_size_constraints[node.room_type]
                if node.area_sqft < min_size:
                    issues.append(f"{node.room_type} {node.room_id} below typical size: "
                                f"{node.area_sqft:.1f} sqft (expected >= {min_size})")
                elif node.area_sqft > max_size:
                    issues.append(f"{node.room_type} {node.room_id} above typical size: "
                                f"{node.area_sqft:.1f} sqft (expected <= {max_size})")
        
        return issues
    
    def _check_overlaps(
        self,
        room_nodes: List[RoomNode]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Check for overlapping rooms"""
        issues = []
        corrections = {}
        
        for i, node1 in enumerate(room_nodes):
            for j, node2 in enumerate(room_nodes[i+1:], i+1):
                if node1.floor != node2.floor:
                    continue  # Different floors can overlap
                
                intersection = node1.polygon.intersection(node2.polygon)
                if not intersection.is_empty:
                    overlap_area = intersection.area
                    overlap_pct1 = overlap_area / node1.polygon.area
                    overlap_pct2 = overlap_area / node2.polygon.area
                    
                    if max(overlap_pct1, overlap_pct2) > self.overlap_tolerance:
                        issues.append(f"Critical: Rooms {node1.room_id} and {node2.room_id} "
                                    f"overlap by {max(overlap_pct1, overlap_pct2)*100:.1f}%")
                        
                        # Suggest correction
                        if overlap_pct1 < overlap_pct2:
                            # Shrink node2
                            corrections[node2.room_id] = {
                                'action': 'shrink',
                                'amount': overlap_area
                            }
                        else:
                            # Shrink node1
                            corrections[node1.room_id] = {
                                'action': 'shrink',
                                'amount': overlap_area
                            }
        
        return issues, corrections
    
    def _check_building_coverage(
        self,
        room_nodes: List[RoomNode],
        building_footprint: List[Tuple[float, float]]
    ) -> List[str]:
        """Check if rooms properly cover the building footprint"""
        issues = []
        
        if not building_footprint or len(building_footprint) < 3:
            return ["Building footprint not provided"]
        
        try:
            building_poly = Polygon(building_footprint)
            
            # Union all room polygons on ground floor
            ground_floor_rooms = [n.polygon for n in room_nodes if n.floor == 1]
            if ground_floor_rooms:
                rooms_union = unary_union(ground_floor_rooms)
                
                # Check coverage
                coverage = rooms_union.area / building_poly.area if building_poly.area > 0 else 0
                
                if coverage < 0.7:
                    issues.append(f"Low building coverage: {coverage*100:.1f}% "
                                "(expected >= 70%)")
                elif coverage > 1.2:
                    issues.append(f"Rooms extend beyond building: {coverage*100:.1f}% coverage")
                
                # Check for gaps
                gaps = building_poly.difference(rooms_union)
                if not gaps.is_empty and gaps.area > building_poly.area * 0.1:
                    issues.append(f"Significant gaps in floor plan: {gaps.area:.1f} sqft")
                    
        except Exception as e:
            issues.append(f"Coverage check failed: {e}")
        
        return issues
    
    def _check_adjacency(self, room_nodes: List[RoomNode]) -> List[str]:
        """Check for proper room adjacency (walls between rooms)"""
        issues = []
        
        for i, node1 in enumerate(room_nodes):
            for j, node2 in enumerate(room_nodes[i+1:], i+1):
                if node1.floor != node2.floor:
                    continue
                
                # Check if rooms are adjacent
                distance = node1.polygon.distance(node2.polygon)
                
                if 0 < distance < self.min_wall_thickness_ft:
                    issues.append(f"Rooms {node1.room_id} and {node2.room_id} "
                                f"have insufficient wall thickness: {distance:.2f} ft")
                elif distance > self.max_wall_thickness_ft:
                    # Check if they should be adjacent (share a wall)
                    if self._should_be_adjacent(node1, node2):
                        issues.append(f"Rooms {node1.room_id} and {node2.room_id} "
                                    f"have excessive gap: {distance:.2f} ft")
        
        return issues
    
    def _should_be_adjacent(self, node1: RoomNode, node2: RoomNode) -> bool:
        """Determine if two rooms should share a wall"""
        # Simple heuristic: rooms are close and on same floor
        center_dist = np.sqrt(
            (node1.center[0] - node2.center[0])**2 +
            (node1.center[1] - node2.center[1])**2
        )
        
        # If centers are close relative to room sizes
        avg_size = np.sqrt((node1.area_sqft + node2.area_sqft) / 2)
        
        return center_dist < avg_size * 2  # Within 2x average dimension
    
    def _build_adjacency_graph(self, room_nodes: List[RoomNode]) -> nx.Graph:
        """Build graph of room adjacencies"""
        G = nx.Graph()
        
        # Add nodes
        for node in room_nodes:
            G.add_node(
                node.room_id,
                polygon=node.polygon,
                area=node.area_sqft,
                type=node.room_type,
                floor=node.floor,
                center=node.center
            )
        
        # Add edges for adjacent rooms
        for i, node1 in enumerate(room_nodes):
            for j, node2 in enumerate(room_nodes[i+1:], i+1):
                # Check if rooms share a wall (are adjacent)
                if self._rooms_are_adjacent(node1, node2):
                    # Calculate shared wall length
                    shared_wall_length = self._calculate_shared_wall(node1, node2)
                    
                    G.add_edge(
                        node1.room_id,
                        node2.room_id,
                        wall_length=shared_wall_length,
                        same_floor=(node1.floor == node2.floor)
                    )
        
        return G
    
    def _rooms_are_adjacent(self, node1: RoomNode, node2: RoomNode) -> bool:
        """Check if two rooms share a wall"""
        # Rooms are adjacent if they touch or are very close
        distance = node1.polygon.distance(node2.polygon)
        
        # Adjacent if distance is less than max wall thickness
        return distance < self.max_wall_thickness_ft
    
    def _calculate_shared_wall(self, node1: RoomNode, node2: RoomNode) -> float:
        """Calculate length of shared wall between rooms"""
        # Buffer polygons slightly to ensure they touch
        buffer_dist = self.max_wall_thickness_ft / 2
        poly1_buffered = node1.polygon.buffer(buffer_dist)
        poly2_buffered = node2.polygon.buffer(buffer_dist)
        
        # Find intersection (shared boundary)
        intersection = poly1_buffered.intersection(poly2_buffered)
        
        if intersection.is_empty:
            return 0
        
        # Estimate shared wall length from intersection
        if hasattr(intersection, 'length'):
            # For line-like intersections
            return intersection.length
        elif hasattr(intersection, 'area'):
            # For area intersections, estimate from perimeter
            return np.sqrt(intersection.area) * 2  # Rough estimate
        
        return 0
    
    def _check_connectivity(
        self,
        graph: nx.Graph,
        room_nodes: List[RoomNode]
    ) -> List[str]:
        """Check if all rooms are properly connected"""
        issues = []
        
        if not graph or graph.number_of_nodes() == 0:
            return ["Room graph is empty"]
        
        # Check if graph is connected (all rooms reachable)
        if not nx.is_connected(graph):
            components = list(nx.connected_components(graph))
            if len(components) > 1:
                issues.append(f"Floor plan has {len(components)} disconnected sections")
                
                # Report isolated rooms
                for component in components:
                    if len(component) == 1:
                        room_id = list(component)[0]
                        issues.append(f"Room {room_id} is isolated (no connections)")
        
        # Check for required connections (e.g., bedrooms should connect to hallway)
        for node in room_nodes:
            if node.room_type == 'bedroom':
                neighbors = list(graph.neighbors(node.room_id)) if graph.has_node(node.room_id) else []
                
                # Check if bedroom has reasonable access
                neighbor_types = [
                    graph.nodes[n]['type'] 
                    for n in neighbors 
                    if 'type' in graph.nodes[n]
                ]
                
                if not any(t in ['hallway', 'living', 'foyer'] for t in neighbor_types):
                    if len(neighbors) == 1 and neighbor_types[0] == 'bathroom':
                        # Master bedroom with ensuite is OK
                        pass
                    else:
                        issues.append(f"Bedroom {node.room_id} lacks proper access "
                                    f"(connects to: {neighbor_types})")
        
        return issues
    
    def _calculate_confidence(
        self,
        issues: List[str],
        room_nodes: List[RoomNode]
    ) -> float:
        """Calculate overall confidence score"""
        if not room_nodes:
            return 0
        
        # Start with perfect score
        confidence = 1.0
        
        # Deduct for issues
        critical_issues = sum(1 for i in issues if 'critical' in i.lower())
        warning_issues = sum(1 for i in issues if 'critical' not in i.lower())
        
        confidence -= critical_issues * 0.2
        confidence -= warning_issues * 0.05
        
        # Boost for good characteristics
        if len(room_nodes) >= 5:
            confidence += 0.1  # Reasonable room count
        
        # Check room size distribution
        areas = [n.area_sqft for n in room_nodes]
        if areas:
            avg_area = np.mean(areas)
            if 100 < avg_area < 300:
                confidence += 0.1  # Reasonable average size
        
        return max(0, min(1, confidence))


# Singleton instance
_room_validator = None

def get_room_validator() -> RoomGraphValidator:
    """Get or create the global room validator"""
    global _room_validator
    if _room_validator is None:
        _room_validator = RoomGraphValidator()
    return _room_validator