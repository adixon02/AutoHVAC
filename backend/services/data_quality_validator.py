"""
Data Quality Validation for Multi-Story Blueprint Processing

This module validates the quality of parsed blueprint data and provides
confidence scores to ensure accurate HVAC load calculations.

NO BAND-AID FIXES: This addresses the ROOT CAUSE of incorrect calculations
by validating data quality at each step and flagging issues for review.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from app.parser.schema import BlueprintSchema, Room, ParsingMetadata

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"  # 90-100% confidence
    GOOD = "good"           # 75-90% confidence
    FAIR = "fair"           # 60-75% confidence
    POOR = "poor"           # 40-60% confidence
    FAILED = "failed"       # <40% confidence


@dataclass
class DataQualityIssue:
    """Individual data quality issue"""
    severity: str  # "critical", "warning", "info"
    category: str  # "area", "floor", "room", "scale", etc.
    message: str
    affected_items: List[str]
    suggested_action: str
    impact_on_calculation: str


@dataclass
class DataQualityReport:
    """Complete data quality validation report"""
    overall_quality: QualityLevel
    overall_confidence: float
    total_issues: int
    critical_issues: int
    warning_issues: int
    issues: List[DataQualityIssue]
    metrics: Dict[str, Any]
    can_proceed: bool
    notes: List[str]


class DataQualityValidator:
    """
    Validates parsed blueprint data quality
    
    ROOT CAUSE FIX: Poor data quality leads to incorrect HVAC calculations.
    This validator ensures data meets minimum quality standards before
    proceeding with calculations.
    """
    
    def __init__(self):
        # Thresholds for validation
        self.min_room_area = 25  # Minimum room area in sqft
        self.max_room_area = 1000  # Maximum residential room area
        self.min_total_area = 500  # Minimum house size
        self.max_total_area = 10000  # Maximum residential size
        self.min_rooms_per_floor = 2  # Minimum rooms per floor
        self.max_area_discrepancy = 0.2  # 20% max discrepancy
    
    def validate_blueprint_quality(self, schema: BlueprintSchema) -> DataQualityReport:
        """
        Comprehensive validation of blueprint data quality
        
        Args:
            schema: Parsed blueprint schema
            
        Returns:
            DataQualityReport with validation results
        """
        issues = []
        metrics = {}
        
        # Validate total area
        area_issues, area_metrics = self._validate_total_area(schema)
        issues.extend(area_issues)
        metrics.update(area_metrics)
        
        # Validate room data
        room_issues, room_metrics = self._validate_rooms(schema.rooms)
        issues.extend(room_issues)
        metrics.update(room_metrics)
        
        # Validate floor assignments
        floor_issues, floor_metrics = self._validate_floor_assignments(schema)
        issues.extend(floor_issues)
        metrics.update(floor_metrics)
        
        # Validate room relationships
        relationship_issues, relationship_metrics = self._validate_room_relationships(schema)
        issues.extend(relationship_issues)
        metrics.update(relationship_metrics)
        
        # Validate parsing metadata
        if schema.parsing_metadata:
            metadata_issues, metadata_metrics = self._validate_parsing_metadata(schema.parsing_metadata)
            issues.extend(metadata_issues)
            metrics.update(metadata_metrics)
        
        # Calculate overall quality
        critical_count = sum(1 for i in issues if i.severity == "critical")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        
        # Determine overall confidence
        confidence = self._calculate_overall_confidence(
            schema, issues, metrics
        )
        
        # Determine quality level
        quality_level = self._determine_quality_level(confidence)
        
        # Determine if we can proceed
        can_proceed = critical_count == 0 and confidence >= 0.4
        
        # Build notes
        notes = self._generate_quality_notes(schema, metrics, issues)
        
        return DataQualityReport(
            overall_quality=quality_level,
            overall_confidence=confidence,
            total_issues=len(issues),
            critical_issues=critical_count,
            warning_issues=warning_count,
            issues=issues,
            metrics=metrics,
            can_proceed=can_proceed,
            notes=notes
        )
    
    def _validate_total_area(self, schema: BlueprintSchema) -> Tuple[List[DataQualityIssue], Dict]:
        """Validate total area calculations"""
        issues = []
        metrics = {}
        
        total_area = schema.sqft_total
        room_area_sum = sum(r.area for r in schema.rooms)
        
        metrics['total_area'] = total_area
        metrics['room_area_sum'] = room_area_sum
        metrics['area_discrepancy'] = abs(total_area - room_area_sum)
        metrics['area_discrepancy_percent'] = (
            abs(total_area - room_area_sum) / total_area * 100 
            if total_area > 0 else 100
        )
        
        # Check total area bounds
        if total_area < self.min_total_area:
            issues.append(DataQualityIssue(
                severity="critical",
                category="area",
                message=f"Total area {total_area:.0f} sqft is below minimum residential size",
                affected_items=["total_area"],
                suggested_action="Check blueprint scale or parsing accuracy",
                impact_on_calculation="HVAC loads will be underestimated"
            ))
        elif total_area > self.max_total_area:
            issues.append(DataQualityIssue(
                severity="warning",
                category="area",
                message=f"Total area {total_area:.0f} sqft exceeds typical residential size",
                affected_items=["total_area"],
                suggested_action="Verify this is a single-family residence",
                impact_on_calculation="May need commercial HVAC calculations"
            ))
        
        # Check area discrepancy
        if metrics['area_discrepancy_percent'] > self.max_area_discrepancy * 100:
            issues.append(DataQualityIssue(
                severity="warning",
                category="area",
                message=f"Room areas sum to {room_area_sum:.0f} sqft but total is {total_area:.0f} sqft ({metrics['area_discrepancy_percent']:.1f}% discrepancy)",
                affected_items=["room_areas", "total_area"],
                suggested_action="Some rooms may be missing or incorrectly sized",
                impact_on_calculation="Load calculations may be inaccurate"
            ))
        
        return issues, metrics
    
    def _validate_rooms(self, rooms: List[Room]) -> Tuple[List[DataQualityIssue], Dict]:
        """Validate individual room data"""
        issues = []
        metrics = {}
        
        metrics['room_count'] = len(rooms)
        metrics['avg_room_area'] = sum(r.area for r in rooms) / len(rooms) if rooms else 0
        metrics['min_room_area'] = min(r.area for r in rooms) if rooms else 0
        metrics['max_room_area'] = max(r.area for r in rooms) if rooms else 0
        
        # Check room count
        if len(rooms) < 3:
            issues.append(DataQualityIssue(
                severity="critical",
                category="room",
                message=f"Only {len(rooms)} rooms detected - too few for residential building",
                affected_items=["room_count"],
                suggested_action="Check blueprint parsing or page selection",
                impact_on_calculation="Cannot calculate accurate HVAC loads"
            ))
        
        # Check individual rooms
        for room in rooms:
            if room.area < self.min_room_area:
                issues.append(DataQualityIssue(
                    severity="warning",
                    category="room",
                    message=f"Room '{room.name}' has very small area: {room.area:.0f} sqft",
                    affected_items=[room.name],
                    suggested_action="Verify room dimensions or consider as closet/utility",
                    impact_on_calculation="May affect zone sizing"
                ))
            elif room.area > self.max_room_area:
                issues.append(DataQualityIssue(
                    severity="critical",
                    category="room",
                    message=f"Room '{room.name}' has unrealistic area: {room.area:.0f} sqft",
                    affected_items=[room.name],
                    suggested_action="Check scale detection or room boundary detection",
                    impact_on_calculation="Will cause significant overestimation of loads"
                ))
        
        # Check for required room types
        has_kitchen = any('kitchen' in r.name.lower() for r in rooms)
        has_bathroom = any('bath' in r.name.lower() for r in rooms)
        has_bedroom = any('bed' in r.name.lower() for r in rooms)
        
        if not has_kitchen:
            issues.append(DataQualityIssue(
                severity="warning",
                category="room",
                message="No kitchen detected in blueprint",
                affected_items=["room_types"],
                suggested_action="Verify main floor was processed correctly",
                impact_on_calculation="Kitchen loads may be missing"
            ))
        
        return issues, metrics
    
    def _validate_floor_assignments(self, schema: BlueprintSchema) -> Tuple[List[DataQualityIssue], Dict]:
        """Validate floor assignments and multi-story structure"""
        issues = []
        metrics = {}
        
        # Group rooms by floor
        floors = {}
        for room in schema.rooms:
            floor_num = room.floor
            if floor_num not in floors:
                floors[floor_num] = []
            floors[floor_num].append(room)
        
        metrics['floors_detected'] = len(floors)
        metrics['declared_stories'] = schema.stories
        
        # Check floor count consistency
        if len(floors) != schema.stories:
            issues.append(DataQualityIssue(
                severity="warning",
                category="floor",
                message=f"Schema declares {schema.stories} stories but {len(floors)} floors detected",
                affected_items=["floor_assignments"],
                suggested_action="Verify floor detection and assignment",
                impact_on_calculation="Multi-story effects may be incorrect"
            ))
        
        # Check each floor
        for floor_num, floor_rooms in floors.items():
            floor_area = sum(r.area for r in floor_rooms)
            
            if len(floor_rooms) < self.min_rooms_per_floor:
                issues.append(DataQualityIssue(
                    severity="warning",
                    category="floor",
                    message=f"Floor {floor_num} has only {len(floor_rooms)} rooms",
                    affected_items=[f"floor_{floor_num}"],
                    suggested_action="Some rooms may be missing from this floor",
                    impact_on_calculation="Floor load distribution may be incorrect"
                ))
            
            metrics[f'floor_{floor_num}_rooms'] = len(floor_rooms)
            metrics[f'floor_{floor_num}_area'] = floor_area
        
        return issues, metrics
    
    def _validate_room_relationships(self, schema: BlueprintSchema) -> Tuple[List[DataQualityIssue], Dict]:
        """Validate relationships between rooms"""
        issues = []
        metrics = {}
        
        # Check for duplicate room names
        room_names = [r.name for r in schema.rooms]
        unique_names = set(room_names)
        
        if len(unique_names) < len(room_names):
            duplicates = [name for name in unique_names if room_names.count(name) > 1]
            issues.append(DataQualityIssue(
                severity="warning",
                category="room",
                message=f"Duplicate room names found: {', '.join(duplicates)}",
                affected_items=duplicates,
                suggested_action="Add floor or location identifiers to room names",
                impact_on_calculation="May cause confusion in zone identification"
            ))
        
        metrics['unique_room_names'] = len(unique_names)
        metrics['duplicate_names'] = len(room_names) - len(unique_names)
        
        return issues, metrics
    
    def _validate_parsing_metadata(self, metadata: ParsingMetadata) -> Tuple[List[DataQualityIssue], Dict]:
        """Validate parsing metadata and confidence"""
        issues = []
        metrics = {}
        
        if hasattr(metadata, 'overall_confidence'):
            confidence = metadata.overall_confidence
            metrics['parsing_confidence'] = confidence
            
            if confidence < 0.5:
                issues.append(DataQualityIssue(
                    severity="warning",
                    category="parsing",
                    message=f"Low parsing confidence: {confidence:.2f}",
                    affected_items=["parsing_quality"],
                    suggested_action="Manual verification recommended",
                    impact_on_calculation="Results may need manual adjustment"
                ))
        
        if hasattr(metadata, 'ai_status'):
            metrics['ai_status'] = metadata.ai_status.value
            if metadata.ai_status.value == "failed":
                issues.append(DataQualityIssue(
                    severity="warning",
                    category="parsing",
                    message="AI analysis failed - using fallback methods",
                    affected_items=["ai_analysis"],
                    suggested_action="Results based on geometry only",
                    impact_on_calculation="Room detection may be less accurate"
                ))
        
        return issues, metrics
    
    def _calculate_overall_confidence(
        self, 
        schema: BlueprintSchema, 
        issues: List[DataQualityIssue],
        metrics: Dict
    ) -> float:
        """Calculate overall data quality confidence"""
        confidence = 1.0
        
        # Reduce confidence for critical issues
        critical_count = sum(1 for i in issues if i.severity == "critical")
        confidence -= critical_count * 0.2
        
        # Reduce confidence for warnings
        warning_count = sum(1 for i in issues if i.severity == "warning")
        confidence -= warning_count * 0.05
        
        # Factor in parsing confidence if available
        if 'parsing_confidence' in metrics:
            confidence *= metrics['parsing_confidence']
        
        # Factor in area discrepancy
        if 'area_discrepancy_percent' in metrics:
            if metrics['area_discrepancy_percent'] > 20:
                confidence *= 0.8
            elif metrics['area_discrepancy_percent'] > 10:
                confidence *= 0.9
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_quality_level(self, confidence: float) -> QualityLevel:
        """Determine quality level from confidence score"""
        if confidence >= 0.9:
            return QualityLevel.EXCELLENT
        elif confidence >= 0.75:
            return QualityLevel.GOOD
        elif confidence >= 0.6:
            return QualityLevel.FAIR
        elif confidence >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAILED
    
    def _generate_quality_notes(
        self, 
        schema: BlueprintSchema,
        metrics: Dict,
        issues: List[DataQualityIssue]
    ) -> List[str]:
        """Generate helpful notes about data quality"""
        notes = []
        
        if metrics.get('parsing_confidence', 1.0) < 0.7:
            notes.append("Consider manual verification of room dimensions")
        
        if metrics.get('area_discrepancy_percent', 0) > 15:
            notes.append("Significant area discrepancy - some rooms may be missing")
        
        if schema.stories > 1 and schema.building_typology:
            if schema.building_typology.get('has_bonus_room'):
                notes.append("Bonus room detected - enhanced load factors applied")
        
        if len(issues) == 0:
            notes.append("Data quality excellent - no issues detected")
        elif all(i.severity != "critical" for i in issues):
            notes.append("Data quality acceptable - minor issues only")
        
        return notes


def validate_blueprint_quality(schema: BlueprintSchema) -> DataQualityReport:
    """
    Convenience function to validate blueprint data quality
    
    Args:
        schema: Parsed blueprint schema
        
    Returns:
        DataQualityReport with validation results
    """
    validator = DataQualityValidator()
    return validator.validate_blueprint_quality(schema)