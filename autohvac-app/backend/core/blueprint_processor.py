#!/usr/bin/env python3
"""
Unified High-Performance Blueprint Processor for AutoHVAC
Consolidates all blueprint processing functionality with optimized performance
"""

import fitz  # PyMuPDF
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
import concurrent.futures
from threading import Lock
import hashlib

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory caching only")

from .data_models import (
    ExtractionResult, ProjectInfo, BuildingCharacteristics, Room, 
    InsulationSpecs, ExtractionGaps, ExtractionMetrics, ProcessingStatus,
    BuildingType, validate_extraction_result
)
from .extraction_patterns import get_patterns, PatternType

# Set up logging
logger = logging.getLogger(__name__)

class SmartCache:
    """
    Intelligent caching layer with Redis fallback to in-memory
    """
    
    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.redis_client = None
        self._memory_cache = {}
        self._cache_lock = Lock()
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
                self.redis_client = None
        else:
            logger.info("Using in-memory caching (Redis not available)")
    
    def _generate_key(self, content: str) -> str:
        """Generate cache key from content"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory cache
        with self._cache_lock:
            return self._memory_cache.get(key)
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        
        if self.redis_client:
            try:
                return self.redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory cache
        with self._cache_lock:
            self._memory_cache[key] = value
            return True
    
    async def get_async(self, key: str) -> Optional[str]:
        """Async get value from cache"""
        return await asyncio.to_thread(self.get, key)
    
    async def set_async(self, key: str, value: str, ttl: int = None) -> bool:
        """Async set value in cache"""
        return await asyncio.to_thread(self.set, key, value, ttl)
    
    def get_extraction_cache_key(self, file_path: Path, file_size: int, mtime: float) -> str:
        """Generate cache key for extraction results"""
        content = f"{file_path.name}:{file_size}:{mtime}"
        return f"extraction:{self._generate_key(content)}"
    
    def get_calculation_cache_key(self, extraction_data: Dict) -> str:
        """Generate cache key for calculation results"""
        # Create deterministic key from extraction data
        key_data = {
            'total_area': extraction_data.get('building_chars', {}).get('total_area', 0),
            'rooms_count': len(extraction_data.get('rooms', [])),
            'zip_code': extraction_data.get('project_info', {}).get('zip_code', ''),
            'construction_type': extraction_data.get('building_chars', {}).get('construction_type', '')
        }
        content = json.dumps(key_data, sort_keys=True)
        return f"calculation:{self._generate_key(content)}"

class BlueprintProcessor:
    """
    High-performance blueprint processor with caching, pre-compiled patterns,
    and intelligent extraction algorithms
    """
    
    def __init__(self, enable_caching: bool = True, redis_url: str = None):
        self.enable_caching = enable_caching
        self._pattern_cache: Dict[str, Any] = {}
        self.smart_cache = SmartCache(redis_url) if enable_caching else None
        self.patterns = get_patterns()
        self._cache_lock = Lock()  # Thread safety for caching
        
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
        
        cache_type = "Redis/Memory" if self.smart_cache and self.smart_cache.redis_client else "Memory"
        logger.info(f"BlueprintProcessor initialized with {cache_type} caching and parallel processing")
    
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
                                     project_info: Dict = None, progress_callback = None) -> ExtractionResult:
        """
        Asynchronously process a blueprint file with progress updates
        """
        return await asyncio.to_thread(self.process_blueprint, file_path, job_id, project_info, progress_callback)
    
    def process_blueprint(self, file_path: Union[str, Path], job_id: str = None, 
                         project_info: Dict = None, progress_callback = None) -> ExtractionResult:
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
        
        def update_progress(stage: str, percentage: int, message: str = ""):
            """Helper function to update progress"""
            if progress_callback:
                progress_callback(job_id, stage, percentage, message)
        
        try:
            logger.info(f"Processing blueprint: {file_path} (Job ID: {job_id})")
            update_progress("initializing", 5, "Starting blueprint processing")
            
            # Extract text from PDF
            update_progress("extracting_text", 15, "Extracting text from PDF pages")
            text_content = self._extract_text_from_pdf(file_path)
            if not text_content:
                raise ValueError("No text content extracted from PDF")
            
            update_progress("text_extracted", 30, f"Extracted text from PDF ({len(text_content)} characters)")
            
            # Store raw text for debugging
            result.raw_data['extracted_text'] = text_content[:5000]  # First 5000 chars
            result.raw_data['file_size'] = Path(file_path).stat().st_size
            result.raw_data['file_name'] = Path(file_path).name
            
            # Perform comprehensive extraction
            update_progress("pattern_matching", 45, "Running pattern matching and data extraction")
            result = self._perform_comprehensive_extraction(result, text_content, project_info)
            
            update_progress("validating", 80, "Validating extracted data")
            # Calculate overall confidence and validate
            result.calculate_overall_confidence()
            validation_issues = validate_extraction_result(result)
            
            if validation_issues:
                result.processing_notes.extend(validation_issues)
                logger.warning(f"Validation issues found: {validation_issues}")
            
            update_progress("finalizing", 95, "Finalizing results")
            # Finalize result
            result.status = ProcessingStatus.COMPLETED
            result.completed_at = datetime.now()
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, result.overall_confidence)
            
            result.extraction_metrics.extraction_time_seconds = processing_time
            
            update_progress("completed", 100, f"Processing completed in {processing_time:.2f}s")
            
            logger.info(f"Blueprint processing completed in {processing_time:.2f}s "
                       f"with {result.overall_confidence:.2f} confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"Blueprint processing failed: {str(e)}", exc_info=True)
            result.status = ProcessingStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            return result
    
    async def _extract_text_from_pdf_async(self, file_path: Union[str, Path]) -> str:
        """
        High-performance text extraction using PyMuPDF with smart caching
        """
        file_path = Path(file_path)
        file_stat = file_path.stat()
        
        # Check smart cache first (async)
        if self.smart_cache:
            cache_key = self.smart_cache.get_extraction_cache_key(
                file_path, file_stat.st_size, file_stat.st_mtime
            )
            
            cached_text = await self.smart_cache.get_async(cache_key)
            if cached_text:
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit for PDF text extraction: {file_path.name}")
                return cached_text
        
        self.stats['cache_misses'] += 1
        
        try:
            # Open document with PyMuPDF (async file I/O)
            doc = await asyncio.to_thread(fitz.open, str(file_path))
            page_count = len(doc)
            
            if page_count == 0:
                await asyncio.to_thread(doc.close)
                raise ValueError("PDF contains no pages")
            
            logger.debug(f"Processing {page_count} pages with parallel extraction")
            
            # Use parallel processing for pages if document is large enough
            if page_count > 3:
                text_content = await asyncio.to_thread(self._extract_pages_parallel, doc)
            else:
                text_content = await asyncio.to_thread(self._extract_pages_sequential, doc)
            
            await asyncio.to_thread(doc.close)
            
            full_text = '\n'.join(text_content)
            
            # Cache the result in smart cache (async)
            if self.smart_cache:
                cache_key = self.smart_cache.get_extraction_cache_key(
                    file_path, file_stat.st_size, file_stat.st_mtime
                )
                await self.smart_cache.set_async(cache_key, full_text, ttl=7200)  # 2 hours TTL
            
            logger.debug(f"Extracted {len(full_text)} characters from {page_count} pages")
            return full_text
                
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"PDF text extraction failed: {e}")
    
    def _extract_text_from_pdf(self, file_path: Union[str, Path]) -> str:
        """
        Synchronous wrapper for async PDF text extraction
        """
        # If we're in an async context, use the async version
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context but called sync method
                # This should not happen in normal usage
                logger.warning("Sync PDF extraction called from async context")
                return asyncio.run_coroutine_threadsafe(
                    self._extract_text_from_pdf_async(file_path), loop
                ).result()
            else:
                return asyncio.run(self._extract_text_from_pdf_async(file_path))
        except RuntimeError:
            # No event loop, run the async function
            return asyncio.run(self._extract_text_from_pdf_async(file_path))
    
    def _extract_pages_parallel(self, doc: fitz.Document) -> List[str]:
        """Extract text from pages in parallel with intelligent page filtering"""
        text_content = [''] * len(doc)  # Pre-allocate list
        
        def extract_page_text(page_num: int) -> Tuple[int, str]:
            """Extract text from a single page with relevance filtering"""
            try:
                page = doc[page_num]
                page_text = page.get_text()
                
                # Skip irrelevant pages using smart filtering
                if not self._is_relevant_page(page_text, page_num, len(doc)):
                    return page_num, ""
                    
                return page_num, page_text
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                return page_num, ""
        
        # Use ThreadPoolExecutor for parallel page processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(extract_page_text, i) for i in range(len(doc))]
            
            for future in concurrent.futures.as_completed(futures):
                page_num, page_text = future.result()
                if page_text:
                    text_content[page_num] = page_text
        
        # Filter out empty pages
        return [text for text in text_content if text]
    
    def _extract_pages_sequential(self, doc: fitz.Document) -> List[str]:
        """Extract text from pages sequentially with intelligent filtering"""
        text_content = []
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                
                # Use same relevance filtering as parallel method
                if page_text.strip() and self._is_relevant_page(page_text, page_num, len(doc)):
                    text_content.append(page_text)
                elif page_text.strip():
                    logger.debug(f"Filtered out page {page_num} as irrelevant")
                    
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                continue
                
        return text_content
    
    def _is_relevant_page(self, page_text: str, page_num: int, total_pages: int) -> bool:
        """
        Determine if a page is relevant for HVAC blueprint processing
        """
        text_clean = page_text.strip()
        
        # Skip obviously empty pages
        if len(text_clean) < 30:
            return False
        
        # Skip cover pages (usually first page with title info only)
        if page_num == 0:
            # Check if it's likely a cover page
            cover_indicators = [
                'title page', 'cover sheet', 'project information',
                'drawing index', 'sheet index', 'revision', 'drawing list'
            ]
            text_lower = text_clean.lower()
            
            # If it has HVAC content, keep it even if it's the first page
            hvac_indicators = [
                'hvac', 'heating', 'cooling', 'duct', 'air conditioning',
                'ventilation', 'cfm', 'btu', 'ton', 'equipment', 'unit'
            ]
            
            has_hvac_content = any(indicator in text_lower for indicator in hvac_indicators)
            has_cover_content = any(indicator in text_lower for indicator in cover_indicators)
            
            if has_cover_content and not has_hvac_content and len(text_clean) < 500:
                logger.debug(f"Skipping cover page {page_num}")
                return False
        
        # Skip index/table of contents pages
        index_indicators = [
            'table of contents', 'drawing index', 'sheet list',
            'drawing list', 'index of drawings', 'sheet index'
        ]
        text_lower = text_clean.lower()
        if any(indicator in text_lower for indicator in index_indicators):
            # Unless it contains actual room or area data
            if not any(word in text_lower for word in ['sf', 'sq ft', 'area', 'room']):
                logger.debug(f"Skipping index page {page_num}")
                return False
        
        # Skip pages that are mostly administrative text
        admin_indicators = [
            'general notes', 'legend', 'abbreviations', 'symbols',
            'code compliance', 'specifications', 'standard details'
        ]
        if any(indicator in text_lower for indicator in admin_indicators):
            # Unless they contain area or room information
            area_indicators = ['area', 'sq ft', 'sf', 'room', 'space']
            if not any(indicator in text_lower for indicator in area_indicators):
                logger.debug(f"Skipping administrative page {page_num}")
                return False
        
        # Keep pages with HVAC-relevant content
        hvac_keywords = [
            'hvac', 'heating', 'cooling', 'air conditioning', 'ventilation',
            'duct', 'cfm', 'btu', 'ton', 'unit', 'equipment', 'mechanical',
            'room', 'area', 'sq ft', 'sf', 'floor plan', 'space',
            'bedroom', 'bathroom', 'kitchen', 'living', 'dining'
        ]
        
        relevant_content = sum(1 for keyword in hvac_keywords if keyword in text_lower)
        
        # Keep if it has multiple relevant keywords or significant text with some keywords
        if relevant_content >= 2 or (relevant_content >= 1 and len(text_clean) > 200):
            return True
        
        # Skip pages with very little content
        if len(text_clean) < 100:
            logger.debug(f"Skipping minimal content page {page_num}")
            return False
        
        return True
    
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