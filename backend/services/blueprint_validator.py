"""
Blueprint validation module for sanity checking dimensions and calculations

This module provides comprehensive validation of blueprint parsing results
to catch dimension errors, suspicious areas, and calculation issues.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from app.parser.schema import BlueprintSchema, Room

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"      # Critical issue that invalidates results
    WARNING = "warning"  # Suspicious but possibly valid
    INFO = "info"       # Informational notice


@dataclass
class ValidationIssue:
    """A single validation issue found"""
    severity: ValidationSeverity
    category: str
    message: str
    details: Dict[str, Any]
    suggested_fix: str
    affected_room: Optional[str] = None


@dataclass
class ValidationResult:
    """Overall validation result"""
    is_valid: bool
    issues: List[ValidationIssue]
    total_area_calculated: float
    total_area_declared: float
    room_count: int
    scale_found: bool
    confidence_score: float  # 0-1 overall confidence


class BlueprintValidationError(Exception):
    """
    Custom exception for blueprint parsing validation failures
    Includes user-friendly messaging and recovery suggestions
    """
    def __init__(self, error_type: str, message: str, details: Dict[str, Any], 
                 recovery_suggestions: List[str] = None):
        self.error_type = error_type
        self.message = message
        self.details = details
        self.recovery_suggestions = recovery_suggestions or []
        super().__init__(self.message)


def calculate_data_quality_score(blueprint: BlueprintSchema, 
                               warnings: List[ValidationIssue]) -> float:
    """
    Calculate overall data quality score (0-100)
    
    Args:
        blueprint: The parsed blueprint
        warnings: List of validation warnings/issues
        
    Returns:
        float: Data quality score from 0 to 100
    """
    # Start with perfect score
    score = 100.0
    
    # Deduct points for warnings based on severity
    for warning in warnings:
        if warning.severity == ValidationSeverity.ERROR:
            score -= 20.0  # Major deduction for errors
        elif warning.severity == ValidationSeverity.WARNING:
            score -= 10.0  # Moderate deduction for warnings
        elif warning.severity == ValidationSeverity.INFO:
            score -= 2.0   # Minor deduction for info
    
    # Additional factors
    if hasattr(blueprint, 'parsing_metadata') and blueprint.parsing_metadata:
        # Deduct for low confidence
        avg_confidence = blueprint.parsing_metadata.overall_confidence or 0.5
        if avg_confidence < 0.7:
            score -= (0.7 - avg_confidence) * 20  # Up to 14 points for low confidence
        
        # Deduct for missing data
        if blueprint.parsing_metadata.geometry_status == "failed":
            score -= 15.0
        if blueprint.parsing_metadata.text_status == "failed":
            score -= 10.0
    
    # Ensure score stays in valid range
    return max(0.0, min(100.0, score))


class BlueprintValidator:
    """Validates blueprint parsing results for accuracy and sanity"""
    
    # Residential room size limits (sq ft)
    ROOM_SIZE_LIMITS = {
        "bedroom": (70, 400),
        "master_bedroom": (120, 600),
        "bathroom": (20, 150),
        "kitchen": (70, 400),
        "living": (150, 600),
        "great_room": (300, 1000),
        "dining": (100, 400),
        "closet": (10, 100),
        "hallway": (20, 200),
        "laundry": (30, 150),
        "garage": (200, 1200),
        "unknown": (20, 800)
    }
    
    # Building size limits
    MAX_RESIDENTIAL_AREA = 10000  # sq ft
    MIN_RESIDENTIAL_AREA = 400    # sq ft
    
    # HVAC calculation limits
    MIN_BTU_PER_SQFT_HEATING = 15
    MAX_BTU_PER_SQFT_HEATING = 60
    MIN_BTU_PER_SQFT_COOLING = 15
    MAX_BTU_PER_SQFT_COOLING = 50
    
    # Equipment sizing (sq ft per ton)
    MIN_SQFT_PER_TON = 400
    MAX_SQFT_PER_TON = 800
    
    def validate_blueprint(self, blueprint: BlueprintSchema) -> ValidationResult:
        """Perform comprehensive validation of blueprint data"""
        issues = []
        
        # Extract scale information if available
        scale_found = False
        if hasattr(blueprint, 'raw_geometry') and blueprint.raw_geometry:
            scale_found = blueprint.raw_geometry.get('scale_found', False)
        
        # Validate individual rooms
        total_area_calculated = 0
        suspicious_rooms = []
        
        for room in blueprint.rooms:
            room_issues = self._validate_room(room)
            issues.extend(room_issues)
            
            total_area_calculated += room.area
            
            # Track suspicious rooms
            if room.area > self.ROOM_SIZE_LIMITS.get(room.room_type, (20, 800))[1]:
                suspicious_rooms.append(room.name)
        
        # Validate total area
        total_area_declared = blueprint.sqft_total
        area_issues = self._validate_total_area(
            total_area_calculated, 
            total_area_declared,
            len(blueprint.rooms)
        )
        issues.extend(area_issues)
        
        # Check room count
        room_count_issues = self._validate_room_count(
            len(blueprint.rooms),
            total_area_declared
        )
        issues.extend(room_count_issues)
        
        # Add scale warning if not found
        if not scale_found:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="scale",
                message="No scale found on blueprint",
                details={"scale_found": False},
                suggested_fix="Manually verify room dimensions or provide scale information"
            ))
        
        # Calculate overall confidence
        confidence_score = self._calculate_confidence(issues, blueprint.rooms)
        
        # Determine if valid
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        is_valid = error_count == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            total_area_calculated=total_area_calculated,
            total_area_declared=total_area_declared,
            room_count=len(blueprint.rooms),
            scale_found=scale_found,
            confidence_score=confidence_score
        )
    
    def _validate_room(self, room: Room) -> List[ValidationIssue]:
        """Validate individual room dimensions and properties"""
        issues = []
        
        # Get size limits for room type
        min_size, max_size = self.ROOM_SIZE_LIMITS.get(
            room.room_type, 
            self.ROOM_SIZE_LIMITS["unknown"]
        )
        
        # Check area against typical sizes
        if room.area < min_size:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="room_size",
                message=f"Room '{room.name}' is unusually small",
                details={
                    "area": room.area,
                    "min_expected": min_size,
                    "room_type": room.room_type
                },
                suggested_fix=f"Verify dimensions - typical {room.room_type} is {min_size}-{max_size} sq ft",
                affected_room=room.name
            ))
        elif room.area > max_size:
            # Great rooms can be larger
            severity = ValidationSeverity.WARNING if room.room_type == "great_room" else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                severity=severity,
                category="room_size",
                message=f"Room '{room.name}' is suspiciously large",
                details={
                    "area": room.area,
                    "max_expected": max_size,
                    "room_type": room.room_type
                },
                suggested_fix=f"Check for scale error - typical {room.room_type} is {min_size}-{max_size} sq ft",
                affected_room=room.name
            ))
        
        # Validate dimensions produce correct area
        width, height = room.dimensions_ft
        calculated_area = width * height
        area_diff_pct = abs(calculated_area - room.area) / room.area * 100 if room.area > 0 else 100
        
        if area_diff_pct > 5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="dimension_mismatch",
                message=f"Room '{room.name}' dimensions don't match area",
                details={
                    "dimensions": f"{width}x{height}",
                    "calculated_area": calculated_area,
                    "declared_area": room.area,
                    "difference_pct": area_diff_pct
                },
                suggested_fix="Verify room dimensions are correct",
                affected_room=room.name
            ))
        
        # Check confidence
        if room.confidence < 0.3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="low_confidence",
                message=f"Low confidence for room '{room.name}'",
                details={
                    "confidence": room.confidence,
                    "dimension_source": room.dimensions_source
                },
                suggested_fix="Consider manual verification of this room",
                affected_room=room.name
            ))
        
        return issues
    
    def _validate_total_area(self, calculated: float, declared: float, room_count: int) -> List[ValidationIssue]:
        """Validate total building area"""
        issues = []
        
        # Check absolute limits
        if declared > self.MAX_RESIDENTIAL_AREA:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="building_size",
                message="Building area exceeds residential maximum",
                details={
                    "total_area": declared,
                    "max_residential": self.MAX_RESIDENTIAL_AREA
                },
                suggested_fix="Verify this is a residential building or check for scale errors"
            ))
        
        if declared < self.MIN_RESIDENTIAL_AREA:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="building_size",
                message="Building area below residential minimum",
                details={
                    "total_area": declared,
                    "min_residential": self.MIN_RESIDENTIAL_AREA
                },
                suggested_fix="Verify building size or check for missing rooms"
            ))
        
        # Check calculated vs declared
        if declared > 0:
            diff_pct = abs(calculated - declared) / declared * 100
            if diff_pct > 20:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="area_mismatch",
                    message="Calculated area differs significantly from declared",
                    details={
                        "calculated": calculated,
                        "declared": declared,
                        "difference_pct": diff_pct,
                        "room_count": room_count
                    },
                    suggested_fix="Check for missing rooms or dimension errors"
                ))
        
        return issues
    
    def _validate_room_count(self, room_count: int, total_area: float) -> List[ValidationIssue]:
        """Validate room count against building size"""
        issues = []
        
        # Expected room counts by building size
        if total_area < 1500:
            expected_range = (6, 12)
        elif total_area < 2500:
            expected_range = (10, 18)
        else:
            expected_range = (15, 30)
        
        if room_count < expected_range[0]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="room_count",
                message="Fewer rooms detected than expected",
                details={
                    "detected": room_count,
                    "expected_min": expected_range[0],
                    "building_size": total_area
                },
                suggested_fix="Check for missed rooms (closets, bathrooms, utility rooms)"
            ))
        elif room_count > expected_range[1]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="room_count",
                message="More rooms detected than typical",
                details={
                    "detected": room_count,
                    "expected_max": expected_range[1],
                    "building_size": total_area
                },
                suggested_fix="Verify all detected spaces are actual rooms"
            ))
        
        return issues
    
    def validate_hvac_calculations(self, 
                                 total_area: float,
                                 heating_btu: float,
                                 cooling_btu: float) -> List[ValidationIssue]:
        """Validate HVAC load calculations"""
        issues = []
        
        if total_area <= 0:
            return issues
        
        # Check BTU per square foot
        heating_per_sqft = heating_btu / total_area
        cooling_per_sqft = cooling_btu / total_area
        
        # Heating validation
        if heating_per_sqft < self.MIN_BTU_PER_SQFT_HEATING:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="hvac_calculation",
                message="Heating load suspiciously low",
                details={
                    "btu_per_sqft": heating_per_sqft,
                    "min_expected": self.MIN_BTU_PER_SQFT_HEATING,
                    "total_heating": heating_btu
                },
                suggested_fix="Check room dimensions - loads appear too low for building size"
            ))
        elif heating_per_sqft > self.MAX_BTU_PER_SQFT_HEATING:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="hvac_calculation",
                message="Heating load suspiciously high",
                details={
                    "btu_per_sqft": heating_per_sqft,
                    "max_expected": self.MAX_BTU_PER_SQFT_HEATING,
                    "total_heating": heating_btu
                },
                suggested_fix="Check for dimension errors - loads appear too high"
            ))
        
        # Cooling validation
        if cooling_per_sqft < self.MIN_BTU_PER_SQFT_COOLING:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="hvac_calculation",
                message="Cooling load suspiciously low",
                details={
                    "btu_per_sqft": cooling_per_sqft,
                    "min_expected": self.MIN_BTU_PER_SQFT_COOLING,
                    "total_cooling": cooling_btu
                },
                suggested_fix="Check room dimensions - loads appear too low for building size"
            ))
        elif cooling_per_sqft > self.MAX_BTU_PER_SQFT_COOLING:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="hvac_calculation",
                message="Cooling load suspiciously high",
                details={
                    "btu_per_sqft": cooling_per_sqft,
                    "max_expected": self.MAX_BTU_PER_SQFT_COOLING,
                    "total_cooling": cooling_btu
                },
                suggested_fix="Check for dimension errors - loads appear too high"
            ))
        
        # Equipment sizing validation
        cooling_tons = cooling_btu / 12000
        sqft_per_ton = total_area / cooling_tons if cooling_tons > 0 else 0
        
        if sqft_per_ton < self.MIN_SQFT_PER_TON:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="equipment_sizing",
                message="System appears oversized",
                details={
                    "cooling_tons": cooling_tons,
                    "sqft_per_ton": sqft_per_ton,
                    "min_expected": self.MIN_SQFT_PER_TON
                },
                suggested_fix=f"Typical residential is {self.MIN_SQFT_PER_TON}-{self.MAX_SQFT_PER_TON} sq ft per ton"
            ))
        elif sqft_per_ton > self.MAX_SQFT_PER_TON:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="equipment_sizing",
                message="System may be undersized",
                details={
                    "cooling_tons": cooling_tons,
                    "sqft_per_ton": sqft_per_ton,
                    "max_expected": self.MAX_SQFT_PER_TON
                },
                suggested_fix=f"Typical residential is {self.MIN_SQFT_PER_TON}-{self.MAX_SQFT_PER_TON} sq ft per ton"
            ))
        
        return issues
    
    def _calculate_confidence(self, issues: List[ValidationIssue], rooms: List[Room]) -> float:
        """Calculate overall confidence score"""
        # Start with base confidence from room averages
        if not rooms:
            return 0.0
        
        avg_room_confidence = sum(room.confidence for room in rooms) / len(rooms)
        
        # Reduce for issues
        error_penalty = sum(0.2 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_penalty = sum(0.05 for issue in issues if issue.severity == ValidationSeverity.WARNING)
        
        confidence = avg_room_confidence - error_penalty - warning_penalty
        
        return max(0.0, min(1.0, confidence))