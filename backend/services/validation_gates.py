"""
Two-Gate Validation System
Gate A: Scale detection (must pass before geometry)
Gate B: Pre-Manual-J validation (must pass before calculations)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Status of a validation gate"""
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


@dataclass
class GateResult:
    """Result from a validation gate check"""
    gate_name: str
    status: GateStatus
    confidence: float  # 0.0 to 1.0
    message: str
    user_action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    can_continue: bool = False


class ValidationGates:
    """
    Two-gate validation system for blueprint processing
    Fails fast on critical issues to avoid wasting computation
    """
    
    # Gate A thresholds
    SCALE_CONFIDENCE_THRESHOLD = 0.95
    MIN_DIMENSION_LABELS = 3  # Minimum dimension labels needed
    
    # Gate B thresholds
    MIN_ROOM_SANITY_RATE = 0.80  # 80% of rooms must pass size checks
    MIN_EXTERIOR_EXPOSURE = 0.01  # At least some exterior exposure
    MAX_AREA_DISCREPANCY = 0.05  # 5% max difference between sum and shell
    
    def __init__(self):
        self.gate_a_result: Optional[GateResult] = None
        self.gate_b_result: Optional[GateResult] = None
    
    def check_gate_a_scale(
        self,
        scale_confidence: float,
        dimension_count: int,
        scale_px_per_ft: Optional[float] = None,
        vector_paths_count: int = 0,
        ocr_text_count: int = 0
    ) -> GateResult:
        """
        Gate A: Scale Detection Gate
        Must pass before any geometry calculations
        
        Args:
            scale_confidence: Confidence in scale detection (0-1)
            dimension_count: Number of dimension labels found
            scale_px_per_ft: Detected scale if available
            vector_paths_count: Number of vector paths in PDF
            ocr_text_count: Number of OCR text elements
            
        Returns:
            GateResult with pass/fail status
        """
        logger.info(f"Gate A Check: scale_conf={scale_confidence:.2f}, dims={dimension_count}, scale={scale_px_per_ft}")
        
        # Check if scale detection passed
        if scale_confidence >= self.SCALE_CONFIDENCE_THRESHOLD and scale_px_per_ft:
            result = GateResult(
                gate_name="Scale Detection",
                status=GateStatus.PASSED,
                confidence=scale_confidence,
                message=f"Scale detected: {scale_px_per_ft:.2f} px/ft with {scale_confidence:.0%} confidence",
                can_continue=True,
                details={
                    "scale_px_per_ft": scale_px_per_ft,
                    "dimension_count": dimension_count,
                    "method": "automatic"
                }
            )
            logger.info(f"✅ Gate A PASSED: {result.message}")
            
        elif dimension_count < self.MIN_DIMENSION_LABELS:
            # Not enough dimension labels to work with
            result = GateResult(
                gate_name="Scale Detection",
                status=GateStatus.FAILED,
                confidence=scale_confidence,
                message=f"Insufficient dimension labels ({dimension_count} found, need {self.MIN_DIMENSION_LABELS}+)",
                user_action="Please provide a known dimension or upload a clearer blueprint",
                can_continue=False,
                details={
                    "dimension_count": dimension_count,
                    "required": self.MIN_DIMENSION_LABELS,
                    "vector_paths": vector_paths_count,
                    "ocr_text": ocr_text_count
                }
            )
            logger.error(f"❌ Gate A FAILED: {result.message}")
            
        else:
            # Have dimensions but low confidence - request user input
            result = GateResult(
                gate_name="Scale Detection",
                status=GateStatus.NEEDS_INPUT,
                confidence=scale_confidence,
                message=f"Scale detection uncertain (confidence: {scale_confidence:.0%})",
                user_action="Please click on a known dimension to calibrate scale",
                can_continue=False,
                details={
                    "dimension_count": dimension_count,
                    "confidence": scale_confidence,
                    "threshold": self.SCALE_CONFIDENCE_THRESHOLD
                }
            )
            logger.warning(f"⚠️ Gate A NEEDS INPUT: {result.message}")
        
        self.gate_a_result = result
        return result
    
    def check_gate_b_pre_manual_j(
        self,
        rooms: List[Dict[str, Any]],
        total_area: float,
        shell_area: float,
        has_exterior_rooms: bool,
        unconditioned_count: int = 0,
        room_sanity_issues: List[str] = None
    ) -> GateResult:
        """
        Gate B: Pre-Manual-J Validation Gate
        Must pass before running HVAC calculations
        
        Args:
            rooms: List of room dictionaries
            total_area: Sum of all room areas
            shell_area: Area of building shell/perimeter
            has_exterior_rooms: Whether exterior rooms were detected
            unconditioned_count: Number of unconditioned spaces
            room_sanity_issues: List of room validation issues
            
        Returns:
            GateResult with pass/fail status
        """
        issues = []
        confidence = 1.0
        
        # Check 1: Room sanity rate
        if room_sanity_issues:
            sanity_rate = 1.0 - (len(room_sanity_issues) / len(rooms))
            if sanity_rate < self.MIN_ROOM_SANITY_RATE:
                issues.append(f"Too many room size issues ({len(room_sanity_issues)}/{len(rooms)})")
                confidence *= sanity_rate
        
        # Check 2: Area consistency
        if shell_area > 0:
            area_discrepancy = abs(total_area - shell_area) / shell_area
            if area_discrepancy > self.MAX_AREA_DISCREPANCY:
                issues.append(f"Room areas don't match shell ({area_discrepancy:.0%} discrepancy)")
                confidence *= (1.0 - area_discrepancy)
        
        # Check 3: Exterior exposure
        if not has_exterior_rooms:
            issues.append("No exterior rooms detected")
            confidence *= 0.5
        
        # Check 4: All rooms are unconditioned
        conditioned_count = len(rooms) - unconditioned_count
        if conditioned_count == 0:
            result = GateResult(
                gate_name="Pre-Manual-J Validation",
                status=GateStatus.FAILED,
                confidence=0.0,
                message="No conditioned rooms found",
                user_action="Check room detection - all rooms appear to be unconditioned",
                can_continue=False,
                details={
                    "total_rooms": len(rooms),
                    "unconditioned": unconditioned_count,
                    "issues": ["no_conditioned_rooms"]
                }
            )
            logger.error(f"❌ Gate B FAILED: {result.message}")
            self.gate_b_result = result
            return result
        
        # Determine overall status
        if not issues:
            result = GateResult(
                gate_name="Pre-Manual-J Validation",
                status=GateStatus.PASSED,
                confidence=confidence,
                message="All validation checks passed",
                can_continue=True,
                details={
                    "rooms": len(rooms),
                    "conditioned": conditioned_count,
                    "unconditioned": unconditioned_count,
                    "area_match": f"{(1-abs(total_area-shell_area)/shell_area):.0%}" if shell_area > 0 else "N/A"
                }
            )
            logger.info(f"✅ Gate B PASSED: {result.message}")
            
        elif len(issues) >= 2 or confidence < 0.5:
            result = GateResult(
                gate_name="Pre-Manual-J Validation",
                status=GateStatus.FAILED,
                confidence=confidence,
                message=f"Multiple validation failures: {'; '.join(issues)}",
                user_action="Review blueprint parsing results before proceeding",
                can_continue=False,
                details={
                    "issues": issues,
                    "rooms": len(rooms),
                    "confidence": confidence
                }
            )
            logger.error(f"❌ Gate B FAILED: {result.message}")
            
        else:
            result = GateResult(
                gate_name="Pre-Manual-J Validation",
                status=GateStatus.NEEDS_INPUT,
                confidence=confidence,
                message=f"Validation warnings: {'; '.join(issues)}",
                user_action="Review and confirm room detection is correct",
                can_continue=True,  # Can continue with warnings
                details={
                    "warnings": issues,
                    "rooms": len(rooms),
                    "confidence": confidence
                }
            )
            logger.warning(f"⚠️ Gate B WARNING: {result.message}")
        
        self.gate_b_result = result
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all gate results"""
        return {
            "gate_a": {
                "name": "Scale Detection",
                "status": self.gate_a_result.status.value if self.gate_a_result else "not_checked",
                "confidence": self.gate_a_result.confidence if self.gate_a_result else 0.0,
                "message": self.gate_a_result.message if self.gate_a_result else "Not checked",
                "can_continue": self.gate_a_result.can_continue if self.gate_a_result else False
            },
            "gate_b": {
                "name": "Pre-Manual-J Validation",
                "status": self.gate_b_result.status.value if self.gate_b_result else "not_checked",
                "confidence": self.gate_b_result.confidence if self.gate_b_result else 0.0,
                "message": self.gate_b_result.message if self.gate_b_result else "Not checked",
                "can_continue": self.gate_b_result.can_continue if self.gate_b_result else False
            },
            "overall_status": self._get_overall_status(),
            "user_actions_required": self._get_user_actions()
        }
    
    def _get_overall_status(self) -> str:
        """Determine overall validation status"""
        if not self.gate_a_result:
            return "not_started"
        
        if self.gate_a_result.status == GateStatus.FAILED:
            return "failed_gate_a"
        
        if self.gate_a_result.status == GateStatus.NEEDS_INPUT:
            return "needs_scale_input"
        
        if not self.gate_b_result:
            return "gate_a_passed"
        
        if self.gate_b_result.status == GateStatus.FAILED:
            return "failed_gate_b"
        
        if self.gate_b_result.status == GateStatus.NEEDS_INPUT:
            return "needs_confirmation"
        
        return "all_gates_passed"
    
    def _get_user_actions(self) -> List[str]:
        """Get list of required user actions"""
        actions = []
        
        if self.gate_a_result and self.gate_a_result.user_action:
            actions.append(self.gate_a_result.user_action)
        
        if self.gate_b_result and self.gate_b_result.user_action:
            actions.append(self.gate_b_result.user_action)
        
        return actions


# Example usage in pipeline:
def process_blueprint_with_gates(pdf_path: str) -> Dict[str, Any]:
    """
    Example of how to use the two-gate system in the pipeline
    """
    gates = ValidationGates()
    
    # Step 1: Extract dimensions and detect scale
    scale_result = extract_scale(pdf_path)  # Your scale extraction
    
    # Gate A: Check scale detection
    gate_a = gates.check_gate_a_scale(
        scale_confidence=scale_result.confidence,
        dimension_count=scale_result.dimension_count,
        scale_px_per_ft=scale_result.scale
    )
    
    if not gate_a.can_continue:
        # Stop here - return needs_input status to frontend
        return {
            "status": "needs_input",
            "gate_failed": "A",
            "message": gate_a.message,
            "user_action": gate_a.user_action,
            "details": gates.get_summary()
        }
    
    # Step 2: Extract geometry using the scale
    geometry = extract_geometry_with_scale(pdf_path, scale_result.scale)
    
    # Step 3: Classify room labels (no numbers from GPT!)
    rooms = classify_room_labels(geometry.rooms)
    
    # Gate B: Pre-Manual-J validation
    gate_b = gates.check_gate_b_pre_manual_j(
        rooms=rooms,
        total_area=sum(r['area'] for r in rooms),
        shell_area=geometry.shell_area,
        has_exterior_rooms=any(r.get('exterior_walls', 0) > 0 for r in rooms)
    )
    
    if not gate_b.can_continue:
        # Stop here - return validation failure
        return {
            "status": "validation_failed",
            "gate_failed": "B",
            "message": gate_b.message,
            "user_action": gate_b.user_action,
            "details": gates.get_summary()
        }
    
    # Both gates passed - proceed with Manual J
    hvac_loads = calculate_manual_j(rooms, geometry)
    
    return {
        "status": "success",
        "validation": gates.get_summary(),
        "hvac_loads": hvac_loads
    }