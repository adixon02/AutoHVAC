"""
Custom exceptions for blueprint parsing that require user intervention
"""

from typing import Optional, Dict

class UserInterventionRequired(Exception):
    """Raised when parsing cannot proceed without user input"""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ScaleNotDetectedError(UserInterventionRequired):
    """Raised when blueprint scale cannot be determined"""
    
    def __init__(self, attempted_methods: list = None):
        message = "Blueprint scale could not be detected. Manual scale entry required."
        details = {
            "error_type": "scale_not_detected",
            "attempted_methods": attempted_methods or [],
            "user_action_required": "enter_scale"
        }
        super().__init__(message, details)


class RoomDetectionFailedError(UserInterventionRequired):
    """Raised when no valid rooms can be detected"""
    
    def __init__(
        self,
        walls_found: int = 0,
        polygons_found: int = 0,
        confidence: float = 0.0,
        message: Optional[str] = None,
        extra_details: Optional[Dict] = None,
    ):
        base_message = (
            message
            or "No valid rooms could be detected from blueprint. Manual room definition required."
        )
        details = {
            "error_type": "room_detection_failed",
            "walls_found": walls_found,
            "polygons_found": polygons_found,
            "confidence": confidence,
            "user_action_required": "define_rooms",
        }
        if extra_details:
            details.update(extra_details)
        super().__init__(base_message, details)


class LowConfidenceError(UserInterventionRequired):
    """Raised when parsing confidence is below acceptable threshold"""
    
    def __init__(self, confidence: float, threshold: float = 0.6, issues: list = None):
        message = f"Parsing confidence ({confidence:.2f}) below threshold ({threshold}). User confirmation required."
        details = {
            "error_type": "low_confidence",
            "confidence": confidence,
            "threshold": threshold,
            "issues": issues or [],
            "user_action_required": "confirm_or_correct"
        }
        super().__init__(message, details)


class ScaleDetectionError(UserInterventionRequired):
    """Raised when blueprint scale cannot be reliably determined"""
    
    def __init__(self, detected_scale: float = None, confidence: float = 0.0, 
                 alternatives: list = None, validation_issues: dict = None):
        if detected_scale:
            message = f"Blueprint scale detection confidence too low ({confidence:.2f}). Detected {detected_scale:.1f} px/ft may be incorrect."
        else:
            message = "Blueprint scale could not be detected. Manual scale entry required."
        
        details = {
            "error_type": "scale_detection_failed",
            "detected_scale": detected_scale,
            "confidence": confidence,
            "alternative_scales": alternatives or [],
            "validation_issues": validation_issues or {},
            "user_action_required": "select_or_enter_scale",
            "common_scales": [
                {"label": "1/8\" = 1'-0\"", "value": 96.0},
                {"label": "3/16\" = 1'-0\"", "value": 64.0},
                {"label": "1/4\" = 1'-0\"", "value": 48.0},
                {"label": "3/8\" = 1'-0\"", "value": 32.0},
                {"label": "1/2\" = 1'-0\"", "value": 24.0},
                {"label": "3/4\" = 1'-0\"", "value": 16.0},
                {"label": "1\" = 1'-0\"", "value": 12.0},
            ]
        }
        super().__init__(message, details)