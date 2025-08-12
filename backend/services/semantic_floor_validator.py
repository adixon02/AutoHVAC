"""
Semantic Floor Validation System

This module validates floor assignments based on room patterns and relationships,
preventing mislabeled pages from causing incorrect floor assignments.

NO BAND-AID FIXES: This addresses the ROOT CAUSE of floor mislabeling
by understanding room relationships, not trusting page labels blindly.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass

from app.parser.schema import Room, PageAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class FloorValidation:
    """Floor validation results"""
    floor_number: int
    original_label: Optional[str]
    detected_type: str  # "main", "upper", "basement", "bonus"
    confidence: float
    issues: List[str]
    suggested_floor: Optional[int]
    rooms: List[Room]


class SemanticFloorValidator:
    """
    Validates floor assignments using semantic understanding of room patterns
    
    ROOT CAUSE FIX: Pages labeled "SECOND FLOOR" showing main floor rooms
    are detected and corrected by analyzing room patterns, not trusting labels.
    """
    
    def __init__(self):
        # Room patterns that indicate main/first floor
        self.main_floor_indicators = {
            'kitchen', 'kit', 'living', 'dining', 'great room', 
            'family', 'entry', 'foyer', 'mud', 'pantry'
        }
        
        # Room patterns that indicate upper floors
        self.upper_floor_indicators = {
            'master', 'mbr', 'bonus', 'loft', 'attic'
        }
        
        # Room patterns that indicate basement
        self.basement_indicators = {
            'basement', 'rec', 'recreation', 'game', 'lower level',
            'workshop', 'wine', 'theater', 'furnace', 'utility'
        }
    
    def validate_floor_assignments(
        self, 
        rooms_by_page: Dict[int, List[Room]], 
        page_analyses: List[PageAnalysisResult]
    ) -> Dict[int, FloorValidation]:
        """
        Validate and correct floor assignments based on semantic analysis
        
        Args:
            rooms_by_page: Rooms grouped by page number (0-indexed)
            page_analyses: Page analysis results with floor labels
            
        Returns:
            Dictionary of page number to validation results
        """
        validations = {}
        
        # First pass: Analyze each page's room patterns
        page_patterns = {}
        for page_num, rooms in rooms_by_page.items():
            pattern = self._analyze_room_pattern(rooms)
            page_patterns[page_num] = pattern
            
            logger.info(f"Page {page_num + 1} pattern: {pattern['type']}, "
                       f"confidence: {pattern['confidence']:.2f}")
        
        # Second pass: Validate against labeled floor numbers
        for page_num, rooms in rooms_by_page.items():
            page_analysis = page_analyses[page_num] if page_num < len(page_analyses) else None
            original_label = page_analysis.floor_name if page_analysis else None
            original_floor_num = page_analysis.floor_number if page_analysis else None
            
            pattern = page_patterns[page_num]
            validation = self._validate_single_floor(
                page_num, rooms, pattern, original_label, original_floor_num
            )
            
            validations[page_num] = validation
            
            if validation.issues:
                logger.warning(f"Page {page_num + 1} validation issues: {validation.issues}")
            
            if validation.suggested_floor != original_floor_num:
                logger.info(f"Page {page_num + 1}: Suggesting floor {validation.suggested_floor} "
                           f"instead of {original_floor_num} (label: {original_label})")
        
        # Third pass: Resolve conflicts between pages
        validations = self._resolve_floor_conflicts(validations, page_patterns)
        
        return validations
    
    def _analyze_room_pattern(self, rooms: List[Room]) -> Dict:
        """Analyze room pattern to determine likely floor type"""
        room_names_lower = [r.name.lower() for r in rooms]
        all_text = ' '.join(room_names_lower)
        
        # Count indicators
        main_floor_score = sum(
            1 for indicator in self.main_floor_indicators 
            if indicator in all_text
        )
        
        upper_floor_score = sum(
            1 for indicator in self.upper_floor_indicators 
            if indicator in all_text
        )
        
        basement_score = sum(
            1 for indicator in self.basement_indicators 
            if indicator in all_text
        )
        
        # Check for specific room types
        has_kitchen = any('kitchen' in name or 'kit' in name for name in room_names_lower)
        has_living = any('living' in name or 'great' in name for name in room_names_lower)
        has_dining = any('dining' in name for name in room_names_lower)
        has_master = any('master' in name or 'mbr' in name for name in room_names_lower)
        has_bonus = any('bonus' in name for name in room_names_lower)
        
        bedroom_count = sum(1 for name in room_names_lower if 'bed' in name or 'br' in name)
        bathroom_count = sum(1 for name in room_names_lower if 'bath' in name or 'ba' in name)
        
        # Determine floor type
        floor_type = "unknown"
        confidence = 0.5
        
        if basement_score > main_floor_score and basement_score > upper_floor_score:
            floor_type = "basement"
            confidence = min(1.0, 0.7 + basement_score * 0.1)
        elif has_kitchen and (has_living or has_dining):
            floor_type = "main"
            confidence = 0.9
        elif has_bonus or (len(rooms) <= 3 and bedroom_count <= 1 and not basement_score):
            floor_type = "bonus"
            confidence = 0.85
        elif len(rooms) <= 3 and any('storage' in r.name.lower() for r in rooms):
            # Small floor with storage room - likely bonus/attic space
            floor_type = "bonus"
            confidence = 0.8
        elif bedroom_count >= 2 and bathroom_count >= 1:
            floor_type = "upper"
            confidence = 0.8
        elif has_master and bedroom_count >= 1:
            floor_type = "upper"
            confidence = 0.85
        elif main_floor_score > upper_floor_score:
            floor_type = "main"
            confidence = min(1.0, 0.6 + main_floor_score * 0.1)
        elif upper_floor_score > 0:
            floor_type = "upper"
            confidence = min(1.0, 0.6 + upper_floor_score * 0.1)
        
        return {
            'type': floor_type,
            'confidence': confidence,
            'has_kitchen': has_kitchen,
            'has_living': has_living,
            'has_dining': has_dining,
            'has_master': has_master,
            'has_bonus': has_bonus,
            'bedroom_count': bedroom_count,
            'bathroom_count': bathroom_count,
            'room_count': len(rooms),
            'total_area': sum(r.area for r in rooms)
        }
    
    def _validate_single_floor(
        self, 
        page_num: int,
        rooms: List[Room], 
        pattern: Dict,
        original_label: Optional[str],
        original_floor_num: Optional[int]
    ) -> FloorValidation:
        """Validate a single floor assignment"""
        issues = []
        suggested_floor = original_floor_num
        
        # Map pattern type to expected floor number
        if pattern['type'] == 'basement':
            expected_floor = 0
        elif pattern['type'] == 'main':
            expected_floor = 1
        elif pattern['type'] in ['upper', 'bonus']:
            expected_floor = 2
        else:
            expected_floor = original_floor_num or 1
        
        # Check for mismatches
        if original_label and original_floor_num is not None:
            label_lower = original_label.lower()
            
            # Detect mislabeled pages
            if 'second' in label_lower or 'upper' in label_lower or '2nd' in label_lower:
                if pattern['has_kitchen'] and pattern['has_living']:
                    issues.append(f"Page labeled '{original_label}' but contains main floor rooms (kitchen, living)")
                    suggested_floor = 1
                elif pattern['type'] == 'main':
                    issues.append(f"Page labeled '{original_label}' but room pattern suggests main floor")
                    suggested_floor = 1
            
            elif 'first' in label_lower or 'main' in label_lower or '1st' in label_lower:
                if pattern['has_bonus']:
                    issues.append(f"Page labeled '{original_label}' but contains bonus room")
                    suggested_floor = 2
                elif pattern['bedroom_count'] >= 3 and not pattern['has_kitchen']:
                    issues.append(f"Page labeled '{original_label}' but appears to be bedroom floor")
                    suggested_floor = 2
            
            elif 'basement' in label_lower or 'lower' in label_lower:
                if pattern['has_kitchen'] and pattern['has_living']:
                    issues.append(f"Page labeled '{original_label}' but contains main living areas")
                    suggested_floor = 1
        
        # Additional validation based on room patterns
        if pattern['type'] == 'main' and original_floor_num == 2:
            issues.append("Main floor pattern (kitchen, living) assigned to floor 2")
            suggested_floor = 1
        
        if pattern['type'] == 'upper' and original_floor_num == 1 and pattern['confidence'] > 0.8:
            issues.append("Upper floor pattern (bedrooms, no kitchen) assigned to floor 1")
            suggested_floor = 2
        
        # Special case: bonus room should always be floor 2
        if pattern['has_bonus'] and original_floor_num != 2:
            issues.append(f"Bonus room on floor {original_floor_num}, should be floor 2")
            suggested_floor = 2
        
        return FloorValidation(
            floor_number=original_floor_num or suggested_floor,
            original_label=original_label,
            detected_type=pattern['type'],
            confidence=pattern['confidence'],
            issues=issues,
            suggested_floor=suggested_floor if suggested_floor != original_floor_num else None,
            rooms=rooms
        )
    
    def _resolve_floor_conflicts(
        self, 
        validations: Dict[int, FloorValidation],
        patterns: Dict[int, Dict]
    ) -> Dict[int, FloorValidation]:
        """Resolve conflicts between floor assignments"""
        
        # Check for duplicate floor numbers
        floor_assignments = {}
        for page_num, validation in validations.items():
            floor_num = validation.suggested_floor or validation.floor_number
            if floor_num not in floor_assignments:
                floor_assignments[floor_num] = []
            floor_assignments[floor_num].append(page_num)
        
        # Resolve duplicates
        for floor_num, page_nums in floor_assignments.items():
            if len(page_nums) > 1:
                logger.warning(f"Multiple pages assigned to floor {floor_num}: {page_nums}")
                
                # Use pattern confidence to resolve
                best_page = max(
                    page_nums, 
                    key=lambda p: patterns[p]['confidence']
                )
                
                # Reassign others
                for page_num in page_nums:
                    if page_num != best_page:
                        validation = validations[page_num]
                        pattern = patterns[page_num]
                        
                        # Find appropriate floor
                        if pattern['type'] == 'bonus':
                            new_floor = 2
                        elif pattern['type'] == 'upper':
                            new_floor = 2 if floor_num != 2 else 3
                        elif pattern['type'] == 'main':
                            new_floor = 1
                        else:
                            # Find next available floor
                            new_floor = 1
                            while new_floor in floor_assignments:
                                new_floor += 1
                        
                        validation.suggested_floor = new_floor
                        validation.issues.append(f"Reassigned from floor {floor_num} to {new_floor} to resolve conflict")
        
        return validations


def validate_floor_assignments(
    rooms_by_page: Dict[int, List[Room]], 
    page_analyses: List[PageAnalysisResult]
) -> Dict[int, FloorValidation]:
    """
    Convenience function to validate floor assignments
    
    Args:
        rooms_by_page: Rooms grouped by page number
        page_analyses: Page analysis results
        
    Returns:
        Validation results for each page
    """
    validator = SemanticFloorValidator()
    return validator.validate_floor_assignments(rooms_by_page, page_analyses)