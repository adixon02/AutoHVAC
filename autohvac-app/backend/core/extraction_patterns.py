#!/usr/bin/env python3
"""
Configurable Extraction Patterns for AutoHVAC Blueprint Processing
Centralized pattern library with pre-compiled regex patterns for maximum performance
"""

import re
from typing import Dict, List, Pattern, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Types of extraction patterns"""
    ADDRESS = "address"
    AREA = "area"
    ROOM = "room"
    R_VALUE = "r_value"
    DIMENSION = "dimension"
    PROJECT_INFO = "project_info"
    WINDOW = "window"
    DOOR = "door"

@dataclass
class PatternDefinition:
    """Definition of an extraction pattern with metadata"""
    name: str
    pattern: str
    type: PatternType
    confidence_weight: float = 1.0
    priority: int = 1  # Lower number = higher priority
    description: str = ""
    compiled_pattern: Optional[Pattern] = field(default=None, init=False)
    
    def __post_init__(self):
        """Compile pattern after initialization"""
        try:
            flags = re.IGNORECASE | re.MULTILINE
            self.compiled_pattern = re.compile(self.pattern, flags)
        except re.error as e:
            logger.error(f"Failed to compile pattern '{self.name}': {e}")
            self.compiled_pattern = None

class ExtractionPatterns:
    """High-performance pattern library with pre-compiled regex patterns"""
    
    def __init__(self):
        self._patterns: Dict[PatternType, List[PatternDefinition]] = {}
        self._compiled_cache: Dict[str, Pattern] = {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize all extraction patterns"""
        self._load_address_patterns()
        self._load_area_patterns()
        self._load_room_patterns()
        self._load_r_value_patterns()
        self._load_dimension_patterns()
        self._load_project_info_patterns()
        self._load_window_door_patterns()
    
    def _add_pattern(self, pattern_def: PatternDefinition):
        """Add a pattern definition to the registry"""
        if pattern_def.type not in self._patterns:
            self._patterns[pattern_def.type] = []
        
        if pattern_def.compiled_pattern:
            self._patterns[pattern_def.type].append(pattern_def)
            # Sort by priority (lower number = higher priority)
            self._patterns[pattern_def.type].sort(key=lambda p: p.priority)
    
    def _load_address_patterns(self):
        """Load address extraction patterns"""
        patterns = [
            PatternDefinition(
                "specific_address",
                r'(\d+\s+[A-Z\s]+(?:STREET|ST|AVENUE|AVE|LANE|LN|DRIVE|DR|ROAD|RD|WAY|COURT|CT|CIRCLE|CIR|PLACE|PL|BOULEVARD|BLVD))',
                PatternType.ADDRESS,
                confidence_weight=0.95,
                priority=1,
                description="Complete street address with number and street type"
            ),
            PatternDefinition(
                "address_field",
                r'(?:ADDRESS|LOCATION|SITE)[:\s]*(.+?)(?:\n|$)',
                PatternType.ADDRESS,
                confidence_weight=0.85,
                priority=2,
                description="Address from labeled field"
            ),
            PatternDefinition(
                "project_location",
                r'(?:PROJECT\s+LOCATION|PROPERTY\s+ADDRESS)[:\s]*(.+?)(?:\n|$)',
                PatternType.ADDRESS,
                confidence_weight=0.90,
                priority=1,
                description="Project location field"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_area_patterns(self):
        """Load area extraction patterns"""
        patterns = [
            PatternDefinition(
                "living_area",
                r'(?:LIVING\s+AREA|FLOOR\s+AREA|TOTAL\s+AREA)[:\s]*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?|SQUARE\s+FEET)',
                PatternType.AREA,
                confidence_weight=0.95,
                priority=1,
                description="Labeled living/floor area"
            ),
            PatternDefinition(
                "area_schedule",
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?)\s*(?:LIVING|TOTAL|FLOOR)',
                PatternType.AREA,
                confidence_weight=0.85,
                priority=2,
                description="Area from schedule or table"
            ),
            PatternDefinition(
                "calculated_area",
                r'AREA\s*=\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?)',
                PatternType.AREA,
                confidence_weight=0.90,
                priority=1,
                description="Calculated area notation"
            ),
            PatternDefinition(
                "garage_area",
                r'(?:GARAGE|GAR\.?)[:\s]*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?)',
                PatternType.AREA,
                confidence_weight=0.85,
                priority=2,
                description="Garage area"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_room_patterns(self):
        """Load room extraction patterns"""
        patterns = [
            PatternDefinition(
                "room_with_area",
                r'([A-Z][A-Z\s\d]*(?:ROOM|BEDROOM|BR|BATHROOM|BA|KITCHEN|LIVING|DINING|FAMILY|OFFICE|DEN))\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?)',
                PatternType.ROOM,
                confidence_weight=0.90,
                priority=1,
                description="Room name with area"
            ),
            PatternDefinition(
                "room_dimensions",
                r'([A-Z][A-Z\s\d]*(?:ROOM|BEDROOM|BR|BATHROOM|BA|KITCHEN|LIVING|DINING|FAMILY|OFFICE|DEN))\s*[:\-]?\s*(\d+(?:\'\d+\"?)?)\s*[xX×]\s*(\d+(?:\'\d+\"?)?)',
                PatternType.ROOM,
                confidence_weight=0.85,
                priority=2,
                description="Room name with dimensions"
            ),
            PatternDefinition(
                "room_schedule",
                r'(\d+(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?)\s*([A-Z][A-Z\s\d]*(?:ROOM|BEDROOM|BR|BATHROOM|BA|KITCHEN|LIVING|DINING|FAMILY|OFFICE|DEN))',
                PatternType.ROOM,
                confidence_weight=0.80,
                priority=3,
                description="Area followed by room name"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_r_value_patterns(self):
        """Load R-value extraction patterns"""
        patterns = [
            PatternDefinition(
                "wall_r_value",
                r'(?:WALL|EXTERIOR\s+WALL)[:\s]*R[\-\s]*(\d+(?:\.\d+)?)',
                PatternType.R_VALUE,
                confidence_weight=0.95,
                priority=1,
                description="Wall R-value specification"
            ),
            PatternDefinition(
                "ceiling_r_value",
                r'(?:CEILING|ROOF|ATTIC)[:\s]*R[\-\s]*(\d+(?:\.\d+)?)',
                PatternType.R_VALUE,
                confidence_weight=0.95,
                priority=1,
                description="Ceiling/roof R-value specification"
            ),
            PatternDefinition(
                "insulation_schedule",
                r'R[\-\s]*(\d+(?:\.\d+)?)\s*(?:WALL|CEILING|FLOOR|FOUNDATION)',
                PatternType.R_VALUE,
                confidence_weight=0.90,
                priority=2,
                description="R-value from insulation schedule"
            ),
            PatternDefinition(
                "generic_r_value",
                r'R[\-\s]*(\d+(?:\.\d+)?)',
                PatternType.R_VALUE,
                confidence_weight=0.60,
                priority=5,
                description="Generic R-value mention"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_dimension_patterns(self):
        """Load dimension extraction patterns"""
        patterns = [
            PatternDefinition(
                "feet_inches",
                r'(\d+)[\'\-\s]*(\d+)[\"\s]*[xX×]\s*(\d+)[\'\-\s]*(\d+)[\"\s]*',
                PatternType.DIMENSION,
                confidence_weight=0.95,
                priority=1,
                description="Feet-inches dimensions (e.g., 12'6\" x 14'0\")"
            ),
            PatternDefinition(
                "feet_only",
                r'(\d+(?:\.\d+)?)\s*[\'\s]*[xX×]\s*(\d+(?:\.\d+)?)\s*[\'\s]*',
                PatternType.DIMENSION,
                confidence_weight=0.90,
                priority=2,
                description="Feet-only dimensions (e.g., 12.5' x 14')"
            ),
            PatternDefinition(
                "decimal_feet",
                r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',
                PatternType.DIMENSION,
                confidence_weight=0.80,
                priority=3,
                description="Decimal dimensions (assumed feet)"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_project_info_patterns(self):
        """Load project information patterns"""
        patterns = [
            PatternDefinition(
                "project_name",
                r'(?:PROJECT|JOB)\s*(?:NAME|TITLE)[:\s]*(.+?)(?:\n|$)',
                PatternType.PROJECT_INFO,
                confidence_weight=0.90,
                priority=1,
                description="Project name from title field"
            ),
            PatternDefinition(
                "owner_name",
                r'(?:OWNER|CLIENT)[:\s]*(.+?)(?:\n|$)',
                PatternType.PROJECT_INFO,
                confidence_weight=0.85,
                priority=2,
                description="Owner/client name"
            ),
            PatternDefinition(
                "architect",
                r'(?:ARCHITECT|ARCH\.?|DESIGNED\s+BY)[:\s]*(.+?)(?:\n|$)',
                PatternType.PROJECT_INFO,
                confidence_weight=0.85,
                priority=2,
                description="Architect name"
            ),
            PatternDefinition(
                "contractor",
                r'(?:CONTRACTOR|BUILDER|BUILT\s+BY)[:\s]*(.+?)(?:\n|$)',
                PatternType.PROJECT_INFO,
                confidence_weight=0.85,
                priority=2,
                description="Contractor name"
            ),
            PatternDefinition(
                "permit_number",
                r'(?:PERMIT|PERMIT\s+NO\.?|PERMIT\s+NUMBER)[:\s]*([A-Z0-9\-]+)',
                PatternType.PROJECT_INFO,
                confidence_weight=0.95,
                priority=1,
                description="Building permit number"
            ),
            PatternDefinition(
                "drawing_date",
                r'(?:DATE|DRAWN|REVISED)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                PatternType.PROJECT_INFO,
                confidence_weight=0.90,
                priority=1,
                description="Drawing or revision date"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def _load_window_door_patterns(self):
        """Load window and door patterns"""
        patterns = [
            PatternDefinition(
                "window_schedule",
                r'(?:WINDOW|WIN\.?)\s*([A-Z0-9]+)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',
                PatternType.WINDOW,
                confidence_weight=0.90,
                priority=1,
                description="Window schedule with dimensions"
            ),
            PatternDefinition(
                "door_schedule",
                r'(?:DOOR|DR\.?)\s*([A-Z0-9]+)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',
                PatternType.DOOR,
                confidence_weight=0.90,
                priority=1,
                description="Door schedule with dimensions"
            )
        ]
        
        for pattern in patterns:
            self._add_pattern(pattern)
    
    def get_patterns(self, pattern_type: PatternType) -> List[PatternDefinition]:
        """Get all patterns for a specific type"""
        return self._patterns.get(pattern_type, [])
    
    def get_compiled_pattern(self, pattern_name: str) -> Optional[Pattern]:
        """Get a compiled pattern by name"""
        for patterns in self._patterns.values():
            for pattern in patterns:
                if pattern.name == pattern_name:
                    return pattern.compiled_pattern
        return None
    
    def search_patterns(self, text: str, pattern_type: PatternType, max_results: int = 10) -> List[Tuple[PatternDefinition, re.Match]]:
        """Search text with all patterns of a given type"""
        results = []
        patterns = self.get_patterns(pattern_type)
        
        for pattern_def in patterns:
            if not pattern_def.compiled_pattern:
                continue
                
            matches = pattern_def.compiled_pattern.finditer(text)
            for match in matches:
                results.append((pattern_def, match))
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        return results
    
    def find_best_match(self, text: str, pattern_type: PatternType) -> Optional[Tuple[PatternDefinition, re.Match]]:
        """Find the best (highest priority/confidence) match for a pattern type"""
        results = self.search_patterns(text, pattern_type, max_results=1)
        return results[0] if results else None
    
    def extract_all_matches(self, text: str) -> Dict[PatternType, List[Tuple[PatternDefinition, re.Match]]]:
        """Extract all matches for all pattern types"""
        all_matches = {}
        
        for pattern_type in PatternType:
            matches = self.search_patterns(text, pattern_type)
            if matches:
                all_matches[pattern_type] = matches
        
        return all_matches
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded patterns"""
        stats = {
            'total_patterns': sum(len(patterns) for patterns in self._patterns.values()),
            'pattern_types': len(self._patterns),
            'patterns_by_type': {
                pattern_type.value: len(patterns) 
                for pattern_type, patterns in self._patterns.items()
            },
            'compilation_errors': sum(
                1 for patterns in self._patterns.values() 
                for pattern in patterns 
                if pattern.compiled_pattern is None
            )
        }
        return stats

# Global pattern instance for reuse
_global_patterns: Optional[ExtractionPatterns] = None

def get_patterns() -> ExtractionPatterns:
    """Get global pattern instance (singleton)"""
    global _global_patterns
    if _global_patterns is None:
        _global_patterns = ExtractionPatterns()
    return _global_patterns

# Utility functions for common extractions
def extract_area_from_text(text: str) -> List[Tuple[float, float]]:
    """Extract areas with confidence scores"""
    patterns = get_patterns()
    results = []
    
    matches = patterns.search_patterns(text, PatternType.AREA)
    for pattern_def, match in matches:
        try:
            area_str = match.group(1).replace(',', '')
            area = float(area_str)
            confidence = pattern_def.confidence_weight
            results.append((area, confidence))
        except (ValueError, IndexError):
            continue
    
    return results

def extract_rooms_from_text(text: str) -> List[Tuple[str, float, float]]:
    """Extract rooms with areas and confidence scores"""
    patterns = get_patterns()
    results = []
    
    matches = patterns.search_patterns(text, PatternType.ROOM)
    for pattern_def, match in matches:
        try:
            room_name = match.group(1).strip()
            if len(match.groups()) >= 2:
                area = float(match.group(2).replace(',', ''))
            else:
                area = 0.0
            confidence = pattern_def.confidence_weight
            results.append((room_name, area, confidence))
        except (ValueError, IndexError):
            continue
    
    return results

def extract_r_values_from_text(text: str) -> List[Tuple[str, float, float]]:
    """Extract R-values with context and confidence scores"""
    patterns = get_patterns()
    results = []
    
    matches = patterns.search_patterns(text, PatternType.R_VALUE)
    for pattern_def, match in matches:
        try:
            context = pattern_def.description
            r_value = float(match.group(1))
            confidence = pattern_def.confidence_weight
            results.append((context, r_value, confidence))
        except (ValueError, IndexError):
            continue
    
    return results