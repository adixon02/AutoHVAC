"""
Pipeline Orchestrator - Clean, single-responsibility pipeline coordination
Each stage has one job and communicates through strict contracts
"""

import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

from services.pipeline_context import pipeline_context
from services.pipeline_contracts import (
    PageClassificationOutput,
    ScaleDetectionOutput,
    GeometryExtractionOutput,
    SemanticAnalysisOutput,
    LoadCalculationOutput,
    PipelineResult,
    validate_stage_transition
)
from services.metrics_collector import metrics_collector, PipelineStage
from services.error_types import NeedsInputError

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the blueprint analysis pipeline with clear stage separation
    Each stage has a single responsibility and passes validated data to the next
    """
    
    def __init__(self):
        """Initialize orchestrator with stage handlers"""
        self.stages = {
            PipelineStage.PAGE_CLASSIFICATION: self._run_page_classification,
            PipelineStage.SCALE_DETECTION: self._run_scale_detection,
            PipelineStage.GEOMETRY_EXTRACTION: self._run_geometry_extraction,
            PipelineStage.SEMANTIC_ANALYSIS: self._run_semantic_analysis,
            PipelineStage.LOAD_CALCULATION: self._run_load_calculation,
        }
        
    def run_pipeline(
        self,
        pdf_path: str,
        zip_code: str,
        project_id: str,
        filename: str
    ) -> PipelineResult:
        """
        Run the complete pipeline with strict stage separation
        
        Args:
            pdf_path: Path to PDF file
            zip_code: Location ZIP code
            project_id: Unique project identifier
            filename: Original filename
            
        Returns:
            PipelineResult with all stage outputs
            
        Raises:
            NeedsInputError: When user input is required
            Exception: For unexpected failures
        """
        start_time = time.time()
        
        # Reset context for new pipeline
        pipeline_context.reset()
        pipeline_context.set_pdf_path(pdf_path)
        pipeline_context.set_project_info(project_id, zip_code)
        
        # Initialize metrics
        import os
        pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        import fitz
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()
        
        metrics_collector.start_pipeline(
            job_id=project_id,
            pdf_filename=filename,
            pdf_size_mb=pdf_size_mb,
            num_pages=num_pages
        )
        
        stage_outputs = {}
        
        try:
            # Run each stage in sequence
            for stage in [
                PipelineStage.PAGE_CLASSIFICATION,
                PipelineStage.SCALE_DETECTION,
                PipelineStage.GEOMETRY_EXTRACTION,
                PipelineStage.SEMANTIC_ANALYSIS,
                PipelineStage.LOAD_CALCULATION
            ]:
                logger.info(f"Starting stage: {stage.value}")
                
                # Get previous stage output if any
                prev_output = None
                if stage_outputs:
                    prev_output = list(stage_outputs.values())[-1]
                
                # Run stage with metrics tracking
                metrics_collector.start_stage(stage)
                
                try:
                    output = self.stages[stage](
                        pdf_path=pdf_path,
                        zip_code=zip_code,
                        previous_output=prev_output
                    )
                    
                    # Validate output contract
                    self._validate_stage_output(stage, output)
                    
                    stage_outputs[stage] = output
                    
                    metrics_collector.end_stage(
                        success=True,
                        output_data=output.dict() if hasattr(output, 'dict') else {}
                    )
                    
                    logger.info(f"Stage {stage.value} completed successfully")
                    
                except Exception as e:
                    metrics_collector.end_stage(
                        success=False,
                        error=str(e)
                    )
                    
                    # Re-raise with context
                    logger.error(f"Stage {stage.value} failed: {e}")
                    raise
            
            # Create final pipeline result
            result = PipelineResult(
                page_classification=stage_outputs[PipelineStage.PAGE_CLASSIFICATION],
                scale_detection=stage_outputs[PipelineStage.SCALE_DETECTION],
                geometry_extraction=stage_outputs[PipelineStage.GEOMETRY_EXTRACTION],
                semantic_analysis=stage_outputs[PipelineStage.SEMANTIC_ANALYSIS],
                load_calculation=stage_outputs[PipelineStage.LOAD_CALCULATION],
                project_id=project_id,
                filename=filename,
                zip_code=zip_code,
                processing_time_seconds=time.time() - start_time,
                total_area_sqft=stage_outputs[PipelineStage.GEOMETRY_EXTRACTION].total_area_sqft,
                num_rooms=len(stage_outputs[PipelineStage.GEOMETRY_EXTRACTION].rooms),
                overall_confidence=self._calculate_confidence(stage_outputs)
            )
            
            # End pipeline successfully
            metrics_collector.end_pipeline(
                success=True,
                results={
                    "total_area": result.total_area_sqft,
                    "num_rooms": result.num_rooms,
                    "heating_load": result.load_calculation.total_heating_btu_hr,
                    "cooling_load": result.load_calculation.total_cooling_btu_hr,
                    "confidence": result.overall_confidence
                }
            )
            
            logger.info(f"Pipeline completed successfully in {result.processing_time_seconds:.2f}s")
            return result
            
        except Exception as e:
            # End pipeline with failure
            metrics_collector.end_pipeline(
                success=False,
                error=str(e)
            )
            raise
    
    def _run_page_classification(
        self,
        pdf_path: str,
        zip_code: str,
        previous_output: Optional[Any] = None
    ) -> PageClassificationOutput:
        """
        Stage 1: Classify pages to find the floor plan
        Single responsibility: Identify which page contains the floor plan
        """
        from services.pdf_page_analyzer import PDFPageAnalyzer
        
        analyzer = PDFPageAnalyzer()
        best_page, scores = analyzer.find_best_floor_plan_page(pdf_path)
        
        # Lock the page in context
        pipeline_context.set_page(best_page, source="page_classification")
        
        # Track decision
        metrics_collector.track_decision(
            decision_type="page_selection",
            description=f"Selected page {best_page + 1} as floor plan",
            chosen_value=best_page,
            alternatives=list(scores.keys()),
            reason="Highest geometric content score"
        )
        
        return PageClassificationOutput(
            selected_page=best_page,
            total_pages=len(scores),
            page_scores=scores,
            selection_reason="Highest geometric complexity score",
            confidence=scores[best_page] / max(scores.values()) if scores else 0.5
        )
    
    def _run_scale_detection(
        self,
        pdf_path: str,
        zip_code: str,
        previous_output: Optional[PageClassificationOutput] = None
    ) -> ScaleDetectionOutput:
        """
        Stage 2: Detect scale from the blueprint
        Single responsibility: Determine pixels-per-foot conversion
        """
        from services.deterministic_scale_detector import deterministic_scale_detector
        
        # Get the locked page
        page_num = pipeline_context.get_page()
        
        # Detect scale deterministically
        scale_result = deterministic_scale_detector.detect_scale(
            pdf_path=pdf_path,
            page_num=page_num
        )
        
        # Lock scale in context
        pipeline_context.set_scale(scale_result.pixels_per_foot, source="scale_detection")
        
        # Track provenance
        metrics_collector.track_provenance(
            field="scale",
            value=scale_result.scale_notation,
            source="detected" if scale_result.confidence > 0.7 else "assumed",
            confidence=scale_result.confidence,
            notes=f"Found via {scale_result.source}"
        )
        
        return ScaleDetectionOutput(
            pixels_per_foot=scale_result.pixels_per_foot,
            scale_notation=scale_result.scale_notation,
            detection_method=scale_result.source,
            confidence=scale_result.confidence,
            source_location=scale_result.location if hasattr(scale_result, 'location') else None
        )
    
    def _run_geometry_extraction(
        self,
        pdf_path: str,
        zip_code: str,
        previous_output: Optional[ScaleDetectionOutput] = None
    ) -> GeometryExtractionOutput:
        """
        Stage 3: Extract room geometry
        Single responsibility: Find room polygons and calculate areas
        """
        from services.geometry_extractor import GeometryExtractor
        from services.pipeline_contracts import RoomGeometry
        
        # Get locked values from context
        page_num = pipeline_context.get_page()
        scale_px_per_ft = pipeline_context.get_scale()
        
        extractor = GeometryExtractor(scale_px_per_ft=scale_px_per_ft)
        rooms, building_footprint = extractor.extract_rooms(pdf_path, page_num)
        
        # Convert to contract format
        room_geometries = []
        for i, room in enumerate(rooms):
            room_geometries.append(RoomGeometry(
                id=f"room_{i+1:03d}",
                polygon=room['polygon'],
                area_sqft=room['area'],
                perimeter_ft=room['perimeter'],
                center=room['center'],
                bounding_box=room['bbox']
            ))
        
        total_area = sum(r.area_sqft for r in room_geometries)
        
        # Track room detection
        for room in room_geometries:
            metrics_collector.track_decision(
                decision_type="room_detection",
                description=f"Detected room {room.id}",
                chosen_value=room.area_sqft,
                reason="Polygon detection algorithm"
            )
        
        return GeometryExtractionOutput(
            rooms=room_geometries,
            total_area_sqft=total_area,
            exterior_perimeter_ft=extractor.calculate_perimeter(building_footprint),
            num_floors=1,  # Default, will be refined by semantic analysis
            building_footprint=building_footprint,
            extraction_method="deterministic_polygon_detection",
            confidence=0.85 if len(room_geometries) > 3 else 0.6
        )
    
    def _run_semantic_analysis(
        self,
        pdf_path: str,
        zip_code: str,
        previous_output: Optional[GeometryExtractionOutput] = None
    ) -> SemanticAnalysisOutput:
        """
        Stage 4: Add semantic information using GPT-5 Vision
        Single responsibility: Label rooms and detect building features
        """
        from services.semantic_vision_analyzer import semantic_analyzer
        from services.pipeline_contracts import RoomSemantics, BuildingEnvelopeData
        
        # Analyze with GPT-5 Vision for semantics only
        semantic_data = semantic_analyzer.analyze_semantics(
            pdf_path=pdf_path,
            page_num=pipeline_context.get_page(),
            room_geometries=previous_output.rooms,
            zip_code=zip_code
        )
        
        # Create room semantics
        room_semantics = []
        for room_geom in previous_output.rooms:
            # Find semantic data for this room
            sem_data = semantic_data.get('rooms', {}).get(room_geom.id, {})
            
            room_semantics.append(RoomSemantics(
                room_id=room_geom.id,
                name=sem_data.get('name', f"Room {room_geom.id[-3:]}"),
                room_type=sem_data.get('type', 'other'),
                windows_count=sem_data.get('windows', 0),
                doors_count=sem_data.get('doors', 1),
                exterior_walls=sem_data.get('exterior_walls', 0),
                features=sem_data.get('features', []),
                occupancy=sem_data.get('occupancy', 1)
            ))
        
        # Get envelope data
        envelope = semantic_data.get('envelope', {})
        
        # Track provenance for envelope values
        for field in ['wall_r_value', 'ceiling_r_value', 'floor_r_value']:
            if field in envelope:
                metrics_collector.track_provenance(
                    field=f"envelope.{field}",
                    value=envelope[field],
                    source="gpt5_vision",
                    confidence=0.85,
                    notes="Detected by GPT-5 Vision"
                )
        
        # Determine climate zone
        from services.climate_zone_lookup import get_climate_zone
        climate_zone = get_climate_zone(zip_code)
        
        return SemanticAnalysisOutput(
            room_semantics=room_semantics,
            building_envelope=BuildingEnvelopeData(
                wall_r_value=envelope.get('wall_r_value', 13.0),
                ceiling_r_value=envelope.get('ceiling_r_value', 30.0),
                floor_r_value=envelope.get('floor_r_value', 19.0),
                window_u_value=envelope.get('window_u_value', 0.35),
                door_u_value=envelope.get('door_u_value', 0.5),
                air_changes_per_hour=envelope.get('ach', 0.5),
                foundation_type=envelope.get('foundation', 'slab')
            ),
            climate_zone=climate_zone,
            orientation_degrees=semantic_data.get('orientation', 0),
            special_features=semantic_data.get('features', []),
            analysis_method="gpt5_vision_semantic",
            confidence=semantic_data.get('confidence', 0.75)
        )
    
    def _run_load_calculation(
        self,
        pdf_path: str,
        zip_code: str,
        previous_output: Optional[SemanticAnalysisOutput] = None
    ) -> LoadCalculationOutput:
        """
        Stage 5: Calculate HVAC loads
        Single responsibility: Compute heating/cooling requirements
        """
        from services.hvac_calculator import HVACCalculator
        from services.pipeline_contracts import RoomHVACLoad
        
        # Get geometry from context
        from services.pipeline_contracts import GeometryExtractionOutput
        geometry = self._get_stage_output(PipelineStage.GEOMETRY_EXTRACTION)
        
        calculator = HVACCalculator(
            climate_zone=previous_output.climate_zone,
            zip_code=zip_code
        )
        
        # Calculate loads for each room
        room_loads = []
        for room_geom, room_sem in zip(geometry.rooms, previous_output.room_semantics):
            loads = calculator.calculate_room_load(
                area_sqft=room_geom.area_sqft,
                room_type=room_sem.room_type,
                exterior_walls=room_sem.exterior_walls,
                windows=room_sem.windows_count,
                envelope=previous_output.building_envelope
            )
            
            room_loads.append(RoomHVACLoad(
                room_id=room_geom.id,
                heating_btu_hr=loads['heating'],
                cooling_btu_hr=loads['cooling'],
                heating_components=loads.get('heating_components', {}),
                cooling_components=loads.get('cooling_components', {})
            ))
        
        # Calculate totals
        total_heating = sum(r.heating_btu_hr for r in room_loads)
        total_cooling = sum(r.cooling_btu_hr for r in room_loads)
        
        # Apply safety factor
        safety_factor = 1.1
        total_heating *= safety_factor
        total_cooling *= safety_factor
        
        return LoadCalculationOutput(
            room_loads=room_loads,
            total_heating_btu_hr=total_heating,
            total_cooling_btu_hr=total_cooling,
            heating_system_tons=total_heating / 12000,
            cooling_system_tons=total_cooling / 12000,
            design_temperatures=calculator.get_design_temps(),
            calculation_method="ACCA Manual J",
            safety_factor=safety_factor
        )
    
    def _validate_stage_output(self, stage: PipelineStage, output: Any) -> None:
        """Validate that stage output meets contract requirements"""
        # The Pydantic models handle validation automatically
        # This is where we'd add additional business logic validation
        pass
    
    def _calculate_confidence(self, stage_outputs: Dict[PipelineStage, Any]) -> float:
        """Calculate overall pipeline confidence"""
        confidences = []
        weights = {
            PipelineStage.PAGE_CLASSIFICATION: 0.15,
            PipelineStage.SCALE_DETECTION: 0.20,
            PipelineStage.GEOMETRY_EXTRACTION: 0.25,
            PipelineStage.SEMANTIC_ANALYSIS: 0.30,
            PipelineStage.LOAD_CALCULATION: 0.10
        }
        
        for stage, output in stage_outputs.items():
            if hasattr(output, 'confidence'):
                confidences.append(output.confidence * weights.get(stage, 0.2))
        
        return sum(confidences) / sum(weights.values()) if confidences else 0.5
    
    def _get_stage_output(self, stage: PipelineStage) -> Any:
        """Get output from a previous stage (for context)"""
        # This would be implemented to retrieve from stage_outputs
        # For now, returning None as placeholder
        return None


# Global instance
pipeline_orchestrator = PipelineOrchestrator()