"""
Blueprint Parser Service for AutoHVAC
Main service that orchestrates PDF to JSON conversion with comprehensive error handling
Implements the JSON-first architecture where all processing uses canonical JSON representation
"""

import os
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4

from app.parser.schema import (
    BlueprintSchema, ParsingMetadata, ParsingStatus, PageAnalysisResult,
    ParsedDimension, ParsedLabel, GeometricElement, Room
)
from app.parser.text_parser import TextParser
from app.parser.geometry_parser import GeometryParser
from app.parser.ai_cleanup import cleanup, AICleanupError
from services.pdf_thread_manager import pdf_thread_manager, PDFDocumentClosedError, PDFProcessingTimeoutError
from services.pdf_page_analyzer import PDFPageAnalyzer
from services.blueprint_ai_parser import blueprint_ai_parser, BlueprintAIParsingError

logger = logging.getLogger(__name__)


class BlueprintParsingError(Exception):
    """Custom exception for blueprint parsing failures"""
    pass


class BlueprintParser:
    """
    Main blueprint parser service that converts PDF files to comprehensive JSON
    
    This service implements the JSON-first architecture:
    1. Parse PDF once into comprehensive JSON
    2. Store JSON as canonical representation
    3. All further processing uses JSON only
    4. Thread-safe PDF handling prevents document closed errors
    """
    
    def __init__(self, ai_timeout: int = 300, geometry_timeout: int = 300):
        self.ai_timeout = ai_timeout
        self.geometry_timeout = geometry_timeout
        self.text_parser = TextParser()
        self.geometry_parser = GeometryParser()
        self.page_analyzer = PDFPageAnalyzer(timeout_per_page=30, max_pages=20)
        
    def parse_pdf_to_json(
        self, 
        pdf_path: str, 
        filename: str,
        zip_code: str,
        project_id: Optional[str] = None
    ) -> BlueprintSchema:
        """
        Convert PDF blueprint to comprehensive JSON representation
        
        Args:
            pdf_path: Path to PDF file
            filename: Original filename for metadata
            zip_code: Project location
            project_id: Optional project ID (generates UUID if None)
            
        Returns:
            BlueprintSchema with complete parsed data and metadata
            
        Raises:
            BlueprintParsingError: If parsing fails critically
        """
        # Check if GPT-4V parsing is enabled
        use_gpt4v = os.getenv("USE_GPT4V_PARSING", "false").lower() == "true"
        
        if use_gpt4v:
            logger.info(f"Using GPT-4V parsing for {filename}")
            try:
                # Use async context to run the AI parser
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        blueprint_ai_parser.parse_pdf_with_gpt4v(pdf_path, filename, zip_code, project_id)
                    )
                    logger.info(f"GPT-4V parsing completed successfully for {filename}")
                    return result
                finally:
                    loop.close()
            except BlueprintAIParsingError as e:
                logger.error(f"GPT-4V parsing failed for {filename}, falling back to traditional parsing: {str(e)}")
                # Fall through to traditional parsing
            except Exception as e:
                logger.error(f"Unexpected error in GPT-4V parsing for {filename}, falling back to traditional parsing: {str(e)}")
                # Fall through to traditional parsing
        
        # Traditional parsing pipeline (existing code)
        logger.info(f"Using traditional parsing for {filename}")
        start_time = time.time()
        parsing_metadata = ParsingMetadata(
            parsing_timestamp=datetime.utcnow(),
            processing_time_seconds=0.0,  # Will be set at end
            pdf_filename=filename,
            pdf_page_count=0,  # Will be determined
            selected_page=1,  # Default, will be updated
            geometry_status=ParsingStatus.FAILED,
            text_status=ParsingStatus.FAILED,
            ai_status=ParsingStatus.FAILED,
            overall_confidence=0.0,
            geometry_confidence=0.0,
            text_confidence=0.0
        )
        
        logger.info(f"Starting traditional blueprint parsing for {filename}")
        
        try:
            # Stage 1: Multi-page analysis and best page selection
            logger.info("Stage 1: Analyzing PDF pages for best floor plan")
            page_analyses, selected_page = self._analyze_pages(pdf_path, parsing_metadata)
            
            # Stage 2: Extract geometry from selected page
            logger.info(f"Stage 2: Extracting geometry from page {selected_page}")
            raw_geometry, geometry_elements = self._extract_geometry(pdf_path, selected_page - 1, parsing_metadata)
            
            # Stage 3: Extract text from selected page
            logger.info(f"Stage 3: Extracting text from page {selected_page}")
            raw_text, parsed_labels, parsed_dimensions = self._extract_text(pdf_path, selected_page - 1, parsing_metadata)
            
            # Stage 4: AI analysis and room identification
            logger.info("Stage 4: AI analysis and room identification")
            rooms = self._perform_ai_analysis(raw_geometry, raw_text, zip_code, parsing_metadata)
            
            # Stage 5: Compile final blueprint schema
            logger.info("Stage 5: Compiling final blueprint schema")
            blueprint_schema = self._compile_blueprint_schema(
                project_id=project_id or str(uuid4()),
                zip_code=zip_code,
                rooms=rooms,
                raw_geometry=raw_geometry,
                raw_text=raw_text,
                parsed_labels=parsed_labels,
                parsed_dimensions=parsed_dimensions,
                geometry_elements=geometry_elements,
                parsing_metadata=parsing_metadata
            )
            
            # Update final metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            parsing_metadata.overall_confidence = self._calculate_overall_confidence(parsing_metadata)
            blueprint_schema.parsing_metadata = parsing_metadata
            
            logger.info(f"Blueprint parsing completed successfully in {parsing_metadata.processing_time_seconds:.2f}s")
            logger.info(f"Identified {len(rooms)} rooms with overall confidence {parsing_metadata.overall_confidence:.2f}")
            
            return blueprint_schema
            
        except Exception as e:
            # Record error in metadata
            parsing_metadata.processing_time_seconds = time.time() - start_time
            parsing_metadata.errors_encountered.append({
                'stage': 'overall',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': time.time()
            })
            
            logger.error(f"Blueprint parsing failed for {filename}: {type(e).__name__}: {str(e)}")
            
            # Try to return partial results if any stages succeeded
            if parsing_metadata.geometry_status == ParsingStatus.SUCCESS or parsing_metadata.text_status == ParsingStatus.SUCCESS:
                logger.info("Returning partial results due to processing error")
                return self._create_partial_blueprint(zip_code, project_id, parsing_metadata, str(e))
            else:
                raise BlueprintParsingError(f"Failed to parse blueprint {filename}: {str(e)}")
    
    def _analyze_pages(self, pdf_path: str, metadata: ParsingMetadata) -> tuple[List[PageAnalysisResult], int]:
        """Analyze all PDF pages and select the best one for processing"""
        try:
            selected_page, analyses = self.page_analyzer.analyze_pdf_pages(pdf_path)
            
            # Convert to our schema format
            page_results = []
            for analysis in analyses:
                page_result = PageAnalysisResult(
                    page_number=analysis.page_number,
                    selected=analysis.selected,
                    score=analysis.score,
                    rectangle_count=analysis.rectangle_count,
                    room_label_count=analysis.room_label_count,
                    dimension_count=analysis.dimension_count,
                    geometric_complexity=analysis.geometric_complexity,
                    text_element_count=analysis.text_element_count,
                    processing_time_seconds=analysis.processing_time,
                    too_complex=analysis.too_complex,
                    errors=([analysis.error] if analysis.error else [])
                )
                page_results.append(page_result)
            
            metadata.page_analyses = page_results
            metadata.pdf_page_count = len(analyses)
            metadata.selected_page = selected_page
            
            return page_results, selected_page
            
        except Exception as e:
            logger.warning(f"Multi-page analysis failed, using page 1: {str(e)}")
            metadata.warnings.append(f"Multi-page analysis failed: {str(e)}")
            metadata.pdf_page_count = 1
            metadata.selected_page = 1
            
            # Create minimal page analysis
            fallback_analysis = PageAnalysisResult(
                page_number=1,
                selected=True,
                score=0.0,
                rectangle_count=0,
                room_label_count=0,
                dimension_count=0,
                geometric_complexity=0,
                text_element_count=0,
                processing_time_seconds=0.0,
                errors=[str(e)]
            )
            metadata.page_analyses = [fallback_analysis]
            
            return [fallback_analysis], 1
    
    def _extract_geometry(self, pdf_path: str, page_number: int, metadata: ParsingMetadata) -> tuple[Dict[str, Any], List[GeometricElement]]:
        """Extract geometry from PDF page with thread safety"""
        try:
            def geometry_operation(path: str):
                return self.geometry_parser.parse(path, page_number=page_number)
            
            raw_geometry = pdf_thread_manager.process_pdf_with_retry(
                pdf_path=pdf_path,
                processor_func=geometry_operation,
                operation_name="geometry_extraction",
                max_retries=2,
                timeout_seconds=self.geometry_timeout
            )
            
            # Convert to structured elements
            geometry_elements = self._convert_raw_geometry_to_elements(raw_geometry)
            
            metadata.geometry_status = ParsingStatus.SUCCESS
            metadata.geometry_confidence = self._calculate_geometry_confidence(raw_geometry)
            
            logger.info(f"Geometry extraction successful: {len(geometry_elements)} elements")
            return raw_geometry.__dict__, geometry_elements
            
        except PDFProcessingTimeoutError as e:
            logger.error(f"Geometry extraction timed out: {str(e)}")
            metadata.geometry_status = ParsingStatus.TIMEOUT
            metadata.errors_encountered.append({
                'stage': 'geometry',
                'error': str(e),
                'error_type': 'timeout'
            })
            return {}, []
            
        except Exception as e:
            logger.error(f"Geometry extraction failed: {type(e).__name__}: {str(e)}")
            metadata.geometry_status = ParsingStatus.FAILED
            metadata.errors_encountered.append({
                'stage': 'geometry',
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {}, []
    
    def _extract_text(self, pdf_path: str, page_number: int, metadata: ParsingMetadata) -> tuple[Dict[str, Any], List[ParsedLabel], List[ParsedDimension]]:
        """Extract text from PDF page with thread safety"""
        try:
            def text_operation(path: str):
                return self.text_parser.parse(path, page_number=page_number)
            
            raw_text = pdf_thread_manager.process_pdf_with_retry(
                pdf_path=pdf_path,
                processor_func=text_operation,
                operation_name="text_extraction",
                max_retries=2,
                timeout_seconds=120  # Text extraction should be faster
            )
            
            # Convert to structured elements
            parsed_labels = self._convert_raw_text_to_labels(raw_text)
            parsed_dimensions = self._convert_raw_text_to_dimensions(raw_text)
            
            metadata.text_status = ParsingStatus.SUCCESS
            metadata.text_confidence = self._calculate_text_confidence(raw_text)
            
            logger.info(f"Text extraction successful: {len(parsed_labels)} labels, {len(parsed_dimensions)} dimensions")
            return raw_text.__dict__, parsed_labels, parsed_dimensions
            
        except PDFProcessingTimeoutError as e:
            logger.error(f"Text extraction timed out: {str(e)}")
            metadata.text_status = ParsingStatus.TIMEOUT
            metadata.errors_encountered.append({
                'stage': 'text',
                'error': str(e),
                'error_type': 'timeout'
            })
            return {}, [], []
            
        except Exception as e:
            logger.error(f"Text extraction failed: {type(e).__name__}: {str(e)}")
            metadata.text_status = ParsingStatus.PARTIAL  # Text extraction can partially succeed
            metadata.errors_encountered.append({
                'stage': 'text',
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {}, [], []
    
    def _perform_ai_analysis(self, raw_geometry: Dict[str, Any], raw_text: Dict[str, Any], zip_code: str, metadata: ParsingMetadata) -> List[Room]:
        """Perform AI analysis to identify rooms"""
        try:
            # Convert back to schema objects for AI processing
            from app.parser.schema import RawGeometry, RawText
            
            geometry_obj = RawGeometry(**raw_geometry) if raw_geometry else None
            text_obj = RawText(**raw_text) if raw_text else None
            
            if not geometry_obj and not text_obj:
                raise AICleanupError("No geometry or text data available for AI analysis")
            
            # Run AI cleanup with timeout
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                blueprint_result = loop.run_until_complete(
                    asyncio.wait_for(
                        cleanup(geometry_obj, text_obj),
                        timeout=self.ai_timeout
                    )
                )
                
                metadata.ai_status = ParsingStatus.SUCCESS
                logger.info(f"AI analysis successful: {len(blueprint_result.rooms)} rooms identified")
                
                # Convert to our enhanced Room schema and add metadata
                enhanced_rooms = []
                for room in blueprint_result.rooms:
                    enhanced_room = Room(
                        name=room.name,
                        dimensions_ft=room.dimensions_ft,
                        floor=room.floor,
                        windows=room.windows,
                        orientation=room.orientation,
                        area=room.area,
                        room_type=getattr(room, 'room_type', 'unknown'),
                        confidence=0.8,  # AI-identified rooms have good confidence
                        center_position=(0.0, 0.0),  # Will be calculated from geometry
                        label_found=True,  # Assume AI found labels
                        dimensions_source="ai_analysis"
                    )
                    enhanced_rooms.append(enhanced_room)
                
                return enhanced_rooms
                
            finally:
                loop.close()
                
        except asyncio.TimeoutError:
            logger.error(f"AI analysis timed out after {self.ai_timeout} seconds")
            metadata.ai_status = ParsingStatus.TIMEOUT
            metadata.errors_encountered.append({
                'stage': 'ai',
                'error': f"AI analysis timed out after {self.ai_timeout} seconds",
                'error_type': 'timeout'
            })
            return self._create_fallback_rooms(raw_geometry, raw_text)
            
        except Exception as e:
            logger.error(f"AI analysis failed: {type(e).__name__}: {str(e)}")
            metadata.ai_status = ParsingStatus.FAILED
            metadata.errors_encountered.append({
                'stage': 'ai',
                'error': str(e),
                'error_type': type(e).__name__
            })
            return self._create_fallback_rooms(raw_geometry, raw_text)
    
    def _create_fallback_rooms(self, raw_geometry: Dict[str, Any], raw_text: Dict[str, Any]) -> List[Room]:
        """Create fallback rooms when AI analysis fails"""
        rooms = []
        
        # Try to create rooms from geometry rectangles
        if raw_geometry and 'rectangles' in raw_geometry:
            rectangles = raw_geometry['rectangles']
            for i, rect in enumerate(rectangles[:10]):  # Limit to 10 rooms
                if rect.get('area', 0) > 50:  # Minimum room size
                    room = Room(
                        name=f"Room {i+1}",
                        dimensions_ft=(rect.get('width', 100) / 12, rect.get('height', 100) / 12),  # Convert to feet
                        floor=1,
                        windows=1,
                        orientation="",
                        area=rect.get('area', 100),
                        room_type="unknown",
                        confidence=0.3,  # Low confidence for fallback
                        center_position=(rect.get('center_x', 0), rect.get('center_y', 0)),
                        label_found=False,
                        dimensions_source="geometry_fallback"
                    )
                    rooms.append(room)
        
        # If no geometry rooms, create minimal room
        if not rooms:
            rooms.append(Room(
                name="Unknown Room",
                dimensions_ft=(20.0, 15.0),
                floor=1,
                windows=2,
                orientation="",
                area=300.0,
                room_type="unknown",
                confidence=0.1,
                center_position=(0.0, 0.0),
                label_found=False,
                dimensions_source="estimated"
            ))
        
        logger.info(f"Created {len(rooms)} fallback rooms")
        return rooms
    
    def _convert_raw_geometry_to_elements(self, raw_geometry) -> List[GeometricElement]:
        """Convert raw geometry to structured GeometricElement objects"""
        elements = []
        
        if not raw_geometry:
            return elements
        
        # Convert lines
        for line in getattr(raw_geometry, 'lines', []):
            element = GeometricElement(
                element_type="line",
                coordinates=[line.get('x0', 0), line.get('y0', 0), line.get('x1', 0), line.get('y1', 0)],
                properties={
                    'length': line.get('length', 0),
                    'width': line.get('width', 1),
                    'orientation': line.get('orientation', 'unknown')
                },
                confidence=line.get('wall_probability', 0.5),
                classification=line.get('line_type', 'unknown')
            )
            elements.append(element)
        
        # Convert rectangles
        for rect in getattr(raw_geometry, 'rectangles', []):
            element = GeometricElement(
                element_type="rectangle",
                coordinates=[rect.get('x0', 0), rect.get('y0', 0), rect.get('x1', 0), rect.get('y1', 0)],
                properties={
                    'area': rect.get('area', 0),
                    'width': rect.get('width', 0),
                    'height': rect.get('height', 0)
                },
                confidence=rect.get('room_probability', 0.5),
                classification="room_boundary"
            )
            elements.append(element)
        
        return elements
    
    def _convert_raw_text_to_labels(self, raw_text) -> List[ParsedLabel]:
        """Convert raw text to structured ParsedLabel objects"""
        labels = []
        
        if not raw_text:
            return labels
        
        for label in getattr(raw_text, 'room_labels', []):
            parsed_label = ParsedLabel(
                text=label.get('text', ''),
                position=(label.get('x0', 0), label.get('top', 0)),
                label_type=label.get('room_type', 'room'),
                confidence=label.get('confidence', 0.5),
                font_size=label.get('size', 12)
            )
            labels.append(parsed_label)
        
        return labels
    
    def _convert_raw_text_to_dimensions(self, raw_text) -> List[ParsedDimension]:
        """Convert raw text to structured ParsedDimension objects"""
        dimensions = []
        
        if not raw_text:
            return dimensions
        
        for dim in getattr(raw_text, 'dimensions', []):
            parsed_dim = ParsedDimension(
                text=dim.get('dimension_text', ''),
                width_ft=dim.get('parsed_dimensions', [0, 0])[0],
                length_ft=dim.get('parsed_dimensions', [0, 0])[1] if len(dim.get('parsed_dimensions', [])) > 1 else 0,
                position=(dim.get('x0', 0), dim.get('top', 0)),
                confidence=dim.get('confidence', 0.5),
                dimension_type="room"
            )
            dimensions.append(parsed_dim)
        
        return dimensions
    
    def _calculate_geometry_confidence(self, raw_geometry) -> float:
        """Calculate geometry parsing confidence"""
        if not raw_geometry:
            return 0.0
        
        line_count = len(getattr(raw_geometry, 'lines', []))
        rect_count = len(getattr(raw_geometry, 'rectangles', []))
        
        if line_count > 20 and rect_count > 3:
            return 0.9
        elif line_count > 10 and rect_count > 1:
            return 0.7
        elif line_count > 5 or rect_count > 0:
            return 0.5
        else:
            return 0.2
    
    def _calculate_text_confidence(self, raw_text) -> float:
        """Calculate text parsing confidence"""
        if not raw_text:
            return 0.0
        
        room_labels = len(getattr(raw_text, 'room_labels', []))
        dimensions = len(getattr(raw_text, 'dimensions', []))
        
        if room_labels > 5 and dimensions > 3:
            return 0.9
        elif room_labels > 2 and dimensions > 1:
            return 0.7
        elif room_labels > 0 or dimensions > 0:
            return 0.5
        else:
            return 0.2
    
    def _calculate_overall_confidence(self, metadata: ParsingMetadata) -> float:
        """Calculate overall parsing confidence"""
        confidence_factors = []
        
        if metadata.geometry_status == ParsingStatus.SUCCESS:
            confidence_factors.append(metadata.geometry_confidence)
        
        if metadata.text_status == ParsingStatus.SUCCESS:
            confidence_factors.append(metadata.text_confidence)
        
        if metadata.ai_status == ParsingStatus.SUCCESS:
            confidence_factors.append(0.8)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.1
    
    def _compile_blueprint_schema(
        self,
        project_id: str,
        zip_code: str,
        rooms: List[Room],
        raw_geometry: Dict[str, Any],
        raw_text: Dict[str, Any],
        parsed_labels: List[ParsedLabel],
        parsed_dimensions: List[ParsedDimension],
        geometry_elements: List[GeometricElement],
        parsing_metadata: ParsingMetadata
    ) -> BlueprintSchema:
        """Compile all parsed data into final BlueprintSchema"""
        
        # Calculate totals
        total_area = sum(room.area for room in rooms)
        max_floor = max((room.floor for room in rooms), default=1)
        
        return BlueprintSchema(
            project_id=project_id,
            zip_code=zip_code,
            sqft_total=total_area,
            stories=max_floor,
            rooms=rooms,
            raw_geometry=raw_geometry,
            raw_text=raw_text,
            dimensions=parsed_dimensions,
            labels=parsed_labels,
            geometric_elements=geometry_elements,
            parsing_metadata=parsing_metadata
        )
    
    def _create_partial_blueprint(self, zip_code: str, project_id: Optional[str], metadata: ParsingMetadata, error: str) -> BlueprintSchema:
        """Create partial blueprint when parsing fails"""
        fallback_room = Room(
            name="Parsing Failed - Unknown Room",
            dimensions_ft=(20.0, 15.0),
            floor=1,
            windows=2,
            orientation="",
            area=300.0,
            room_type="unknown",
            confidence=0.0,
            center_position=(0.0, 0.0),
            label_found=False,
            dimensions_source="error_fallback"
        )
        
        return BlueprintSchema(
            project_id=project_id or str(uuid4()),
            zip_code=zip_code,
            sqft_total=300.0,
            stories=1,
            rooms=[fallback_room],
            raw_geometry={},
            raw_text={},
            dimensions=[],
            labels=[],
            geometric_elements=[],
            parsing_metadata=metadata
        )


# Global instance
blueprint_parser = BlueprintParser()


# Convenience function
def parse_blueprint_to_json(
    pdf_path: str,
    filename: str,
    zip_code: str,
    project_id: Optional[str] = None
) -> BlueprintSchema:
    """
    Convenience function to parse blueprint PDF to JSON
    
    Args:
        pdf_path: Path to PDF file
        filename: Original filename
        zip_code: Project location
        project_id: Optional project ID
        
    Returns:
        BlueprintSchema with complete parsed data
    """
    return blueprint_parser.parse_pdf_to_json(pdf_path, filename, zip_code, project_id)