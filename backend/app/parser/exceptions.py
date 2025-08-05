"""
Custom exceptions for blueprint parsing that require user intervention
"""


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
    
    def __init__(self, walls_found: int = 0, polygons_found: int = 0, confidence: float = 0.0):
        message = "No valid rooms could be detected from blueprint. Manual room definition required."
        details = {
            "error_type": "room_detection_failed",
            "walls_found": walls_found,
            "polygons_found": polygons_found,
            "confidence": confidence,
            "user_action_required": "define_rooms"
        }
        super().__init__(message, details)


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