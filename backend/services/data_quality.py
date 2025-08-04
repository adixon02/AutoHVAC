"""
Data Quality Reporting Service
Provides comprehensive quality metrics for blueprint parsing and calculations
"""

from typing import List, Dict, Any, Tuple, Optional, Literal
from pydantic import BaseModel, Field
from app.parser.schema import BlueprintSchema, ParsingMetadata
from services.blueprint_validator import ValidationIssue as ValidationWarning
import logging

logger = logging.getLogger(__name__)


class DataQualityReport(BaseModel):
    """Comprehensive data quality report for user transparency"""
    
    # Overall metrics
    overall_score: float = Field(..., description="Overall quality score 0-100")
    status: Literal["good", "warning", "needs_review", "failed"] = Field(..., description="Overall status")
    confidence_level: Literal["high", "medium", "low"] = Field(..., description="Confidence in results")
    
    # Detection metrics
    rooms_detected: int = Field(..., description="Number of rooms detected")
    rooms_expected_range: Tuple[int, int] = Field(..., description="Expected room count range based on sqft")
    room_detection_confidence: float = Field(..., description="Confidence in room detection 0-1")
    room_detection_status: str = Field(..., description="Status message for room detection")
    
    # Area metrics
    detected_area: float = Field(..., description="Total detected room area")
    declared_area: float = Field(..., description="Declared total area")
    area_match_percentage: float = Field(..., description="Percentage match between detected and declared")
    area_validation_status: str = Field(..., description="Status message for area validation")
    
    # Orientation metrics
    rooms_with_orientation: int = Field(..., description="Rooms with detected orientation")
    orientation_detection_rate: float = Field(..., description="Percentage of rooms with orientation")
    orientation_impact: str = Field(..., description="Impact of missing orientations")
    
    # Envelope metrics
    envelope_extraction_success: bool = Field(..., description="Whether envelope extraction succeeded")
    envelope_fields_defaulted: List[str] = Field(default_factory=list, description="Envelope fields that used defaults")
    envelope_confidence: float = Field(..., description="Confidence in envelope data 0-1")
    
    # Quality indicators
    parsing_method: str = Field(..., description="Method used for parsing (gpt4v, traditional)")
    parsing_confidence: float = Field(..., description="Parsing confidence from metadata")
    critical_warnings: List[str] = Field(default_factory=list, description="Critical warnings requiring attention")
    
    # Detailed warnings and defaults
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="All warnings with details")
    defaulted_values: Dict[str, Any] = Field(default_factory=dict, description="Fields that used default values")
    
    # User guidance
    next_steps: List[str] = Field(default_factory=list, description="Actionable steps for user")
    can_request_review: bool = Field(..., description="Whether manual review is available")
    improvement_suggestions: List[str] = Field(default_factory=list, description="How to improve results")
    
    # Impact assessment
    calculation_impact: str = Field(..., description="How data quality affects calculations")
    reliability_assessment: str = Field(..., description="Overall reliability of results")


