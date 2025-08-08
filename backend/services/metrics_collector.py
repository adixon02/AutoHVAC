"""
Metrics Collector for HVAC Load Calculation Pipeline
Tracks performance, data quality, and calculation provenance
"""

import logging
import time
import json
import traceback
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import psutil
import os

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics we track"""
    TIMING = "timing"
    QUALITY = "quality"
    ERROR = "error"
    DATA = "data"
    DECISION = "decision"
    WARNING = "warning"


class PipelineStage(Enum):
    """Stages in the processing pipeline"""
    UPLOAD = "upload"
    PAGE_CLASSIFICATION = "page_classification"
    SCALE_DETECTION = "scale_detection"
    GEOMETRY_EXTRACTION = "geometry_extraction"
    ROOM_FILTERING = "room_filtering"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    ENVELOPE_DEFAULTS = "envelope_defaults"
    INFILTRATION_CALC = "infiltration_calculation"
    DUCT_LOSS_CALC = "duct_loss_calculation"
    LOAD_CALCULATION = "load_calculation"
    CONFIDENCE_SCORING = "confidence_scoring"
    REPORT_GENERATION = "report_generation"


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage"""
    stage: PipelineStage
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    
    # Data metrics
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    confidence: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    
    # Decisions made
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Resource usage
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None


@dataclass
class DataProvenance:
    """Track where data came from"""
    field: str
    value: Any
    source: str  # detected, default, inferred, user_provided
    confidence: float
    stage: PipelineStage
    timestamp: float
    notes: Optional[str] = None


@dataclass
class PipelineMetrics:
    """Complete metrics for entire pipeline run"""
    job_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    
    # Stage metrics
    stages: List[StageMetrics] = field(default_factory=list)
    
    # Data provenance
    provenance: List[DataProvenance] = field(default_factory=list)
    
    # Overall metrics
    success: bool = False
    error_stage: Optional[PipelineStage] = None
    error_message: Optional[str] = None
    
    # Quality metrics
    overall_confidence: Optional[float] = None
    quality_score: Optional[float] = None
    data_completeness: Optional[float] = None
    
    # Key results
    total_area_sqft: Optional[float] = None
    num_rooms: Optional[int] = None
    heating_load_btu: Optional[float] = None
    cooling_load_btu: Optional[float] = None
    heating_tons: Optional[float] = None
    cooling_tons: Optional[float] = None
    
    # Warnings and issues
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    data_gaps: List[str] = field(default_factory=list)
    
    # Resource usage
    peak_memory_mb: Optional[float] = None
    total_cpu_seconds: Optional[float] = None
    
    # File info
    pdf_filename: Optional[str] = None
    pdf_size_mb: Optional[float] = None
    num_pages: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects
        data['start_time'] = self.start_time.isoformat() if self.start_time else None
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data


