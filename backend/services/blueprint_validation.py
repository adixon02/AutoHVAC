"""
Blueprint Validation Service
Implements fail-fast validation with user-friendly error messages
"""

from typing import List, Dict, Any, Tuple, Optional
from app.parser.schema import BlueprintSchema, Room
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class BlueprintValidationError(Exception):
    """
    Custom exception for blueprint parsing validation failures
    Includes user-friendly messaging and recovery suggestions
    """
    def __init__(self, error_type: str, message: str, details: Dict[str, Any], 
                 user_actions: List[str], can_continue: bool = False):
        self.error_type = error_type
        self.message = message
        self.details = details
        self.user_actions = user_actions
        self.can_continue = can_continue
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "user_actions": self.user_actions,
            "can_continue": self.can_continue
        }


class ValidationWarning(BaseModel):
    """Non-critical validation issue"""
    warning_type: str
    message: str
    severity: str  # "low", "medium", "high"
    field: Optional[str] = None
    impact: str


class BlueprintValidator:
    """
    Validates blueprint parsing results for quality and completeness
    """
    
    # Minimum requirements by building type
    MIN_ROOMS = {
        "residential": 3,
        "commercial": 2,
        "industrial": 1
    }
    
    # Expected rooms per 1000 sqft
    ROOMS_PER_1000_SQFT = {
        "min": 2,
        "max": 8
    }
    
    # Maximum acceptable area deviation
    MAX_AREA_DEVIATION = 0.30  # 30%
    
    # Minimum orientation detection rate
    MIN_ORIENTATION_RATE = 0.20  # At least 20% of rooms should have orientation
    
    def __init__(self):
        self.warnings: List[ValidationWarning] = []
    
    def validate_blueprint(self, blueprint: BlueprintSchema, 
                          building_type: str = "residential") -> List[ValidationWarning]:
        """
        Perform comprehensive validation of parsed blueprint
        
        Args:
            blueprint: Parsed blueprint schema
            building_type: Type of building (residential, commercial, etc.)
            
        Returns:
            List of validation warnings
            
        Raises:
            BlueprintValidationError: For critical failures
        """
        self.warnings = []
        
        # Critical validations (will raise exceptions)
        self._validate_room_count(blueprint, building_type)
        self._validate_total_area(blueprint)
        
        # Non-critical validations (will add warnings)
        self._validate_room_sizes(blueprint)
        self._validate_orientation_detection(blueprint)
        self._validate_room_types(blueprint)
        self._validate_data_completeness(blueprint)
        
        return self.warnings
    
    def _validate_room_count(self, blueprint: BlueprintSchema, building_type: str):
        """Validate minimum room count"""
        room_count = len(blueprint.rooms)
        min_rooms = self.MIN_ROOMS.get(building_type, 3)
        
        if room_count < min_rooms:
            # Calculate expected room count based on area
            expected_min = int(blueprint.sqft_total / 1000 * self.ROOMS_PER_1000_SQFT["min"])
            expected_max = int(blueprint.sqft_total / 1000 * self.ROOMS_PER_1000_SQFT["max"])
            
            raise BlueprintValidationError(
                error_type="insufficient_rooms",
                message=f"Only {room_count} rooms detected. Minimum {min_rooms} required for {building_type} buildings.",
                details={
                    "detected_rooms": room_count,
                    "minimum_required": min_rooms,
                    "expected_range": (expected_min, expected_max),
                    "total_sqft": blueprint.sqft_total
                },
                user_actions=[
                    "Upload a clearer floor plan with visible room labels",
                    "Ensure all rooms are shown on the selected page",
                    "Check that room boundaries are clearly defined",
                    f"For a {blueprint.sqft_total:.0f} sqft building, we expect {expected_min}-{expected_max} rooms"
                ],
                can_continue=False
            )
        
        # Warning if room count seems unusual
        rooms_per_1000 = room_count / (blueprint.sqft_total / 1000)
        if rooms_per_1000 < self.ROOMS_PER_1000_SQFT["min"] * 0.8:
            self.warnings.append(ValidationWarning(
                warning_type="low_room_density",
                message=f"Room count ({room_count}) seems low for {blueprint.sqft_total:.0f} sqft",
                severity="medium",
                impact="Some rooms may not have been detected"
            ))
    
    def _validate_total_area(self, blueprint: BlueprintSchema):
        """Validate detected area matches declared total"""
        detected_area = sum(room.area for room in blueprint.rooms)
        declared_area = blueprint.sqft_total
        
        if declared_area <= 0:
            return  # Skip if no declared area
        
        deviation = abs(detected_area - declared_area) / declared_area
        
        if deviation > self.MAX_AREA_DEVIATION:
            raise BlueprintValidationError(
                error_type="area_mismatch",
                message=f"Detected room areas ({detected_area:.0f} sqft) differ significantly from expected total ({declared_area:.0f} sqft)",
                details={
                    "detected_area": detected_area,
                    "declared_area": declared_area,
                    "deviation_percent": deviation * 100,
                    "rooms_detected": len(blueprint.rooms)
                },
                user_actions=[
                    "Verify all rooms are visible and labeled in the blueprint",
                    "Check if closets, hallways, or utility rooms were missed",
                    "Ensure the scale or dimensions are clearly marked",
                    "Upload a higher resolution floor plan if text is unclear"
                ],
                can_continue=True  # Allow continuation with warning
            )
        
        elif deviation > 0.15:  # Warning for 15-30% deviation
            self.warnings.append(ValidationWarning(
                warning_type="area_deviation",
                message=f"Detected area differs by {deviation*100:.0f}% from declared total",
                severity="high",
                field="total_area",
                impact="Load calculations may be less accurate"
            ))
    
    def _validate_room_sizes(self, blueprint: BlueprintSchema):
        """Validate individual room sizes are reasonable"""
        for room in blueprint.rooms:
            # Check for unreasonably small rooms
            if room.area < 25:  # Less than 5x5 feet
                self.warnings.append(ValidationWarning(
                    warning_type="tiny_room",
                    message=f"Room '{room.name}' is very small ({room.area:.0f} sqft)",
                    severity="medium",
                    field=room.name,
                    impact="May be a closet or error in detection"
                ))
            
            # Check for unreasonably large rooms
            elif room.area > 1000:  # Over 1000 sqft
                self.warnings.append(ValidationWarning(
                    warning_type="oversized_room",
                    message=f"Room '{room.name}' is very large ({room.area:.0f} sqft)",
                    severity="low",
                    field=room.name,
                    impact="Verify this is a single room, not multiple spaces"
                ))
            
            # Check dimension ratios
            if room.dimensions_ft[0] > 0 and room.dimensions_ft[1] > 0:
                ratio = max(room.dimensions_ft) / min(room.dimensions_ft)
                if ratio > 4:  # Very elongated room
                    self.warnings.append(ValidationWarning(
                        warning_type="unusual_proportions",
                        message=f"Room '{room.name}' has unusual proportions ({room.dimensions_ft[0]:.1f}x{room.dimensions_ft[1]:.1f} ft)",
                        severity="low",
                        field=room.name,
                        impact="Verify room boundaries are correct"
                    ))
    
    def _validate_orientation_detection(self, blueprint: BlueprintSchema):
        """Validate orientation detection rate"""
        rooms_with_orientation = sum(1 for room in blueprint.rooms 
                                   if room.orientation and room.orientation != "unknown")
        total_rooms = len(blueprint.rooms)
        
        if total_rooms > 0:
            orientation_rate = rooms_with_orientation / total_rooms
            
            if orientation_rate < self.MIN_ORIENTATION_RATE and total_rooms >= 3:
                self.warnings.append(ValidationWarning(
                    warning_type="poor_orientation_detection",
                    message=f"Only {rooms_with_orientation} of {total_rooms} rooms have orientation detected",
                    severity="high",
                    impact="Solar heat gains will be averaged, reducing accuracy"
                ))
    
    def _validate_room_types(self, blueprint: BlueprintSchema):
        """Check for expected room types in residential buildings"""
        room_names_lower = [room.name.lower() for room in blueprint.rooms]
        
        # Expected rooms in residential
        expected_rooms = {
            "kitchen": ["kitchen", "kit"],
            "bathroom": ["bath", "bathroom", "powder"],
            "bedroom": ["bedroom", "bed", "master"],
            "living": ["living", "family", "great room"]
        }
        
        missing_types = []
        for room_type, keywords in expected_rooms.items():
            found = any(any(keyword in name for keyword in keywords) 
                       for name in room_names_lower)
            if not found:
                missing_types.append(room_type)
        
        if missing_types:
            self.warnings.append(ValidationWarning(
                warning_type="missing_room_types",
                message=f"Common room types not detected: {', '.join(missing_types)}",
                severity="medium",
                impact="Some rooms may be mislabeled or missing"
            ))
    
    def _validate_data_completeness(self, blueprint: BlueprintSchema):
        """Check for data quality and completeness"""
        # Check confidence levels
        if hasattr(blueprint, 'parsing_metadata'):
            metadata = blueprint.parsing_metadata
            if metadata.overall_confidence < 0.6:
                self.warnings.append(ValidationWarning(
                    warning_type="low_confidence",
                    message=f"Overall parsing confidence is low ({metadata.overall_confidence:.0%})",
                    severity="high",
                    impact="Results may be less reliable"
                ))
        
        # Check for rooms with default/estimated values
        estimated_rooms = sum(1 for room in blueprint.rooms 
                            if hasattr(room, 'dimensions_source') and 
                            room.dimensions_source == 'estimated')
        
        if estimated_rooms > len(blueprint.rooms) * 0.3:
            self.warnings.append(ValidationWarning(
                warning_type="many_estimated_dimensions",
                message=f"{estimated_rooms} rooms have estimated dimensions",
                severity="medium",
                impact="Actual room sizes may differ from estimates"
            ))


def calculate_data_quality_score(blueprint: BlueprintSchema, 
                               warnings: List[ValidationWarning]) -> float:
    """
    Calculate overall data quality score (0-100)
    
    Args:
        blueprint: Parsed blueprint
        warnings: List of validation warnings
        
    Returns:
        Quality score from 0-100
    """
    score = 100.0
    
    # Deduct points for warnings based on severity
    severity_penalties = {
        "low": 5,
        "medium": 10,
        "high": 20
    }
    
    for warning in warnings:
        penalty = severity_penalties.get(warning.severity, 5)
        score -= penalty
    
    # Additional factors
    if blueprint.parsing_metadata:
        # Factor in parsing confidence
        confidence_weight = 0.3
        score = score * (1 - confidence_weight) + \
                blueprint.parsing_metadata.overall_confidence * 100 * confidence_weight
    
    # Ensure score stays in valid range
    return max(0, min(100, score))