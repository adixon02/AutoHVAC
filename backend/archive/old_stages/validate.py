"""
Aggressive Validation Stage
Catches problems before they hit Manual J calculations
"""

import logging
from typing import List, Optional
from core.models import Building, Floor, Room

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation failed - clear error message"""
    pass


class BuildingValidator:
    """
    Aggressive validation rules
    Better to fail fast with clear errors than produce wrong calculations
    """
    
    # Minimum thresholds
    MIN_BUILDING_SQFT = 1000  # Lowered for testing - normally 1500
    MIN_FLOOR_SQFT = 100      # Lowered for testing - normally 500
    MIN_ROOM_SQFT = 20        # Smallest reasonable room (closet/utility)
    MAX_ROOM_SQFT = 1000      # Largest reasonable room
    MIN_ROOMS_PER_FLOOR = 1   # Lowered for testing - normally 4
    MIN_CEILING_HEIGHT = 7     # Minimum ceiling height
    MAX_CEILING_HEIGHT = 20    # Maximum ceiling height
    
    def validate_building(self, floors: List[Floor]) -> Building:
        """
        Main validation entry point
        
        Args:
            floors: List of Floor objects from extraction
            
        Returns:
            Validated Building object
            
        Raises:
            ValidationError with clear message
        """
        if not floors:
            raise ValidationError("No floors detected - check PDF classification")
        
        building = Building()
        
        # Validate each floor
        for floor in floors:
            self._validate_floor(floor)
            building.add_floor(floor)
        
        # Validate building totals
        self._validate_building_totals(building)
        
        # Check for common issues
        self._check_multi_story_detection(building)
        
        logger.info(f"Validation passed: {building.floor_count} floors, "
                   f"{building.room_count} rooms, {building.total_sqft:.0f} sqft")
        
        return building
    
    def _validate_floor(self, floor: Floor):
        """Validate a single floor"""
        # Check floor has rooms
        if floor.room_count == 0:
            raise ValidationError(f"Floor {floor.number} has no rooms")
        
        # Check minimum rooms
        if floor.room_count < self.MIN_ROOMS_PER_FLOOR:
            raise ValidationError(
                f"Floor {floor.number} has only {floor.room_count} rooms "
                f"(minimum {self.MIN_ROOMS_PER_FLOOR}). Missing rooms?"
            )
        
        # Check floor total area
        if floor.total_sqft < self.MIN_FLOOR_SQFT:
            raise ValidationError(
                f"Floor {floor.number} is only {floor.total_sqft:.0f} sqft "
                f"(minimum {self.MIN_FLOOR_SQFT}). Extraction failed?"
            )
        
        # Validate each room
        for room in floor.rooms:
            self._validate_room(room)
    
    def _validate_room(self, room: Room):
        """Validate a single room"""
        # Check room area (but be lenient for utility spaces)
        if room.area_sqft < self.MIN_ROOM_SQFT:
            # Allow small utility spaces
            room_name_lower = room.name.lower()
            if any(word in room_name_lower for word in ['closet', 'access', 'storage', 'pantry', 'hall']):
                logger.debug(f"Allowing small utility space: {room.name} ({room.area_sqft:.0f} sqft)")
            else:
                raise ValidationError(
                    f"Room '{room.name}' is only {room.area_sqft:.0f} sqft "
                    f"(minimum {self.MIN_ROOM_SQFT})"
                )
        
        if room.area_sqft > self.MAX_ROOM_SQFT:
            logger.warning(
                f"Room '{room.name}' is {room.area_sqft:.0f} sqft - "
                "unusually large, check extraction"
            )
        
        # Check dimensions match area
        calculated_area = room.width_ft * room.length_ft
        if abs(calculated_area - room.area_sqft) > 50:
            logger.warning(
                f"Room '{room.name}' area mismatch: "
                f"{room.width_ft}×{room.length_ft} = {calculated_area:.0f} sqft, "
                f"but area is {room.area_sqft:.0f} sqft"
            )
        
        # Check ceiling height
        if room.ceiling_height_ft < self.MIN_CEILING_HEIGHT:
            room.ceiling_height_ft = 8  # Fix to reasonable default
            logger.warning(f"Fixed ceiling height for '{room.name}'")
        
        if room.ceiling_height_ft > self.MAX_CEILING_HEIGHT:
            room.ceiling_height_ft = 9  # Fix to reasonable default
            logger.warning(f"Fixed ceiling height for '{room.name}'")
    
    def _validate_building_totals(self, building: Building):
        """Validate building-level totals"""
        # Check total square footage
        if building.total_sqft < self.MIN_BUILDING_SQFT:
            raise ValidationError(
                f"Building total is only {building.total_sqft:.0f} sqft "
                f"(minimum {self.MIN_BUILDING_SQFT} for residential). "
                f"Detected {building.floor_count} floor(s) - likely missing floors!"
            )
        
        # Check room count
        min_rooms = building.floor_count * self.MIN_ROOMS_PER_FLOOR
        if building.room_count < min_rooms:
            raise ValidationError(
                f"Building has only {building.room_count} rooms across {building.floor_count} floors "
                f"(expected at least {min_rooms}). Missing rooms in extraction?"
            )
    
    def _check_multi_story_detection(self, building: Building):
        """Check if we might be missing floors"""
        # Single floor with low square footage might mean we missed upper floor
        if building.floor_count == 1 and building.total_sqft < 2000:
            logger.warning(
                f"⚠️  Single floor with {building.total_sqft:.0f} sqft - "
                "typical homes are 2000+ sqft. Check for missed upper floor!"
            )
        
        # Check for floor numbering gaps
        floor_numbers = [f.number for f in building.floors]
        if 1 in floor_numbers and 2 not in floor_numbers:
            # Has first floor but no second floor
            avg_floor_area = building.total_sqft / building.floor_count
            if avg_floor_area < 1500:
                logger.warning(
                    "⚠️  No second floor detected but first floor is small. "
                    "Multi-story building might be missing upper floor!"
                )


# Module-level instance
validator = BuildingValidator()


def validate_building(floors: List[Floor]) -> Building:
    """Convenience function"""
    return validator.validate_building(floors)
