#!/usr/bin/env python3
"""
Blueprint Service Layer for AutoHVAC
Handles business logic, file management, and processing orchestration
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
import shutil
import uuid
from dataclasses import asdict

from ..core.blueprint_processor import get_processor
from ..core.data_models import ExtractionResult, ProcessingStatus
from ..professional_output_generator import ProfessionalOutputGenerator

logger = logging.getLogger(__name__)

class BlueprintService:
    """
    Service layer for blueprint processing with job management,
    file handling, and result caching
    """
    
    def __init__(self, 
                 upload_dir: str = "uploads",
                 processed_dir: str = "processed", 
                 outputs_dir: str = "outputs",
                 cache_ttl_hours: int = 24):
        
        # Directory setup
        self.upload_dir = Path(upload_dir)
        self.processed_dir = Path(processed_dir)
        self.outputs_dir = Path(outputs_dir)
        
        # Create directories if they don't exist
        for directory in [self.upload_dir, self.processed_dir, self.outputs_dir]:
            directory.mkdir(exist_ok=True)
        
        # Configuration
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # Initialize processor and output generator
        self.processor = get_processor()
        self.output_generator = ProfessionalOutputGenerator()
        
        # In-memory job tracking
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.completed_jobs: Dict[str, ExtractionResult] = {}
        
        logger.info(f"BlueprintService initialized with cache TTL: {cache_ttl_hours}h")
    
    async def upload_and_process_blueprint(self, 
                                          file_content: bytes,
                                          filename: str,
                                          project_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle file upload and initiate processing
        """
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        try:
            # Validate file
            self._validate_file(filename, file_content)
            
            # Save uploaded file
            file_path = await self._save_uploaded_file(file_content, filename, job_id)
            
            # Track job
            self.active_jobs[job_id] = {
                'status': ProcessingStatus.PENDING,
                'filename': filename,
                'file_path': str(file_path),
                'project_info': project_info or {},
                'created_at': datetime.now(),
                'progress': 0
            }
            
            # Start background processing
            asyncio.create_task(self._process_blueprint_background(job_id, file_path, project_info))
            
            return {
                'job_id': job_id,
                'status': 'uploaded',
                'message': 'File uploaded successfully, processing started',
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"Upload failed for {filename}: {str(e)}")
            raise ValueError(f"File upload failed: {str(e)}")
    
    async def get_processing_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current processing status for a job
        """
        # Check completed jobs first
        if job_id in self.completed_jobs:
            result = self.completed_jobs[job_id]
            return {
                'job_id': job_id,
                'status': result.status.value,
                'progress': 100,
                'confidence': result.overall_confidence,
                'message': 'Processing completed successfully',
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'error': result.error_message
            }
        
        # Check active jobs
        if job_id in self.active_jobs:
            job_info = self.active_jobs[job_id]
            return {
                'job_id': job_id,
                'status': job_info['status'].value if isinstance(job_info['status'], ProcessingStatus) else job_info['status'],
                'progress': job_info.get('progress', 0),
                'message': job_info.get('message', 'Processing in progress'),
                'created_at': job_info['created_at'].isoformat()
            }
        
        # Check for cached results on disk
        cached_result = await self._load_cached_result(job_id)
        if cached_result:
            return {
                'job_id': job_id,
                'status': cached_result.status.value,
                'progress': 100,
                'confidence': cached_result.overall_confidence,
                'message': 'Retrieved from cache',
                'completed_at': cached_result.completed_at.isoformat() if cached_result.completed_at else None
            }
        
        return {
            'job_id': job_id,
            'status': 'not_found',
            'message': 'Job not found or expired'
        }
    
    async def get_extraction_results(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed extraction results for a completed job
        """
        # Check in-memory cache first
        if job_id in self.completed_jobs:
            result = self.completed_jobs[job_id]
            return result.to_dict()
        
        # Check disk cache
        cached_result = await self._load_cached_result(job_id)
        if cached_result:
            return cached_result.to_dict()
        
        raise ValueError(f"Results not found for job {job_id}")
    
    async def get_professional_analysis(self, job_id: str) -> Dict[str, Any]:
        """
        Get professional analysis results including Manual J calculations
        """
        # Get extraction results first
        extraction_data = await self.get_extraction_results(job_id)
        
        # Check if professional analysis already exists
        analysis_file = self.outputs_dir / job_id / "professional_analysis.json"
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                return json.load(f)
        
        # Generate professional analysis
        result = ExtractionResult.from_dict(extraction_data)
        analysis = await self._generate_professional_analysis(result)
        
        # Cache the analysis
        await self._cache_professional_analysis(job_id, analysis)
        
        return analysis
    
    async def list_job_outputs(self, job_id: str) -> List[Dict[str, Any]]:
        """
        List all available output files for a job
        """
        job_output_dir = self.outputs_dir / job_id
        
        if not job_output_dir.exists():
            return []
        
        outputs = []
        for file_path in job_output_dir.iterdir():
            if file_path.is_file():
                outputs.append({
                    'filename': file_path.name,
                    'file_type': file_path.suffix.lower(),
                    'size_bytes': file_path.stat().st_size,
                    'created_at': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    'download_url': f"/api/blueprint/download/{job_id}/{file_path.name}"
                })
        
        return outputs
    
    async def get_output_file(self, job_id: str, filename: str) -> Path:
        """
        Get path to a specific output file
        """
        file_path = self.outputs_dir / job_id / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Output file not found: {filename}")
        
        return file_path
    
    async def cleanup_expired_jobs(self, max_age_hours: int = 168):  # 7 days default
        """
        Clean up old job files and data
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        # Clean up active jobs
        expired_jobs = [
            job_id for job_id, job_info in self.active_jobs.items()
            if job_info['created_at'] < cutoff_time
        ]
        
        for job_id in expired_jobs:
            del self.active_jobs[job_id]
            cleaned_count += 1
        
        # Clean up completed jobs
        expired_completed = [
            job_id for job_id, result in self.completed_jobs.items()
            if result.created_at < cutoff_time
        ]
        
        for job_id in expired_completed:
            del self.completed_jobs[job_id]
            cleaned_count += 1
        
        # Clean up disk files
        for directory in [self.upload_dir, self.processed_dir, self.outputs_dir]:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                elif file_path.is_dir():
                    # Clean up empty job directories
                    try:
                        if not any(file_path.iterdir()):
                            file_path.rmdir()
                            cleaned_count += 1
                    except OSError:
                        pass
        
        logger.info(f"Cleaned up {cleaned_count} expired job artifacts")
        return cleaned_count
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service performance statistics
        """
        return {
            'active_jobs': len(self.active_jobs),
            'completed_jobs': len(self.completed_jobs),
            'processor_stats': self.processor.get_performance_stats(),
            'disk_usage': {
                'uploads_mb': self._get_directory_size(self.upload_dir) / 1024 / 1024,
                'processed_mb': self._get_directory_size(self.processed_dir) / 1024 / 1024,
                'outputs_mb': self._get_directory_size(self.outputs_dir) / 1024 / 1024
            }
        }
    
    # Private methods
    
    def _validate_file(self, filename: str, content: bytes):
        """
        Validate uploaded file
        """
        # Check file extension
        allowed_extensions = {'.pdf'}
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024
        if len(content) > max_size:
            raise ValueError(f"File too large: {len(content)} bytes (max: {max_size})")
        
        # Basic PDF validation
        if not content.startswith(b'%PDF'):
            raise ValueError("Invalid PDF file")
    
    async def _save_uploaded_file(self, content: bytes, filename: str, job_id: str) -> Path:
        """
        Save uploaded file to disk
        """
        file_ext = Path(filename).suffix
        file_path = self.upload_dir / f"{job_id}{file_ext}"
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        return file_path
    
    async def _process_blueprint_background(self, job_id: str, file_path: Path, project_info: Dict):
        """
        Background task for blueprint processing
        """
        try:
            # Update job status
            self.active_jobs[job_id]['status'] = ProcessingStatus.PROCESSING
            self.active_jobs[job_id]['progress'] = 10
            
            # Process the blueprint
            result = await self.processor.process_blueprint_async(
                file_path, job_id, project_info
            )
            
            # Update progress
            self.active_jobs[job_id]['progress'] = 70
            
            # Generate professional outputs
            if result.status == ProcessingStatus.COMPLETED:
                await self._generate_professional_outputs(result)
                self.active_jobs[job_id]['progress'] = 90
            
            # Cache the result
            await self._cache_result(result)
            
            # Move to completed jobs
            self.completed_jobs[job_id] = result
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            logger.info(f"Blueprint processing completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Background processing failed for job {job_id}: {str(e)}", exc_info=True)
            
            # Update job with error status
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['status'] = ProcessingStatus.FAILED
                self.active_jobs[job_id]['error'] = str(e)
    
    async def _generate_professional_outputs(self, result: ExtractionResult):
        """
        Generate professional deliverables
        """
        try:
            # Create output directory
            output_dir = self.outputs_dir / result.job_id
            output_dir.mkdir(exist_ok=True)
            
            # Generate using the existing professional output generator
            analysis = self.output_generator.generate_complete_analysis(
                result.job_id,
                str(self.upload_dir / f"{result.job_id}.pdf")
            )
            
            # Save analysis as JSON
            analysis_file = output_dir / "professional_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Generated professional outputs for job {result.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate professional outputs: {str(e)}")
    
    async def _generate_professional_analysis(self, result: ExtractionResult) -> Dict[str, Any]:
        """
        Generate professional analysis from extraction result
        """
        # This would integrate with the existing professional_output_generator
        # For now, return a structured analysis
        return {
            'job_id': result.job_id,
            'status': 'completed',
            'confidence': result.overall_confidence,
            'extraction_summary': {
                'project_info': asdict(result.project_info),
                'building_characteristics': asdict(result.building_chars),
                'rooms': [asdict(room) for room in result.rooms],
                'insulation_specs': asdict(result.insulation)
            },
            'gaps_identified': asdict(result.gaps_identified),
            'recommendations': result.gaps_identified.recommendations,
            'processing_metrics': asdict(result.extraction_metrics),
            'generated_at': datetime.now().isoformat()
        }
    
    async def _cache_result(self, result: ExtractionResult):
        """
        Cache extraction result to disk
        """
        cache_file = self.processed_dir / f"{result.job_id}.json"
        
        with open(cache_file, 'w') as f:
            f.write(result.to_json())
        
        logger.debug(f"Cached result for job {result.job_id}")
    
    async def _cache_professional_analysis(self, job_id: str, analysis: Dict[str, Any]):
        """
        Cache professional analysis to disk
        """
        output_dir = self.outputs_dir / job_id
        output_dir.mkdir(exist_ok=True)
        
        analysis_file = output_dir / "professional_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
    
    async def _load_cached_result(self, job_id: str) -> Optional[ExtractionResult]:
        """
        Load cached result from disk
        """
        cache_file = self.processed_dir / f"{job_id}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if cache is still valid
        file_age = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_age > self.cache_ttl:
            cache_file.unlink()  # Remove expired cache
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return ExtractionResult.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load cached result: {str(e)}")
            return None
    
    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of directory
        """
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

# Global service instance
_global_service: Optional[BlueprintService] = None

def get_blueprint_service() -> BlueprintService:
    """Get global service instance (singleton)"""
    global _global_service
    if _global_service is None:
        _global_service = BlueprintService()
    return _global_service