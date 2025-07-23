#!/usr/bin/env python3
"""
Unified High-Performance Blueprint Processor for AutoHVAC
Consolidates all blueprint processing functionality with optimized performance
"""

import PyPDF2
import re
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union, Set
from collections import defaultdict
import logging
from datetime import datetime
import time
import uuid

from .data_models import (
    ExtractionResult, ProjectInfo, BuildingCharacteristics, Room, 
    InsulationSpecs, ExtractionGaps, ExtractionMetrics, ProcessingStatus,
    BuildingType, validate_extraction_result
)
from .extraction_patterns import get_patterns, PatternType

# Set up logging
logger = logging.getLogger(__name__)

class BlueprintProcessor:
    """
    High-performance blueprint processor with caching, pre-compiled patterns,
    and intelligent extraction algorithms
    """
    
    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self._pattern_cache: Dict[str, Any] = {}
        self._text_cache: Dict[str, str] = {}
        self.patterns = get_patterns()
        
        # Performance optimization: pre-compile common patterns
        self._precompile_critical_patterns()
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0.0,
            'extraction_accuracy': 0.0
        }
        
        logger.info("BlueprintProcessor initialized with pattern caching")
    
    def _precompile_critical_patterns(self):
        """Pre-compile the most commonly used patterns for better performance"""
        critical_patterns = {
            'area_pattern': re.compile(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:SF|SQ\.?\s*FT\.?|SQUARE\s+FEET)', re.IGNORECASE),
            'dimension_pattern': re.compile(r'(\d+(?:\.\d+)?)\s*[\'x×]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            'room_pattern': re.compile(r'([A-Z][A-Z\s\d]*(?:ROOM|BEDROOM|BR|BATHROOM|BA|KITCHEN|LIVING|DINING|FAMILY))', re.IGNORECASE),
            'zip_pattern': re.compile(r'\b(\d{5})\b'),
            'r_value_pattern': re.compile(r'R[\-\s]*(\d+(?:\.\d+)?)', re.IGNORECASE)
        }
        
        self._pattern_cache.update(critical_patterns)
        logger.debug(f"Pre-compiled {len(critical_patterns)} critical patterns")
    
    async def process_blueprint_async(self, file_path: Union[str, Path], job_id: str = None, 
                                     project_info: Dict = None) -> ExtractionResult:
        """
        Asynchronously process a blueprint file
        """
        return await asyncio.to_thread(self.process_blueprint, file_path, job_id, project_info)
    
    def process_blueprint(self, file_path: Union[str, Path], job_id: str = None, 
                         project_info: Dict = None) -> ExtractionResult:
        """
        Main entry point for blueprint processing with comprehensive error handling
        """
        start_time = time.time()
        
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        # Initialize result object
        result = ExtractionResult(
            job_id=job_id,
            status=ProcessingStatus.PROCESSING,
            created_at=datetime.now()
        )
        
        try:
            logger.info(f"Processing blueprint: {file_path} (Job ID: {job_id})")
            
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(file_path)
            if not text_content:
                raise ValueError("No text content extracted from PDF")
            
            # Store raw text for debugging
            result.raw_data['extracted_text'] = text_content[:5000]  # First 5000 chars
            result.raw_data['file_size'] = Path(file_path).stat().st_size
            result.raw_data['file_name'] = Path(file_path).name
            
            # Perform comprehensive extraction
            result = self._perform_comprehensive_extraction(result, text_content, project_info)
            
            # Calculate overall confidence and validate
            result.calculate_overall_confidence()
            validation_issues = validate_extraction_result(result)
            
            if validation_issues:
                result.processing_notes.extend(validation_issues)
                logger.warning(f"Validation issues found: {validation_issues}")
            
            # Finalize result
            result.status = ProcessingStatus.COMPLETED
            result.completed_at = datetime.now()
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, result.overall_confidence)
            
            result.extraction_metrics.extraction_time_seconds = processing_time
            
            logger.info(f"Blueprint processing completed in {processing_time:.2f}s "
                       f"with {result.overall_confidence:.2f} confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"Blueprint processing failed: {str(e)}", exc_info=True)
            result.status = ProcessingStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result
    
    def _extract_text_from_pdf(self, file_path: Union[str, Path]) -> str:
        """
        Extract text from PDF with caching and error handling
        """
        file_path = Path(file_path)
        cache_key = f"{file_path.name}_{file_path.stat().st_mtime}"
        
        # Check cache first
        if self.enable_caching and cache_key in self._text_cache:
            self.stats['cache_hits'] += 1
            return self._text_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue
                
                full_text = '\n'.join(text_content)
                
                # Cache the result
                if self.enable_caching:
                    self._text_cache[cache_key] = full_text
                
                logger.debug(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")
                return full_text
                
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"PDF text extraction failed: {e}")
    
    def _perform_comprehensive_extraction(self, result: ExtractionResult, 
                                        text_content: str, project_info: Dict = None) -> ExtractionResult:
        """
        Perform comprehensive data extraction from text content
        """
        # Normalize text for better pattern matching
        normalized_text = self._normalize_text(text_content)
        
        # Extract project information
        result.project_info = self._extract_project_info(normalized_text, project_info)
        
        # Extract building characteristics
        result.building_chars = self._extract_building_characteristics(normalized_text)
        
        # Extract rooms
        result.rooms = self._extract_rooms(normalized_text)
        
        # Extract insulation specifications
        result.insulation = self._extract_insulation_specs(normalized_text)
        
        # Identify gaps and make recommendations
        result.gaps_identified = self._identify_extraction_gaps(result)
        
        # Store extraction metrics
        result.extraction_metrics = ExtractionMetrics(
            pages_processed=len(text_content.split('\n\n')),
            text_blocks_analyzed=len(normalized_text.split('\n')),
            patterns_matched=self._count_pattern_matches(normalized_text),
            processing_timestamp=datetime.now()
        )
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent pattern matching
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Standardize common abbreviations
        replacements = {
            r'\bSQ\.?\s*FT\.?\b': 'SF',
            r'\bSQUARE\s+FEET\b': 'SF',
            r'\bBEDROOM\b': 'BR',
            r'\bBATHROOM\b': 'BA',
            r'\bLIVING\s+ROOM\b': 'LIVING',
            r'\bDINING\s+ROOM\b': 'DINING',
            r'\bFAMILY\s+ROOM\b': 'FAMILY'
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _extract_project_info(self, text: str, provided_info: Dict = None) -> ProjectInfo:
        """
        Extract project information with intelligent fallbacks
        """
        project_info = ProjectInfo()
        
        # Use provided info if available
        if provided_info:
            for key, value in provided_info.items():
                if hasattr(project_info, key) and value:
                    setattr(project_info, key, value)
        
        # Extract from text using patterns
        matches = self.patterns.extract_all_matches(text)
        
        if PatternType.PROJECT_INFO in matches:
            for pattern_def, match in matches[PatternType.PROJECT_INFO]:
                value = match.group(1).strip()
                
                if 'project' in pattern_def.name.lower() and not project_info.project_name:
                    project_info.project_name = value
                elif 'owner' in pattern_def.name.lower() and not project_info.owner:
                    project_info.owner = value
                elif 'architect' in pattern_def.name.lower() and not project_info.architect:
                    project_info.architect = value
                elif 'contractor' in pattern_def.name.lower() and not project_info.contractor:
                    project_info.contractor = value
                elif 'permit' in pattern_def.name.lower() and not project_info.permit_number:
                    project_info.permit_number = value
                elif 'date' in pattern_def.name.lower() and not project_info.drawing_date:
                    project_info.drawing_date = value
        
        # Extract address
        if PatternType.ADDRESS in matches:
            best_address_match = matches[PatternType.ADDRESS][0]  # Highest priority
            project_info.address = best_address_match[1].group(1).strip()
        
        # Extract ZIP code
        zip_matches = self._pattern_cache['zip_pattern'].findall(text)
        if zip_matches and not project_info.zip_code:
            project_info.zip_code = zip_matches[0]
        
        # Calculate confidence
        filled_fields = sum(1 for field in ['project_name', 'address', 'zip_code', 'owner'] 
                           if getattr(project_info, field))
        project_info.confidence_score = min(filled_fields / 4.0, 1.0)
        
        return project_info
    
    def _extract_building_characteristics(self, text: str) -> BuildingCharacteristics:
        """
        Extract building characteristics with intelligent area calculation
        """
        building_chars = BuildingCharacteristics()
        
        # Extract areas using patterns
        matches = self.patterns.extract_all_matches(text)
        
        if PatternType.AREA in matches:
            areas = []
            for pattern_def, match in matches[PatternType.AREA]:
                try:
                    area_str = match.group(1).replace(',', '')
                    area = float(area_str)
                    confidence = pattern_def.confidence_weight
                    areas.append((area, confidence, pattern_def.description))
                except (ValueError, IndexError):
                    continue
            
            if areas:
                # Sort by confidence and take the best
                areas.sort(key=lambda x: x[1], reverse=True)
                best_area = areas[0]
                
                if 'garage' in best_area[2].lower():
                    building_chars.garage_area = best_area[0]
                else:
                    building_chars.total_area = best_area[0]
                    building_chars.main_residence_area = best_area[0]
        
        # Extract number of stories
        story_pattern = re.compile(r'(\d+)\s*STOR(?:Y|IES)', re.IGNORECASE)
        story_matches = story_pattern.findall(text)
        if story_matches:
            building_chars.stories = int(story_matches[0])
        
        # Determine construction type
        if re.search(r'\b(?:ADDITION|REMODEL|RENOVATION|RETROFIT)\b', text, re.IGNORECASE):
            building_chars.construction_type = "retrofit"
        elif re.search(r'\b(?:NEW|CONSTRUCTION)\b', text, re.IGNORECASE):
            building_chars.construction_type = "new_construction"
        
        # Calculate confidence
        confidence_factors = [
            building_chars.total_area > 0,
            building_chars.stories > 0,
            bool(building_chars.construction_type)
        ]
        building_chars.confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        return building_chars
    
    def _extract_rooms(self, text: str) -> List[Room]:
        """
        Extract room information with area calculation and validation
        """
        rooms = []
        room_counter = defaultdict(int)
        
        matches = self.patterns.extract_all_matches(text)
        
        if PatternType.ROOM in matches:
            for pattern_def, match in matches[PatternType.ROOM]:
                try:
                    room_name = match.group(1).strip().upper()
                    
                    # Extract area if available
                    area = 0.0
                    if len(match.groups()) >= 2:
                        area_str = match.group(2).replace(',', '')
                        area = float(area_str)
                    
                    # Generate unique room ID
                    room_counter[room_name] += 1
                    room_id = f"{room_name.lower().replace(' ', '_')}_{room_counter[room_name]}"
                    
                    # Determine room type and typical occupancy
                    occupancy = self._determine_room_occupancy(room_name)
                    
                    room = Room(
                        id=room_id,
                        name=room_name,
                        area=area,
                        occupancy=occupancy,
                        confidence_score=pattern_def.confidence_weight
                    )
                    
                    # Try to extract dimensions if area is missing
                    if area == 0.0:
                        room.area = self._estimate_room_area_from_dimensions(text, room_name)
                    
                    rooms.append(room)
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse room match: {e}")
                    continue
        
        return rooms
    
    def _extract_insulation_specs(self, text: str) -> InsulationSpecs:
        """
        Extract insulation specifications with intelligent defaults
        """
        insulation = InsulationSpecs()
        
        matches = self.patterns.extract_all_matches(text)
        
        if PatternType.R_VALUE in matches:
            r_values = {}
            for pattern_def, match in matches[PatternType.R_VALUE]:
                try:
                    r_value = float(match.group(1))
                    context = pattern_def.description.lower()
                    
                    if 'wall' in context:
                        r_values['wall'] = r_value
                    elif 'ceiling' in context or 'roof' in context:
                        r_values['ceiling'] = r_value
                    elif 'floor' in context:
                        r_values['floor'] = r_value
                    elif 'foundation' in context:
                        r_values['foundation'] = r_value
                        
                except (ValueError, IndexError):
                    continue
            
            # Apply extracted R-values
            if 'wall' in r_values:
                insulation.wall_r_value = r_values['wall']
            if 'ceiling' in r_values:
                insulation.ceiling_r_value = r_values['ceiling']
            if 'floor' in r_values:
                insulation.floor_r_value = r_values['floor']
            if 'foundation' in r_values:
                insulation.foundation_r_value = r_values['foundation']
        
        # Determine window type from text
        if re.search(r'\b(?:TRIPLE|3)[\s\-]*PANE\b', text, re.IGNORECASE):
            insulation.window_type = "triple_pane"
            insulation.window_u_value = 0.18
        elif re.search(r'\b(?:DOUBLE|2)[\s\-]*PANE\b', text, re.IGNORECASE):
            insulation.window_type = "double_pane"
            insulation.window_u_value = 0.30
        elif re.search(r'\bSINGLE[\s\-]*PANE\b', text, re.IGNORECASE):
            insulation.window_type = "single_pane"
            insulation.window_u_value = 1.04
        
        # Calculate confidence based on extracted data
        extracted_values = sum(1 for val in [
            insulation.wall_r_value != 20.0,  # Default changed
            insulation.ceiling_r_value != 49.0,
            insulation.window_type != "double_pane"
        ])
        insulation.confidence_score = min(extracted_values / 3.0, 1.0)
        
        return insulation
    
    def _identify_extraction_gaps(self, result: ExtractionResult) -> ExtractionGaps:
        """
        Identify missing data and provide recommendations
        """
        gaps = ExtractionGaps()
        
        # Check for missing required fields
        if not result.project_info.zip_code:
            gaps.missing_required_fields.append("zip_code")
            gaps.critical_gaps.append("ZIP code required for climate zone determination")
        
        if result.building_chars.total_area <= 0:
            gaps.missing_required_fields.append("total_area")
            gaps.critical_gaps.append("Building area required for load calculations")
        
        if not result.rooms:
            gaps.missing_required_fields.append("rooms")
            gaps.critical_gaps.append("At least one room required for HVAC design")
        
        # Check for low confidence fields
        confidence_threshold = 0.5
        
        if result.project_info.confidence_score < confidence_threshold:
            gaps.low_confidence_fields.append("project_info")
        
        if result.building_chars.confidence_score < confidence_threshold:
            gaps.low_confidence_fields.append("building_characteristics")
        
        if result.insulation.confidence_score < confidence_threshold:
            gaps.low_confidence_fields.append("insulation_specs")
            gaps.assumptions_made.append("Using standard insulation values for calculations")
        
        # Generate recommendations
        if gaps.missing_required_fields:
            gaps.recommendations.append("Please verify and provide missing required information")
        
        if gaps.low_confidence_fields:
            gaps.recommendations.append("Consider manual verification of extracted data")
        
        if result.building_chars.total_area > 0 and result.rooms:
            total_room_area = sum(room.area for room in result.rooms)
            if total_room_area < result.building_chars.total_area * 0.6:
                gaps.recommendations.append("Room areas seem low compared to total building area")
        
        return gaps
    
    def _determine_room_occupancy(self, room_name: str) -> int:
        """
        Determine typical occupancy for room types
        """
        room_name = room_name.upper()
        
        occupancy_map = {
            'MASTER': 2, 'MASTER BEDROOM': 2, 'MASTER BR': 2,
            'BEDROOM': 1, 'BR': 1, 'GUEST': 1,
            'LIVING': 4, 'LIVING ROOM': 4, 'FAMILY': 4, 'FAMILY ROOM': 4,
            'KITCHEN': 2, 'DINING': 4, 'DINING ROOM': 4,
            'OFFICE': 1, 'DEN': 1, 'STUDY': 1,
            'BATHROOM': 0, 'BA': 0, 'POWDER': 0,
            'LAUNDRY': 0, 'UTILITY': 0, 'GARAGE': 0,
            'CLOSET': 0, 'PANTRY': 0, 'STORAGE': 0
        }
        
        for key, occupancy in occupancy_map.items():
            if key in room_name:
                return occupancy
        
        return 1  # Default occupancy
    
    def _estimate_room_area_from_dimensions(self, text: str, room_name: str) -> float:
        """
        Estimate room area from dimensions found in text
        """
        # Look for dimensions near the room name
        room_context = self._extract_room_context(text, room_name)
        
        dimension_matches = self._pattern_cache['dimension_pattern'].findall(room_context)
        
        if dimension_matches:
            try:
                length = float(dimension_matches[0][0])
                width = float(dimension_matches[0][1])
                return length * width
            except (ValueError, IndexError):
                pass
        
        return 0.0
    
    def _extract_room_context(self, text: str, room_name: str, context_size: int = 200) -> str:
        """
        Extract text context around a room name mention
        """
        room_pattern = re.compile(re.escape(room_name), re.IGNORECASE)
        match = room_pattern.search(text)
        
        if match:
            start = max(0, match.start() - context_size)
            end = min(len(text), match.end() + context_size)
            return text[start:end]
        
        return ""
    
    def _count_pattern_matches(self, text: str) -> int:
        """
        Count total pattern matches for metrics
        """
        total_matches = 0
        matches = self.patterns.extract_all_matches(text)
        
        for pattern_type, pattern_matches in matches.items():
            total_matches += len(pattern_matches)
        
        return total_matches
    
    def _update_stats(self, processing_time: float, confidence: float):
        """
        Update processing statistics
        """
        self.stats['files_processed'] += 1
        
        # Update running average
        prev_avg = self.stats['avg_processing_time']
        n = self.stats['files_processed']
        self.stats['avg_processing_time'] = (prev_avg * (n - 1) + processing_time) / n
        
        # Update accuracy
        prev_accuracy = self.stats['extraction_accuracy']
        self.stats['extraction_accuracy'] = (prev_accuracy * (n - 1) + confidence) / n
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        """
        cache_hit_rate = 0.0
        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses'])
        
        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'pattern_stats': self.patterns.get_pattern_stats(),
            'cache_size': len(self._text_cache) + len(self._pattern_cache)
        }
    
    def clear_cache(self):
        """
        Clear processing caches
        """
        self._text_cache.clear()
        logger.info("Processing caches cleared")

# Global processor instance for reuse
_global_processor: Optional[BlueprintProcessor] = None

def get_processor() -> BlueprintProcessor:
    """Get global processor instance (singleton)"""
    global _global_processor
    if _global_processor is None:
        _global_processor = BlueprintProcessor()
    return _global_processor

# Convenience functions
async def process_blueprint_async(file_path: Union[str, Path], job_id: str = None, 
                                 project_info: Dict = None) -> ExtractionResult:
    """Async convenience function"""
    processor = get_processor()
    return await processor.process_blueprint_async(file_path, job_id, project_info)

def process_blueprint_sync(file_path: Union[str, Path], job_id: str = None, 
                          project_info: Dict = None) -> ExtractionResult:
    """Sync convenience function"""
    processor = get_processor()
    return processor.process_blueprint(file_path, job_id, project_info)