class QualityMetricsCalculator:
    """Calculate comprehensive quality metrics from parsing results"""
    
    @staticmethod
    def calculate_quality_report(
        blueprint: BlueprintSchema,
        validation_warnings: List[ValidationWarning],
        envelope_data: Optional[Any] = None,
        climate_zone: Optional[str] = None
    ) -> DataQualityReport:
        """
        Generate comprehensive quality report
        
        Args:
            blueprint: Parsed blueprint schema
            validation_warnings: List of validation warnings
            envelope_data: Envelope extraction results (if any)
            climate_zone: Climate zone for context
            
        Returns:
            Comprehensive data quality report
        """
        # Calculate basic metrics
        rooms_detected = len(blueprint.rooms)
        detected_area = sum(room.area for room in blueprint.rooms)
        declared_area = blueprint.sqft_total
        
        # Expected rooms based on area
        rooms_per_1000_sqft_min = 2
        rooms_per_1000_sqft_max = 8
        expected_min = max(3, int(declared_area / 1000 * rooms_per_1000_sqft_min))
        expected_max = int(declared_area / 1000 * rooms_per_1000_sqft_max)
        
        # Room detection confidence
        room_confidence = 1.0
        if rooms_detected < expected_min:
            room_confidence = rooms_detected / expected_min
        elif rooms_detected > expected_max:
            room_confidence = expected_max / rooms_detected
        
        # Area match percentage
        area_match = 0.0
        if declared_area > 0:
            area_match = min(detected_area, declared_area) / max(detected_area, declared_area) * 100
        
        # Orientation detection
        rooms_with_orientation = sum(1 for room in blueprint.rooms 
                                   if room.orientation and room.orientation != "unknown")
        orientation_rate = rooms_with_orientation / rooms_detected if rooms_detected > 0 else 0
        
        # Envelope analysis
        envelope_success = envelope_data is not None and hasattr(envelope_data, 'overall_confidence')
        envelope_confidence = envelope_data.overall_confidence if envelope_success else 0.0
        envelope_defaults = []
        
        if envelope_data:
            # Check which fields are using defaults
            default_checks = [
                ('wall_r_value', 11.0, "Wall insulation"),
                ('roof_r_value', 30.0, "Roof insulation"),
                ('window_u_factor', 0.50, "Window performance"),
                ('infiltration_class', 'code', "Air tightness")
            ]
            
            for field, default_val, desc in default_checks:
                if hasattr(envelope_data, field):
                    value = getattr(envelope_data, field)
                    confidence_field = f"{field.split('_')[0]}_confidence"
                    confidence = getattr(envelope_data, confidence_field, 0.5)
                    
                    if confidence < 0.6 or value == default_val:
                        envelope_defaults.append(desc)
        
        # Calculate overall score
        score = 100.0
        
        # Room detection scoring (30 points)
        room_score = min(30, room_confidence * 30)
        score = score - (30 - room_score)
        
        # Area matching scoring (20 points)
        area_score = min(20, (area_match / 100) * 20)
        score = score - (20 - area_score)
        
        # Orientation scoring (15 points)
        orientation_score = min(15, orientation_rate * 15)
        score = score - (15 - orientation_score)
        
        # Envelope scoring (20 points)
        envelope_score = 20 if envelope_success else 5
        score = score - (20 - envelope_score)
        
        # Warning deductions (15 points)
        warning_deductions = {
            "low": 1,
            "medium": 3,
            "high": 5
        }
        for warning in validation_warnings:
            deduction = warning_deductions.get(warning.severity, 1)
            score = max(0, score - deduction)
        
        # Determine status
        if score >= 80:
            status = "good"
            confidence = "high"
        elif score >= 60:
            status = "warning"
            confidence = "medium"
        elif score >= 40:
            status = "needs_review"
            confidence = "low"
        else:
            status = "failed"
            confidence = "low"
        
        # Generate user guidance
        next_steps = []
        suggestions = []
        
        if rooms_detected < expected_min:
            next_steps.append("Upload a clearer floor plan with all rooms visible")
            suggestions.append("Ensure room labels are clearly readable")
        
        if area_match < 70:
            next_steps.append("Verify all rooms are included in the blueprint")
            suggestions.append("Check if closets, hallways, or utility spaces were missed")
        
        if orientation_rate < 0.2:
            next_steps.append("Include a north arrow or compass on the blueprint")
            suggestions.append("Label exterior walls with cardinal directions")
        
        if not envelope_success:
            suggestions.append("Include construction details or wall sections")
            suggestions.append("Add insulation specifications to the blueprint")
        
        # Critical warnings
        critical_warnings = []
        for warning in validation_warnings:
            if warning.severity == "high":
                critical_warnings.append(warning.message)
        
        # Impact assessment
        if score >= 80:
            calc_impact = "Calculations should be accurate within industry standards"
            reliability = "High reliability - results can be used with confidence"
        elif score >= 60:
            calc_impact = "Calculations may have moderate uncertainty in some areas"
            reliability = "Moderate reliability - review results and consider safety factors"
        else:
            calc_impact = "Calculations may have significant uncertainty"
            reliability = "Low reliability - results should be verified by a professional"
        
        return DataQualityReport(
            overall_score=score,
            status=status,
            confidence_level=confidence,
            
            # Detection metrics
            rooms_detected=rooms_detected,
            rooms_expected_range=(expected_min, expected_max),
            room_detection_confidence=room_confidence,
            room_detection_status=f"{rooms_detected} rooms found (expected {expected_min}-{expected_max})",
            
            # Area metrics
            detected_area=detected_area,
            declared_area=declared_area,
            area_match_percentage=area_match,
            area_validation_status=f"{area_match:.0f}% match between detected and declared area",
            
            # Orientation metrics
            rooms_with_orientation=rooms_with_orientation,
            orientation_detection_rate=orientation_rate,
            orientation_impact="Solar gains will be averaged" if orientation_rate < 0.5 else "Solar gains calculated by orientation",
            
            # Envelope metrics
            envelope_extraction_success=envelope_success,
            envelope_fields_defaulted=envelope_defaults,
            envelope_confidence=envelope_confidence,
            
            # Quality indicators
            parsing_method=blueprint.parsing_metadata.ai_status.value if blueprint.parsing_metadata else "unknown",
            parsing_confidence=blueprint.parsing_metadata.overall_confidence if blueprint.parsing_metadata else 0.5,
            critical_warnings=critical_warnings,
            
            # Warnings and defaults
            warnings=[w.dict() for w in validation_warnings],
            defaulted_values={
                "envelope": envelope_defaults,
                "rooms": [r.name for r in blueprint.rooms if hasattr(r, 'confidence') and r.confidence < 0.6]
            },
            
            # User guidance
            next_steps=next_steps,
            can_request_review=score < 60,
            improvement_suggestions=suggestions,
            
            # Impact assessment
            calculation_impact=calc_impact,
            reliability_assessment=reliability
        )