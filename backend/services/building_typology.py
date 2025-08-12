"""
Building Typology Detection and Classification System

This module provides intelligent detection of building types (1-story, 1.5-story, 2-story, etc.)
and handles special cases like bonus rooms over garages, lofts, and partial upper floors.

NO BAND-AID FIXES: This module addresses the ROOT CAUSE of misclassification
by understanding building semantics, not just counting floors.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from app.parser.schema import Room, PageAnalysisResult

logger = logging.getLogger(__name__)


class BuildingType(Enum):
    """Building typology classifications"""
    SINGLE_STORY = "1-story"
    ONE_AND_HALF_STORY = "1.5-story"  # Main floor + bonus/partial upper
    TWO_STORY = "2-story"  # Full two floors
    TWO_AND_HALF_STORY = "2.5-story"  # Two floors + finished attic/loft
    THREE_STORY = "3-story"
    SPLIT_LEVEL = "split-level"
    RAISED_RANCH = "raised-ranch"
    

class RoomType(Enum):
    """Room type classifications for floor assignment"""
    # Main living areas (typically first floor)
    LIVING = "living"
    DINING = "dining"
    KITCHEN = "kitchen"
    FAMILY = "family"
    GREAT = "great"
    DEN = "den"
    OFFICE = "office"
    
    # Bedrooms (can be any floor)
    BEDROOM = "bedroom"
    MASTER = "master"
    
    # Service areas
    BATHROOM = "bathroom"
    LAUNDRY = "laundry"
    UTILITY = "utility"
    MECHANICAL = "mechanical"
    
    # Storage/circulation
    CLOSET = "closet"
    STORAGE = "storage"
    HALLWAY = "hallway"
    ENTRY = "entry"
    FOYER = "foyer"
    STAIRWAY = "stairway"
    
    # Garage areas
    GARAGE = "garage"
    
    # Special upper floor rooms
    BONUS = "bonus"
    LOFT = "loft"
    ATTIC = "attic"
    
    # Basement rooms
    BASEMENT = "basement"
    REC = "recreation"
    
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class FloorCharacteristics:
    """Characteristics of a floor for typology detection"""
    floor_number: int
    floor_name: str
    room_count: int
    total_area: float
    room_types: Set[RoomType]
    has_kitchen: bool
    has_living_areas: bool
    bedroom_count: int
    bathroom_count: int
    is_bonus_room: bool
    is_partial_floor: bool
    confidence: float


@dataclass
class BuildingTypology:
    """Complete building typology analysis"""
    building_type: BuildingType
    actual_stories: float  # 1.0, 1.5, 2.0, 2.5, etc.
    floor_characteristics: List[FloorCharacteristics]
    has_bonus_room: bool
    bonus_room_area: float
    has_basement: bool
    has_attic: bool
    total_conditioned_area: float
    main_floor_area: float
    upper_floor_area: float
    confidence: float
    notes: List[str]


class BuildingTypologyDetector:
    """
    Intelligent building typology detection that understands building semantics
    
    ROOT CAUSE FIX: Instead of blindly trusting page labels, this analyzes
    room patterns and relationships to determine actual building type.
    """
    
    def __init__(self):
        self.room_type_keywords = {
            RoomType.LIVING: ['living', 'liv', 'great room', 'family'],
            RoomType.DINING: ['dining', 'din'],
            RoomType.KITCHEN: ['kitchen', 'kit', 'ktch'],
            RoomType.BEDROOM: ['bedroom', 'bed', 'br', 'bdrm'],
            RoomType.MASTER: ['master', 'mbr', 'owner'],
            RoomType.BATHROOM: ['bathroom', 'bath', 'ba', 'powder', 'toilet', 'wc'],
            RoomType.BONUS: ['bonus', 'flex', 'multi-purpose'],
            RoomType.GARAGE: ['garage', 'gar'],
            RoomType.LOFT: ['loft'],
            RoomType.CLOSET: ['closet', 'clo', 'wic', 'walk-in'],
            RoomType.STORAGE: ['storage', 'stor'],
            RoomType.LAUNDRY: ['laundry', 'laun', 'mud'],
            RoomType.UTILITY: ['utility', 'util', 'mech', 'furnace'],
            RoomType.HALLWAY: ['hall', 'corridor'],
            RoomType.ENTRY: ['entry', 'foyer', 'vestibule'],
            RoomType.BASEMENT: ['basement', 'lower level'],
            RoomType.REC: ['rec', 'recreation', 'game', 'media'],
            RoomType.ATTIC: ['attic'],
            RoomType.OFFICE: ['office', 'study', 'library'],
            RoomType.DEN: ['den'],
            RoomType.STAIRWAY: ['stair', 'stairs']
        }
    
    def detect_building_typology(
        self, 
        rooms_by_floor: Dict[int, List[Room]], 
        page_analyses: Optional[List[PageAnalysisResult]] = None
    ) -> BuildingTypology:
        """
        Detect building typology from room data
        
        Args:
            rooms_by_floor: Dictionary mapping floor numbers to rooms
            page_analyses: Optional page analysis results for additional context
            
        Returns:
            BuildingTypology with classification and analysis
        """
        logger.info(f"Detecting building typology for {len(rooms_by_floor)} floors")
        
        # Analyze each floor
        floor_chars = []
        for floor_num in sorted(rooms_by_floor.keys()):
            floor_rooms = rooms_by_floor[floor_num]
            characteristics = self._analyze_floor(floor_num, floor_rooms)
            floor_chars.append(characteristics)
            
            logger.info(f"Floor {floor_num}: {characteristics.room_count} rooms, "
                       f"{characteristics.total_area:.0f} sqft, "
                       f"bonus={characteristics.is_bonus_room}, "
                       f"partial={characteristics.is_partial_floor}")
        
        # Determine building type
        building_type, actual_stories = self._classify_building_type(floor_chars)
        
        # Calculate areas
        main_floor_area = sum(fc.total_area for fc in floor_chars if fc.floor_number == 1)
        upper_floor_area = sum(fc.total_area for fc in floor_chars if fc.floor_number > 1)
        basement_area = sum(fc.total_area for fc in floor_chars if fc.floor_number == 0)
        bonus_area = sum(fc.total_area for fc in floor_chars if fc.is_bonus_room)
        
        total_conditioned = main_floor_area + upper_floor_area + basement_area
        
        # Build notes
        notes = []
        if bonus_area > 0:
            notes.append(f"Bonus room detected: {bonus_area:.0f} sqft")
        if any(fc.is_partial_floor for fc in floor_chars):
            notes.append("Partial upper floor detected")
        
        # Validate and adjust if needed
        validation_notes = self._validate_typology(floor_chars, building_type)
        notes.extend(validation_notes)
        
        return BuildingTypology(
            building_type=building_type,
            actual_stories=actual_stories,
            floor_characteristics=floor_chars,
            has_bonus_room=bonus_area > 0,
            bonus_room_area=bonus_area,
            has_basement=any(fc.floor_number == 0 for fc in floor_chars),
            has_attic=any(RoomType.ATTIC in fc.room_types for fc in floor_chars),
            total_conditioned_area=total_conditioned,
            main_floor_area=main_floor_area,
            upper_floor_area=upper_floor_area,
            confidence=self._calculate_confidence(floor_chars),
            notes=notes
        )
    
    def _analyze_floor(self, floor_number: int, rooms: List[Room]) -> FloorCharacteristics:
        """Analyze characteristics of a single floor"""
        room_types = set()
        bedroom_count = 0
        bathroom_count = 0
        total_area = 0
        
        for room in rooms:
            room_type = self._classify_room(room.name)
            room_types.add(room_type)
            
            if room_type in [RoomType.BEDROOM, RoomType.MASTER]:
                bedroom_count += 1
            elif room_type == RoomType.BATHROOM:
                bathroom_count += 1
            
            total_area += room.area
        
        # Detect special floor types
        is_bonus = RoomType.BONUS in room_types or (
            floor_number == 2 and 
            len(rooms) <= 3 and 
            bedroom_count <= 1
        )
        
        is_partial = (
            floor_number > 1 and 
            total_area < 500 and  # Less than 500 sqft is likely partial
            len(rooms) <= 4
        )
        
        has_kitchen = RoomType.KITCHEN in room_types
        has_living = any(rt in room_types for rt in [
            RoomType.LIVING, RoomType.FAMILY, RoomType.GREAT, RoomType.DEN
        ])
        
        # Calculate confidence based on room pattern consistency
        confidence = 1.0
        if floor_number == 1 and not has_kitchen:
            confidence *= 0.7  # Main floor usually has kitchen
        if floor_number == 2 and has_kitchen:
            confidence *= 0.8  # Upper floor rarely has kitchen
        
        return FloorCharacteristics(
            floor_number=floor_number,
            floor_name=self._get_floor_name(floor_number, is_bonus),
            room_count=len(rooms),
            total_area=total_area,
            room_types=room_types,
            has_kitchen=has_kitchen,
            has_living_areas=has_living,
            bedroom_count=bedroom_count,
            bathroom_count=bathroom_count,
            is_bonus_room=is_bonus,
            is_partial_floor=is_partial,
            confidence=confidence
        )
    
    def _classify_room(self, room_name: str) -> RoomType:
        """Classify a room based on its name"""
        room_name_lower = room_name.lower()
        
        for room_type, keywords in self.room_type_keywords.items():
            for keyword in keywords:
                if keyword in room_name_lower:
                    return room_type
        
        return RoomType.UNKNOWN
    
    def _classify_building_type(self, floor_chars: List[FloorCharacteristics]) -> Tuple[BuildingType, float]:
        """
        Classify building type based on floor characteristics
        
        Returns:
            Tuple of (BuildingType, actual_stories_count)
        """
        num_floors = len(floor_chars)
        has_basement = any(fc.floor_number == 0 for fc in floor_chars)
        main_floors = [fc for fc in floor_chars if fc.floor_number > 0]
        
        # Check for bonus room or partial upper floor
        has_bonus = any(fc.is_bonus_room for fc in floor_chars)
        has_partial_upper = any(fc.is_partial_floor and fc.floor_number > 1 for fc in floor_chars)
        
        # Single story
        if len(main_floors) == 1:
            return BuildingType.SINGLE_STORY, 1.0
        
        # 1.5 story (main + bonus/partial)
        if len(main_floors) == 2:
            upper_floor = main_floors[1]
            main_floor = main_floors[0]
            
            # Check if upper floor is bonus or partial
            if upper_floor.is_bonus_room or upper_floor.is_partial_floor:
                return BuildingType.ONE_AND_HALF_STORY, 1.5
            
            # Check area ratio - if upper is less than 60% of main, it's likely 1.5 story
            if upper_floor.total_area < main_floor.total_area * 0.6:
                return BuildingType.ONE_AND_HALF_STORY, 1.5
            
            # Full two story
            return BuildingType.TWO_STORY, 2.0
        
        # 2.5 story (two full floors + attic/loft)
        if len(main_floors) == 3:
            top_floor = main_floors[2]
            if RoomType.ATTIC in top_floor.room_types or RoomType.LOFT in top_floor.room_types:
                return BuildingType.TWO_AND_HALF_STORY, 2.5
            return BuildingType.THREE_STORY, 3.0
        
        # More than 3 floors
        return BuildingType.THREE_STORY, float(len(main_floors))
    
    def _get_floor_name(self, floor_number: int, is_bonus: bool) -> str:
        """Get appropriate floor name"""
        if floor_number == 0:
            return "Basement"
        elif floor_number == 1:
            return "Main Floor"
        elif floor_number == 2:
            return "Bonus Floor" if is_bonus else "Second Floor"
        elif floor_number == 3:
            return "Third Floor"
        else:
            return f"Floor {floor_number}"
    
    def _validate_typology(self, floor_chars: List[FloorCharacteristics], 
                          building_type: BuildingType) -> List[str]:
        """Validate and return any warnings about the typology detection"""
        notes = []
        
        # Check for inconsistencies
        main_floors = [fc for fc in floor_chars if fc.floor_number == 1]
        if main_floors and not main_floors[0].has_kitchen:
            notes.append("Warning: Main floor missing kitchen - verify floor assignment")
        
        upper_floors = [fc for fc in floor_chars if fc.floor_number > 1]
        if upper_floors and upper_floors[0].has_kitchen:
            notes.append("Warning: Upper floor has kitchen - may indicate apartment or duplex")
        
        # Validate area relationships
        if len(floor_chars) >= 2:
            floor1_area = floor_chars[0].total_area
            floor2_area = floor_chars[1].total_area if len(floor_chars) > 1 else 0
            
            if floor2_area > floor1_area * 1.2:
                notes.append("Warning: Upper floor larger than main floor - verify floor detection")
        
        return notes
    
    def _calculate_confidence(self, floor_chars: List[FloorCharacteristics]) -> float:
        """Calculate overall confidence in typology detection"""
        if not floor_chars:
            return 0.0
        
        # Average the individual floor confidences
        avg_confidence = sum(fc.confidence for fc in floor_chars) / len(floor_chars)
        
        # Adjust based on pattern consistency
        if all(fc.confidence > 0.8 for fc in floor_chars):
            return min(1.0, avg_confidence * 1.1)
        
        return avg_confidence


def detect_building_typology(rooms: List[Room], 
                            page_analyses: Optional[List[PageAnalysisResult]] = None) -> BuildingTypology:
    """
    Convenience function to detect building typology
    
    Args:
        rooms: List of all rooms in the building
        page_analyses: Optional page analysis results
        
    Returns:
        BuildingTypology analysis
    """
    # Group rooms by floor
    rooms_by_floor = {}
    for room in rooms:
        floor = room.floor
        if floor not in rooms_by_floor:
            rooms_by_floor[floor] = []
        rooms_by_floor[floor].append(room)
    
    detector = BuildingTypologyDetector()
    return detector.detect_building_typology(rooms_by_floor, page_analyses)