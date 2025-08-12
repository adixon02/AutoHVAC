"""
Room size and type validation for HVAC calculations
Ensures room dimensions are within reasonable bounds
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RoomConstraints:
    """Size constraints for a room type"""
    min_area: float
    max_area: float
    typical_area: float
    min_width: float = 3.0  # Minimum 3 ft width for any room


# Room size constraints based on residential standards (sq ft)
ROOM_SIZE_CONSTRAINTS = {
    'closet': RoomConstraints(min_area=10, max_area=100, typical_area=30),
    'bathroom': RoomConstraints(min_area=30, max_area=200, typical_area=60),
    'powder': RoomConstraints(min_area=20, max_area=50, typical_area=30),
    'bedroom': RoomConstraints(min_area=80, max_area=500, typical_area=150),
    'master': RoomConstraints(min_area=120, max_area=600, typical_area=250),
    'kitchen': RoomConstraints(min_area=60, max_area=400, typical_area=200),
    'living': RoomConstraints(min_area=120, max_area=600, typical_area=300),
    'dining': RoomConstraints(min_area=80, max_area=400, typical_area=180),
    'office': RoomConstraints(min_area=60, max_area=300, typical_area=120),
    'hallway': RoomConstraints(min_area=20, max_area=200, typical_area=60, min_width=3.0),
    'garage': RoomConstraints(min_area=200, max_area=1000, typical_area=400),
    'utility': RoomConstraints(min_area=30, max_area=150, typical_area=60),
    'laundry': RoomConstraints(min_area=30, max_area=100, typical_area=50),
    'pantry': RoomConstraints(min_area=15, max_area=80, typical_area=40),
    'bonus': RoomConstraints(min_area=150, max_area=800, typical_area=350),
    'basement': RoomConstraints(min_area=200, max_area=2000, typical_area=800),
    'attic': RoomConstraints(min_area=100, max_area=1000, typical_area=400),
}


@dataclass
class ValidationIssue:
    """A validation issue found in room data"""
    severity: str  # 'critical', 'warning', 'info'
    room_name: str
    message: str
    action: str
    details: Dict[str, Any]


class RoomValidator:
    """Validates room sizes and types for sanity"""
    
    def __init__(self):
        self.critical_issues = []
        self.warnings = []
        self.info = []
    
    def validate_rooms(self, rooms: List[Any]) -> List[ValidationIssue]:
        """
        Validate all rooms against size constraints
        
        Args:
            rooms: List of Room objects
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        for room in rooms:
            room_issues = self._validate_single_room(room)
            issues.extend(room_issues)
        
        # Check for duplicate room detection
        room_names = [r.name.lower() for r in rooms]
        for name in set(room_names):
            count = room_names.count(name)
            if count > 3 and 'bedroom' not in name and 'bathroom' not in name:
                issues.append(ValidationIssue(
                    severity='warning',
                    room_name=name,
                    message=f"Found {count} rooms named '{name}'",
                    action="Check if rooms were duplicated in parsing",
                    details={'count': count}
                ))
        
        # Sort by severity
        issues.sort(key=lambda x: {'critical': 0, 'warning': 1, 'info': 2}[x.severity])
        
        # Store by severity
        self.critical_issues = [i for i in issues if i.severity == 'critical']
        self.warnings = [i for i in issues if i.severity == 'warning']
        self.info = [i for i in issues if i.severity == 'info']
        
        return issues
    
    def _validate_single_room(self, room: Any) -> List[ValidationIssue]:
        """Validate a single room"""
        issues = []
        
        # Determine room type from name
        room_type = self._get_room_type(room.name)
        constraints = ROOM_SIZE_CONSTRAINTS.get(room_type)
        
        if not constraints:
            # Unknown room type - use general bounds
            if room.area < 10:
                issues.append(ValidationIssue(
                    severity='critical',
                    room_name=room.name,
                    message=f"Room area {room.area:.0f} sqft is impossibly small",
                    action="Check scale detection or room parsing",
                    details={'area': room.area, 'min_expected': 10}
                ))
            elif room.area > 1000:
                issues.append(ValidationIssue(
                    severity='warning',
                    room_name=room.name,
                    message=f"Room area {room.area:.0f} sqft is unusually large",
                    action="Verify this is a single room, not combined spaces",
                    details={'area': room.area, 'max_expected': 1000}
                ))
        else:
            # Check against specific constraints
            if room.area < constraints.min_area:
                issues.append(ValidationIssue(
                    severity='critical',
                    room_name=room.name,
                    message=f"{room_type.title()} area {room.area:.0f} sqft below minimum {constraints.min_area}",
                    action="Verify room type classification or check scale",
                    details={
                        'area': room.area,
                        'min_area': constraints.min_area,
                        'room_type': room_type
                    }
                ))
            elif room.area > constraints.max_area:
                severity = 'warning' if room.area < constraints.max_area * 1.5 else 'critical'
                issues.append(ValidationIssue(
                    severity=severity,
                    room_name=room.name,
                    message=f"{room_type.title()} area {room.area:.0f} sqft exceeds maximum {constraints.max_area}",
                    action="Check if multiple rooms were combined",
                    details={
                        'area': room.area,
                        'max_area': constraints.max_area,
                        'room_type': room_type
                    }
                ))
            
            # Check dimensions if available
            if hasattr(room, 'dimensions_ft') and room.dimensions_ft:
                width = min(room.dimensions_ft)
                length = max(room.dimensions_ft)
                
                if width < constraints.min_width:
                    issues.append(ValidationIssue(
                        severity='warning',
                        room_name=room.name,
                        message=f"Room width {width:.1f} ft below minimum {constraints.min_width} ft",
                        action="Verify dimensions are correct",
                        details={'width': width, 'min_width': constraints.min_width}
                    ))
                
                # Check aspect ratio
                if length > 0:
                    aspect_ratio = length / width if width > 0 else 999
                    if aspect_ratio > 5:
                        issues.append(ValidationIssue(
                            severity='warning',
                            room_name=room.name,
                            message=f"Unusual aspect ratio {aspect_ratio:.1f}:1",
                            action="Verify room is not a hallway or combined space",
                            details={'aspect_ratio': aspect_ratio}
                        ))
        
        return issues
    
    def _get_room_type(self, room_name: str) -> str:
        """Determine room type from name"""
        name_lower = room_name.lower()
        
        # Check for specific room types
        if 'closet' in name_lower or 'clos' in name_lower:
            return 'closet'
        elif 'bath' in name_lower:
            if 'powder' in name_lower or 'half' in name_lower:
                return 'powder'
            elif 'master' in name_lower or 'primary' in name_lower:
                return 'bathroom'  # Master bath
            return 'bathroom'
        elif 'bed' in name_lower or 'br' in name_lower:
            if 'master' in name_lower or 'primary' in name_lower:
                return 'master'
            return 'bedroom'
        elif 'kitchen' in name_lower or 'kit' in name_lower:
            return 'kitchen'
        elif 'living' in name_lower or 'great' in name_lower or 'family' in name_lower:
            return 'living'
        elif 'dining' in name_lower or 'dinette' in name_lower:
            return 'dining'
        elif 'office' in name_lower or 'study' in name_lower or 'den' in name_lower:
            return 'office'
        elif 'hall' in name_lower:
            return 'hallway'
        elif 'garage' in name_lower:
            return 'garage'
        elif 'utility' in name_lower or 'mech' in name_lower:
            return 'utility'
        elif 'laundry' in name_lower or 'wash' in name_lower:
            return 'laundry'
        elif 'pantry' in name_lower:
            return 'pantry'
        elif 'bonus' in name_lower:
            return 'bonus'
        elif 'basement' in name_lower or 'lower' in name_lower:
            return 'basement'
        elif 'attic' in name_lower:
            return 'attic'
        
        return 'other'
    
    def should_stop_pipeline(self) -> bool:
        """Determine if pipeline should stop due to critical issues"""
        return len(self.critical_issues) > 0
    
    def get_summary(self) -> str:
        """Get validation summary"""
        if self.critical_issues:
            return f"CRITICAL: {len(self.critical_issues)} critical issues found - pipeline should stop"
        elif self.warnings:
            return f"WARNING: {len(self.warnings)} warnings found - review recommended"
        else:
            return "PASSED: All rooms within expected bounds"


def validate_room_sizes(rooms: List[Any]) -> tuple[bool, List[ValidationIssue]]:
    """
    Convenience function to validate room sizes
    
    Args:
        rooms: List of Room objects
        
    Returns:
        Tuple of (should_continue, issues)
    """
    validator = RoomValidator()
    issues = validator.validate_rooms(rooms)
    should_continue = not validator.should_stop_pipeline()
    
    if not should_continue:
        logger.error(f"Room validation failed: {validator.get_summary()}")
        for issue in validator.critical_issues:
            logger.error(f"  {issue.room_name}: {issue.message}")
    
    return should_continue, issues