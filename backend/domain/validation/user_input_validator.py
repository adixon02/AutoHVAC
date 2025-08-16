"""
User Input Validation System

Implements comprehensive validation of user inputs to prevent "garbage in/garbage out"
scenarios that can cause 15-20% accuracy issues in Manual J calculations.

This system provides:
- Sanity checks for square footage vs blueprint detection
- Foundation type consistency validation  
- Building geometry validation
- HVAC system configuration validation
- Climate zone compatibility checks
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Represents a validation issue found in user inputs"""
    field: str
    severity: ValidationSeverity
    message: str
    suggested_fix: Optional[str] = None
    auto_correctable: bool = False

@dataclass
class ValidationResult:
    """Result of user input validation"""
    is_valid: bool
    issues: List[ValidationIssue]
    corrected_inputs: Optional[Dict[str, Any]] = None
    confidence_impact: float = 0.0  # Impact on calculation confidence (0.0-1.0)

class UserInputValidator:
    """
    Comprehensive user input validation system.
    
    Prevents common input errors that can cause significant calculation inaccuracies:
    - Square footage mismatches
    - Foundation type inconsistencies  
    - Building system conflicts
    - Unrealistic building parameters
    """
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
    
    def validate_user_inputs(
        self,
        user_inputs: Dict[str, Any],
        blueprint_data: Dict[str, Any] = None,
        climate_zone: str = None
    ) -> ValidationResult:
        """
        Validate user inputs against blueprint data and building science principles.
        
        Args:
            user_inputs: User-provided building parameters
            blueprint_data: Extracted blueprint data for comparison
            climate_zone: IECC climate zone for compatibility checks
            
        Returns:
            ValidationResult with issues and suggested corrections
        """
        issues = []
        corrected_inputs = user_inputs.copy()
        
        # 1. Square footage validation (Critical)
        sqft_issues = self._validate_square_footage(user_inputs, blueprint_data)
        issues.extend(sqft_issues)
        
        # 2. Foundation type consistency (High Impact)
        foundation_issues = self._validate_foundation_consistency(user_inputs)
        issues.extend(foundation_issues)
        
        # 3. Building geometry validation
        geometry_issues = self._validate_building_geometry(user_inputs)
        issues.extend(geometry_issues)
        
        # 4. HVAC system configuration validation
        hvac_issues = self._validate_hvac_configuration(user_inputs, climate_zone)
        issues.extend(hvac_issues)
        
        # 5. Climate zone compatibility
        if climate_zone:
            climate_issues = self._validate_climate_compatibility(user_inputs, climate_zone)
            issues.extend(climate_issues)
        
        # 6. Apply auto-corrections where possible
        for issue in issues:
            if issue.auto_correctable and issue.suggested_fix:
                corrected_inputs = self._apply_correction(corrected_inputs, issue)
        
        # Calculate validation impact on confidence
        confidence_impact = self._calculate_confidence_impact(issues)
        
        # Determine overall validity
        critical_errors = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        is_valid = len(critical_errors) == 0 and len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            corrected_inputs=corrected_inputs if corrected_inputs != user_inputs else None,
            confidence_impact=confidence_impact
        )
    
    def _validate_square_footage(
        self, 
        user_inputs: Dict[str, Any], 
        blueprint_data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate square footage inputs against blueprint detection"""
        issues = []
        
        user_sqft = user_inputs.get('conditioned_sqft') or user_inputs.get('total_sqft')
        if not user_sqft:
            return issues
        
        try:
            user_sqft = float(user_sqft)
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                field='conditioned_sqft',
                severity=ValidationSeverity.ERROR,
                message=f"Invalid square footage format: {user_sqft}",
                suggested_fix="Provide numeric square footage value"
            ))
            return issues
        
        # Sanity check: Reasonable range for residential
        if user_sqft < 400:
            issues.append(ValidationIssue(
                field='conditioned_sqft',
                severity=ValidationSeverity.WARNING,
                message=f"Square footage {user_sqft:.0f} seems unusually small for residential",
                suggested_fix="Verify square footage measurement"
            ))
        elif user_sqft > 15000:
            issues.append(ValidationIssue(
                field='conditioned_sqft',
                severity=ValidationSeverity.WARNING,
                message=f"Square footage {user_sqft:.0f} seems unusually large for residential",
                suggested_fix="Verify square footage or consider commercial calculator"
            ))
        
        # Compare with blueprint detection if available
        if blueprint_data and 'total_sqft' in blueprint_data:
            blueprint_sqft = blueprint_data['total_sqft']
            if blueprint_sqft > 0:
                ratio = user_sqft / blueprint_sqft
                
                # Flag major discrepancies  
                if ratio > 2.0:
                    issues.append(ValidationIssue(
                        field='conditioned_sqft',
                        severity=ValidationSeverity.CRITICAL,
                        message=f"User input ({user_sqft:.0f} sqft) is {ratio:.1f}x larger than blueprint detection ({blueprint_sqft:.0f} sqft)",
                        suggested_fix=f"Verify square footage - consider using blueprint detected value: {blueprint_sqft:.0f} sqft"
                    ))
                elif ratio < 0.5:
                    issues.append(ValidationIssue(
                        field='conditioned_sqft',
                        severity=ValidationSeverity.WARNING,
                        message=f"User input ({user_sqft:.0f} sqft) is much smaller than blueprint detection ({blueprint_sqft:.0f} sqft)",
                        suggested_fix="Verify if input includes only conditioned space"
                    ))
                elif ratio > 1.3 or ratio < 0.7:
                    issues.append(ValidationIssue(
                        field='conditioned_sqft',
                        severity=ValidationSeverity.INFO,
                        message=f"User input ({user_sqft:.0f} sqft) differs from blueprint detection ({blueprint_sqft:.0f} sqft) by {abs(1-ratio)*100:.1f}%",
                        suggested_fix="Consider if discrepancy is due to unconditioned spaces"
                    ))
        
        return issues
    
    def _validate_foundation_consistency(self, user_inputs: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate foundation type consistency with basement inputs"""
        issues = []
        
        foundation_type = user_inputs.get('foundation_type')
        basement_type = user_inputs.get('basement_type')
        basement_status = user_inputs.get('basement_status')
        
        if not foundation_type:
            return issues
        
        # Critical inconsistency: Slab foundation with basement info
        if foundation_type == 'slab_only' or foundation_type == 'slab_on_grade':
            if basement_type or basement_status:
                issues.append(ValidationIssue(
                    field='foundation_type',
                    severity=ValidationSeverity.CRITICAL,
                    message="Slab-on-grade foundation cannot have basement type or status",
                    suggested_fix="Remove basement information or change foundation type",
                    auto_correctable=True
                ))
        
        # Crawlspace with basement info  
        elif foundation_type == 'crawlspace':
            if basement_type or basement_status:
                issues.append(ValidationIssue(
                    field='foundation_type',
                    severity=ValidationSeverity.ERROR,
                    message="Crawlspace foundation should not have basement type or status",
                    suggested_fix="Remove basement information or change to basement foundation",
                    auto_correctable=True
                ))
        
        # Basement foundation missing required info
        elif foundation_type == 'basement_with_slab':
            if not basement_type:
                issues.append(ValidationIssue(
                    field='basement_type',
                    severity=ValidationSeverity.WARNING,
                    message="Basement foundation should specify basement type",
                    suggested_fix="Specify basement type (full, daylight, walkout)"
                ))
            
            if not basement_status:
                issues.append(ValidationIssue(
                    field='basement_status',
                    severity=ValidationSeverity.WARNING,
                    message="Basement foundation should specify if finished or unfinished",
                    suggested_fix="Specify basement status (finished/unfinished)"
                ))
        
        return issues
    
    def _validate_building_geometry(self, user_inputs: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate building geometry and proportions"""
        issues = []
        
        stories = user_inputs.get('number_of_stories')
        sqft = user_inputs.get('conditioned_sqft') or user_inputs.get('total_sqft')
        
        if stories and sqft:
            try:
                stories = int(stories)
                sqft = float(sqft)
                
                # Validate story count
                if stories < 1:
                    issues.append(ValidationIssue(
                        field='number_of_stories',
                        severity=ValidationSeverity.ERROR,
                        message="Number of stories must be at least 1",
                        suggested_fix="Use 1 for single-story buildings"
                    ))
                elif stories > 4:
                    issues.append(ValidationIssue(
                        field='number_of_stories',
                        severity=ValidationSeverity.WARNING,
                        message=f"{stories} stories is unusual for residential",
                        suggested_fix="Verify story count for residential building"
                    ))
                
                # Validate reasonable floor area per story
                if stories > 0:
                    area_per_story = sqft / stories
                    if area_per_story < 300:
                        issues.append(ValidationIssue(
                            field='conditioned_sqft',
                            severity=ValidationSeverity.WARNING,
                            message=f"Average {area_per_story:.0f} sqft per story seems small",
                            suggested_fix="Verify total square footage and story count"
                        ))
                    elif area_per_story > 6000:
                        issues.append(ValidationIssue(
                            field='conditioned_sqft',
                            severity=ValidationSeverity.WARNING,
                            message=f"Average {area_per_story:.0f} sqft per story seems large",
                            suggested_fix="Verify if this includes unconditioned space"
                        ))
                        
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field='number_of_stories',
                    severity=ValidationSeverity.ERROR,
                    message="Invalid number of stories format",
                    suggested_fix="Provide numeric value for stories"
                ))
        
        return issues
    
    def _validate_hvac_configuration(self, user_inputs: Dict[str, Any], climate_zone: str) -> List[ValidationIssue]:
        """Validate HVAC system configuration"""
        issues = []
        
        system_type = user_inputs.get('system_type')
        duct_location = user_inputs.get('duct_location')
        heating_fuel = user_inputs.get('heating_fuel')
        foundation_type = user_inputs.get('foundation_type')
        
        # Ductless system with duct location
        if system_type == 'ductless':
            if duct_location and duct_location != 'not_applicable':
                issues.append(ValidationIssue(
                    field='duct_location',
                    severity=ValidationSeverity.ERROR,
                    message="Ductless system cannot have duct location",
                    suggested_fix="Remove duct location or change to ducted system",
                    auto_correctable=True
                ))
        
        # Ducted system without duct location
        elif system_type == 'ducted':
            if not duct_location or duct_location == 'not_applicable':
                issues.append(ValidationIssue(
                    field='duct_location',
                    severity=ValidationSeverity.WARNING,
                    message="Ducted system should specify duct location",
                    suggested_fix="Specify duct location (attic, crawlspace, basement, etc.)"
                ))
        
        # Duct location vs foundation consistency
        if duct_location == 'crawlspace' and foundation_type == 'slab_only':
            issues.append(ValidationIssue(
                field='duct_location',
                severity=ValidationSeverity.ERROR,
                message="Cannot have crawlspace ducts with slab-on-grade foundation",
                suggested_fix="Change duct location or foundation type"
            ))
        
        if duct_location == 'basement' and foundation_type != 'basement_with_slab':
            issues.append(ValidationIssue(
                field='duct_location',
                severity=ValidationSeverity.ERROR,
                message="Cannot have basement ducts without basement foundation",
                suggested_fix="Change duct location or foundation type"
            ))
        
        return issues
    
    def _validate_climate_compatibility(self, user_inputs: Dict[str, Any], climate_zone: str) -> List[ValidationIssue]:
        """Validate inputs against climate zone requirements"""
        issues = []
        
        heating_fuel = user_inputs.get('heating_fuel')
        
        # Heat pump in very cold climates
        if heating_fuel == 'heat_pump' and climate_zone.startswith(('7', '8')):
            issues.append(ValidationIssue(
                field='heating_fuel',
                severity=ValidationSeverity.WARNING,
                message=f"Heat pump heating in climate zone {climate_zone} may require backup heating",
                suggested_fix="Consider dual-fuel system for extreme cold climates"
            ))
        
        return issues
    
    def _apply_correction(self, inputs: Dict[str, Any], issue: ValidationIssue) -> Dict[str, Any]:
        """Apply automatic correction for auto-correctable issues"""
        corrected = inputs.copy()
        
        # Auto-correct foundation inconsistencies
        if issue.field == 'foundation_type' and issue.auto_correctable:
            foundation_type = inputs.get('foundation_type')
            if foundation_type in ['slab_only', 'slab_on_grade']:
                # Remove basement info for slab foundations
                corrected.pop('basement_type', None)
                corrected.pop('basement_status', None)
                logger.info("Auto-corrected: Removed basement info for slab foundation")
        
        # Auto-correct HVAC inconsistencies
        elif issue.field == 'duct_location' and issue.auto_correctable:
            system_type = inputs.get('system_type')
            if system_type == 'ductless':
                corrected['duct_location'] = None
                logger.info("Auto-corrected: Removed duct location for ductless system")
        
        return corrected
    
    def _calculate_confidence_impact(self, issues: List[ValidationIssue]) -> float:
        """Calculate impact of validation issues on calculation confidence"""
        impact = 0.0
        
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                impact += 0.3  # 30% confidence reduction
            elif issue.severity == ValidationSeverity.ERROR:
                impact += 0.15  # 15% confidence reduction
            elif issue.severity == ValidationSeverity.WARNING:
                impact += 0.05  # 5% confidence reduction
        
        return min(impact, 1.0)  # Cap at 100% impact
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules and thresholds"""
        return {
            'sqft_min': 400,
            'sqft_max': 15000,
            'stories_max': 4,
            'sqft_per_story_min': 300,
            'sqft_per_story_max': 6000,
            'blueprint_variance_warning': 0.3,  # 30%
            'blueprint_variance_critical': 2.0,  # 200%
        }


def validate_user_inputs(
    user_inputs: Dict[str, Any],
    blueprint_data: Dict[str, Any] = None,
    climate_zone: str = None
) -> ValidationResult:
    """
    Convenience function for user input validation.
    
    Args:
        user_inputs: User-provided parameters
        blueprint_data: Blueprint extraction results  
        climate_zone: IECC climate zone
        
    Returns:
        ValidationResult with issues and corrections
    """
    validator = UserInputValidator()
    return validator.validate_user_inputs(user_inputs, blueprint_data, climate_zone)