class MetricsCollector:
    """
    Collects and aggregates metrics throughout the pipeline.
    Provides observability into calculation process and decision-making.
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self.current_metrics: Optional[PipelineMetrics] = None
        self.current_stage: Optional[StageMetrics] = None
        self.process = psutil.Process()
        
    def start_pipeline(
        self,
        job_id: str,
        pdf_filename: str,
        pdf_size_mb: float,
        num_pages: int
    ) -> PipelineMetrics:
        """Start tracking a new pipeline run"""
        logger.info(f"Starting metrics collection for job {job_id}")
        
        self.current_metrics = PipelineMetrics(
            job_id=job_id,
            start_time=datetime.now(),
            pdf_filename=pdf_filename,
            pdf_size_mb=pdf_size_mb,
            num_pages=num_pages
        )
        
        return self.current_metrics
    
    def start_stage(
        self,
        stage: PipelineStage,
        input_data: Optional[Dict[str, Any]] = None
    ) -> StageMetrics:
        """Start tracking a pipeline stage"""
        logger.debug(f"Starting stage: {stage.value}")
        
        if not self.current_metrics:
            raise ValueError("No pipeline started - call start_pipeline first")
        
        # End previous stage if still running
        if self.current_stage and self.current_stage.end_time is None:
            self.end_stage(success=False, error="Stage interrupted")
        
        # Start new stage
        self.current_stage = StageMetrics(
            stage=stage,
            start_time=time.time(),
            input_data=input_data or {},
            memory_mb=self.process.memory_info().rss / 1024 / 1024
        )
        
        self.current_metrics.stages.append(self.current_stage)
        return self.current_stage
    
    def end_stage(
        self,
        success: bool = True,
        output_data: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """End tracking current stage"""
        if not self.current_stage:
            logger.warning("No stage to end")
            return
        
        self.current_stage.end_time = time.time()
        self.current_stage.duration_ms = (
            (self.current_stage.end_time - self.current_stage.start_time) * 1000
        )
        self.current_stage.success = success
        self.current_stage.output_data = output_data or {}
        self.current_stage.confidence = confidence
        self.current_stage.error = error
        
        # Capture resource usage
        self.current_stage.memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.current_stage.cpu_percent = self.process.cpu_percent()
        
        stage_name = self.current_stage.stage.value
        duration = self.current_stage.duration_ms
        
        if success:
            logger.info(f"Stage {stage_name} completed in {duration:.0f}ms")
        else:
            logger.error(f"Stage {stage_name} failed after {duration:.0f}ms: {error}")
            self.current_metrics.error_stage = self.current_stage.stage
            self.current_metrics.error_message = error
    
    def track_decision(
        self,
        decision_type: str,
        description: str,
        chosen_value: Any,
        alternatives: Optional[List[Any]] = None,
        reason: Optional[str] = None
    ) -> None:
        """Track a decision made during processing"""
        if not self.current_stage:
            logger.warning("No active stage to track decision")
            return
        
        decision = {
            "type": decision_type,
            "description": description,
            "chosen": chosen_value,
            "alternatives": alternatives or [],
            "reason": reason,
            "timestamp": time.time()
        }
        
        self.current_stage.decisions.append(decision)
        logger.debug(f"Decision tracked: {decision_type} = {chosen_value}")
    
    def track_provenance(
        self,
        field: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
        notes: Optional[str] = None
    ) -> None:
        """Track data provenance"""
        if not self.current_metrics or not self.current_stage:
            return
        
        provenance = DataProvenance(
            field=field,
            value=value,
            source=source,
            confidence=confidence,
            stage=self.current_stage.stage,
            timestamp=time.time(),
            notes=notes
        )
        
        self.current_metrics.provenance.append(provenance)
        logger.debug(f"Provenance: {field} = {value} (source: {source}, conf: {confidence:.2f})")
    
    def add_warning(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a warning to current stage and pipeline"""
        if not self.current_stage:
            return
        
        warning_msg = f"{category}: {message}"
        self.current_stage.warnings.append(warning_msg)
        
        if self.current_metrics:
            self.current_metrics.warnings.append({
                "stage": self.current_stage.stage.value,
                "category": category,
                "message": message,
                "details": details or {},
                "timestamp": time.time()
            })
        
        logger.warning(warning_msg)
    
    def end_pipeline(
        self,
        success: bool = True,
        results: Optional[Dict[str, Any]] = None
    ) -> PipelineMetrics:
        """End pipeline tracking and finalize metrics"""
        if not self.current_metrics:
            raise ValueError("No pipeline to end")
        
        # End current stage if still running
        if self.current_stage and self.current_stage.end_time is None:
            self.end_stage(success=False, error="Pipeline ended")
        
        self.current_metrics.end_time = datetime.now()
        self.current_metrics.total_duration_ms = (
            (self.current_metrics.end_time - self.current_metrics.start_time).total_seconds() * 1000
        )
        self.current_metrics.success = success
        
        # Extract key results if provided
        if results:
            self.current_metrics.total_area_sqft = results.get("total_area")
            self.current_metrics.num_rooms = results.get("num_rooms")
            self.current_metrics.heating_load_btu = results.get("heating_load")
            self.current_metrics.cooling_load_btu = results.get("cooling_load")
            self.current_metrics.heating_tons = results.get("heating_tons")
            self.current_metrics.cooling_tons = results.get("cooling_tons")
            self.current_metrics.overall_confidence = results.get("confidence")
            self.current_metrics.quality_score = results.get("quality_score")
        
        # Calculate aggregate metrics
        self._calculate_aggregates()
        
        # Log summary
        self._log_summary()
        
        return self.current_metrics
    
    def _calculate_aggregates(self) -> None:
        """Calculate aggregate metrics across all stages"""
        if not self.current_metrics:
            return
        
        # Peak memory usage
        peak_memory = 0
        total_cpu = 0
        
        for stage in self.current_metrics.stages:
            if stage.memory_mb:
                peak_memory = max(peak_memory, stage.memory_mb)
            if stage.cpu_percent and stage.duration_ms:
                total_cpu += (stage.cpu_percent * stage.duration_ms / 1000)
        
        self.current_metrics.peak_memory_mb = peak_memory
        self.current_metrics.total_cpu_seconds = total_cpu / 100  # Convert from percent
        
        # Data completeness
        detected_count = sum(
            1 for p in self.current_metrics.provenance
            if p.source == "detected"
        )
        total_count = len(self.current_metrics.provenance)
        
        if total_count > 0:
            self.current_metrics.data_completeness = detected_count / total_count
        
        # Identify data gaps
        gaps = set()
        for p in self.current_metrics.provenance:
            if p.source in ["default", "inferred"] and p.confidence < 0.7:
                gaps.add(f"{p.field} ({p.source})")
        
        self.current_metrics.data_gaps = list(gaps)
    
    def _log_summary(self) -> None:
        """Log pipeline execution summary"""
        if not self.current_metrics:
            return
        
        m = self.current_metrics
        logger.info("=" * 70)
        logger.info(f"PIPELINE METRICS SUMMARY - Job: {m.job_id}")
        logger.info("=" * 70)
        
        # Timing
        logger.info(f"Total Duration: {m.total_duration_ms:.0f}ms")
        logger.info("Stage Breakdown:")
        for stage in m.stages:
            status = "✓" if stage.success else "✗"
            conf = f" (conf: {stage.confidence:.1%})" if stage.confidence else ""
            logger.info(f"  {status} {stage.stage.value:25s} {stage.duration_ms:6.0f}ms{conf}")
        
        # Results
        if m.success:
            logger.info(f"\nResults:")
            if m.total_area_sqft:
                logger.info(f"  Area: {m.total_area_sqft:.0f} sqft")
            if m.num_rooms:
                logger.info(f"  Rooms: {m.num_rooms}")
            if m.heating_load_btu:
                logger.info(f"  Heating: {m.heating_load_btu:.0f} BTU/hr ({m.heating_tons:.1f} tons)")
            if m.cooling_load_btu:
                logger.info(f"  Cooling: {m.cooling_load_btu:.0f} BTU/hr ({m.cooling_tons:.1f} tons)")
            if m.overall_confidence:
                logger.info(f"  Confidence: {m.overall_confidence:.1%}")
        else:
            logger.error(f"\nPipeline Failed at: {m.error_stage.value if m.error_stage else 'unknown'}")
            logger.error(f"Error: {m.error_message}")
        
        # Warnings
        if m.warnings:
            logger.warning(f"\nWarnings ({len(m.warnings)}):")
            for w in m.warnings[:5]:  # Show first 5
                logger.warning(f"  - {w['category']}: {w['message']}")
        
        # Data gaps
        if m.data_gaps:
            logger.info(f"\nData Gaps ({len(m.data_gaps)}):")
            for gap in m.data_gaps[:5]:
                logger.info(f"  - {gap}")
        
        # Resources
        logger.info(f"\nResource Usage:")
        logger.info(f"  Peak Memory: {m.peak_memory_mb:.0f} MB")
        logger.info(f"  CPU Time: {m.total_cpu_seconds:.1f} seconds")
        
        logger.info("=" * 70)
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        """Export metrics to JSON file"""
        if not self.current_metrics:
            raise ValueError("No metrics to export")
        
        if not filepath:
            filepath = f"metrics_{self.current_metrics.job_id}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.current_metrics.to_dict(), f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {filepath}")
        return filepath
    
    def get_stage_summary(self, stage: PipelineStage) -> Optional[Dict[str, Any]]:
        """Get summary for a specific stage"""
        if not self.current_metrics:
            return None
        
        for s in self.current_metrics.stages:
            if s.stage == stage:
                return {
                    "success": s.success,
                    "duration_ms": s.duration_ms,
                    "confidence": s.confidence,
                    "warnings": s.warnings,
                    "decisions": len(s.decisions),
                    "error": s.error
                }
        
        return None
    
    @staticmethod
    def format_duration(ms: float) -> str:
        """Format duration in human-readable format"""
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.1f}s"
        else:
            return f"{ms/60000:.1f}min"


# Global singleton instance
metrics_collector = MetricsCollector()


# Context manager for stage tracking
class track_stage:
    """Context manager for automatic stage tracking"""
    
    def __init__(
        self,
        stage: PipelineStage,
        collector: Optional[MetricsCollector] = None,
        input_data: Optional[Dict[str, Any]] = None
    ):
        self.stage = stage
        self.collector = collector or metrics_collector
        self.input_data = input_data
        self.stage_metrics = None
        
    def __enter__(self):
        self.stage_metrics = self.collector.start_stage(self.stage, self.input_data)
        return self.stage_metrics
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            self.collector.end_stage(success=True)
        else:
            # Error occurred
            error_msg = f"{exc_type.__name__}: {exc_val}"
            self.collector.end_stage(success=False, error=error_msg)
            # Re-raise the exception
            return False