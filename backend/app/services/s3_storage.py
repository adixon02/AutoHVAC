"""
S3 Storage Service for AutoHVAC V3
Enhanced data collection for the V3 pipeline
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)

class S3StorageService:
    """
    AWS S3-based storage service for AutoHVAC V3
    Captures comprehensive data for training and analytics
    """
    
    def __init__(self):
        # Get AWS configuration from environment
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
        self.bucket_name = os.getenv("S3_BUCKET", "autohvac-uploads")
        
        # Skip initialization if no AWS credentials (for local dev)
        if not all([self.aws_access_key_id, self.aws_secret_access_key]):
            logger.warning("AWS credentials not configured. S3 storage disabled.")
            self.enabled = False
            return
        
        self.enabled = True
        
        # Configure boto3 with retry logic
        config = Config(
            region_name=self.aws_region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=50
        )
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=config
        )
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Verify bucket exists
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ S3 connected to bucket: {self.bucket_name}")
        except ClientError as e:
            logger.error(f"❌ S3 bucket access failed: {e}")
            self.enabled = False
    
    async def save_upload(self, job_id: str, content: bytes, filename: str) -> str:
        """
        Save uploaded blueprint to S3
        
        Args:
            job_id: Unique job identifier  
            content: File content as bytes
            filename: Original filename
            
        Returns:
            str: S3 key of the uploaded file
        """
        if not self.enabled:
            logger.warning("S3 storage disabled - skipping upload save")
            return ""
        
        s3_key = f"jobs/{job_id}/blueprint.pdf"
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType='application/pdf',
                    Metadata={
                        'job_id': job_id,
                        'original_filename': filename,
                        'upload_type': 'blueprint',
                        'pipeline_version': 'v3'
                    }
                )
            )
            
            logger.info(f"📄 Saved blueprint: jobs/{job_id}/blueprint.pdf ({len(content)} bytes)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save blueprint for job {job_id}: {e}")
            return ""
    
    def save_json(self, job_id: str, filename: str, data: Dict[str, Any]) -> str:
        """
        Save JSON data to S3 in the job folder
        
        Args:
            job_id: Job identifier
            filename: JSON filename (e.g., 'v3_results.json', 'metadata.json')
            data: Dictionary to save as JSON
            
        Returns:
            str: S3 key of the saved file
        """
        if not self.enabled:
            logger.warning(f"S3 storage disabled - skipping JSON save: {filename}")
            return ""
        
        s3_key = f"jobs/{job_id}/{filename}"
        
        try:
            # Convert data to JSON string with proper formatting
            json_content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'job_id': job_id,
                    'file_type': 'json',
                    'data_type': filename.replace('.json', ''),
                    'pipeline_version': 'v3'
                }
            )
            logger.info(f"💾 Saved data: jobs/{job_id}/{filename} ({len(json_content)} chars)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save JSON {filename} for job {job_id}: {e}")
            return ""
    
    async def save_complete_job_data(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """
        Save comprehensive job data for V3 pipeline with enhanced training data collection
        
        Args:
            job_id: Job identifier
            job_data: Complete job data from the V3 pipeline
        """
        if not self.enabled:
            return
        
        try:
            # 1. V3 Results - The complete pipeline output
            if "result" in job_data and job_data["result"]:
                v3_results = {
                    "job_id": job_id,
                    "pipeline_version": "v3",
                    "status": job_data.get("status"),
                    "processing_time": job_data["result"].get("processing_time_seconds"),
                    "hvac_calculations": {
                        "heating_load_btu_hr": job_data["result"].get("heating_load_btu_hr"),
                        "cooling_load_btu_hr": job_data["result"].get("cooling_load_btu_hr"),
                        "heating_tons": job_data["result"].get("heating_tons"),
                        "cooling_tons": job_data["result"].get("cooling_tons"),
                        "zones": job_data["result"].get("zones"),
                        "spaces": job_data["result"].get("spaces"),
                        "zone_loads": job_data["result"].get("zone_loads", {}),
                        "confidence": job_data["result"].get("confidence", 0.0),
                        "warnings": job_data["result"].get("warnings", [])
                    },
                    "building_analysis": {
                        "garage_detected": job_data["result"].get("garage_detected", False),
                        "bonus_over_garage": job_data["result"].get("bonus_over_garage", False),
                        "zones_created": job_data["result"].get("zones_created", 0),
                        "spaces_detected": job_data["result"].get("spaces_detected", 0)
                    },
                    "quality_metrics": {
                        "confidence_score": job_data["result"].get("confidence_score", 0.0),
                        "processing_time_seconds": job_data["result"].get("processing_time_seconds", 0)
                    }
                }
                self.save_json(job_id, "v3_results.json", v3_results)
                
                # Enhanced V3 Data Collection - Additional valuable datasets
                result = job_data["result"]
                
                # 2. AI Training Data - Vision processing and construction analysis
                if result.get("vision_processing") or result.get("ai_analysis") or result.get("construction_context"):
                    ai_data = {
                        "job_id": job_id,
                        "vision_processing": result.get("vision_processing", {}),
                        "ai_analysis": result.get("ai_analysis", {}),
                        "construction_context": result.get("construction_context", {}),
                        "ai_confidence": result.get("ai_confidence", 0.0),
                        "page_classifications": result.get("page_classifications", []),
                        "api_usage": {
                            "tokens_used": result.get("tokens_used", 0),
                            "api_calls": result.get("api_calls", 0),
                            "processing_time_ai": result.get("processing_time_ai", 0)
                        }
                    }
                    self.save_json(job_id, "ai_training_data.json", ai_data)
                
                # 3. Scale Analytics - Scale detection performance
                if result.get("scale_data") or result.get("scale_detection") or result.get("scale_px_per_ft"):
                    scale_data = {
                        "job_id": job_id,
                        "scale_detection": result.get("scale_detection", {}),
                        "scale_px_per_ft": result.get("scale_px_per_ft"),
                        "scale_confidence": result.get("scale_confidence", 0.0),
                        "scale_method": result.get("scale_method", "unknown"),
                        "scale_text_found": result.get("scale_text_found", []),
                        "scale_visual_found": result.get("scale_visual_found", False),
                        "drawing_dimensions": result.get("drawing_dimensions", {})
                    }
                    self.save_json(job_id, "scale_analytics.json", scale_data)
                
                # 4. Space Analytics - Room/space detection results
                space_data = {
                    "job_id": job_id,
                    "spaces_detected": result.get("spaces_detected", 0),
                    "rooms_data": result.get("rooms_data", {}),
                    "vector_extraction": result.get("vector_extraction", {}),
                    "foundation_data": result.get("foundation_data", {}),
                    "fenestration_data": result.get("fenestration_data", {}),
                    "mechanical_data": result.get("mechanical_data", {}),
                    "room_detection_method": result.get("room_detection_method", "unknown"),
                    "area_calculations": result.get("area_calculations", {}),
                    "polygon_detection": result.get("polygon_detection", {}),
                    "building_footprint": result.get("building_footprint", {})
                }
                self.save_json(job_id, "space_analytics.json", space_data)
                
                # 5. Energy Training Data - Building energy specifications
                if result.get("energy_specs") or result.get("r_values") or result.get("insulation_data"):
                    energy_data = {
                        "job_id": job_id,
                        "energy_specs": result.get("energy_specs", {}),
                        "r_values": result.get("r_values", {}),
                        "window_specs": result.get("window_specs", {}),
                        "insulation_data": result.get("insulation_data", {}),
                        "envelope_specs": result.get("envelope_specs", {}),
                        "extraction_confidence": result.get("energy_extraction_confidence", 0.0),
                        "extraction_source": result.get("energy_extraction_source", "unknown"),
                        "ai_vs_manual": result.get("ai_vs_manual_detection", {}),
                        "construction_quality": result.get("construction_quality", "unknown")
                    }
                    self.save_json(job_id, "energy_training_data.json", energy_data)
                
                # 6. Performance Metrics - Pipeline performance data
                performance_data = {
                    "job_id": job_id,
                    "processing_stages": result.get("processing_stages", {}),
                    "stage_timings": result.get("stage_timings", {}),
                    "success_rates": result.get("success_rates", {}),
                    "warning_patterns": result.get("warnings", []),
                    "load_magnitudes": {
                        "heating_load_btu_hr": result.get("heating_load_btu_hr"),
                        "cooling_load_btu_hr": result.get("cooling_load_btu_hr"),
                        "heating_per_sqft": result.get("heating_per_sqft"),
                        "cooling_per_sqft": result.get("cooling_per_sqft"),
                        "total_conditioned_area_sqft": result.get("total_conditioned_area_sqft")
                    },
                    "calculation_components": {
                        "heating_components": result.get("heating_components", {}),
                        "cooling_components": result.get("cooling_components", {}),
                        "infiltration_data": result.get("infiltration_data", {}),
                        "envelope_loads": result.get("envelope_loads", {})
                    },
                    "total_processing_time": result.get("processing_time_seconds", 0),
                    "pipeline_version": "v3",
                    "accuracy_indicators": {
                        "confidence_score": result.get("confidence_score", 0.0),
                        "validation_results": result.get("validation_results", {}),
                        "quality_checks": result.get("quality_checks", {})
                    }
                }
                self.save_json(job_id, "performance_metrics.json", performance_data)
            
            # 7. Job Metadata - Important for business analytics
            metadata = {
                "job_id": job_id,
                "pipeline_version": "v3",
                "created_at": job_data.get("created_at"),
                "completed_at": job_data.get("completed_at"),
                "status": job_data.get("status"),
                "progress": job_data.get("progress", 0),
                "user_email": job_data.get("email"),
                "zip_code": job_data.get("zip_code"),
                "filename": job_data.get("filename"),
                "error": job_data.get("error"),
                "pipeline_improvements": {
                    "paywall_enforced": True,
                    "user_tracking": True,
                    "data_collection": True
                }
            }
            self.save_json(job_id, "metadata.json", metadata)
            
            # 3. Business Intelligence Data - For growth analytics
            if job_data.get("email"):
                bi_data = {
                    "user_email_hash": hash(job_data["email"]) % 1000000,  # Privacy-safe hash
                    "zip_code": job_data.get("zip_code"),
                    "processing_successful": job_data.get("status") == "completed",
                    "hvac_load_range": self._categorize_hvac_load(job_data.get("result", {})),
                    "building_type": self._infer_building_type(job_data.get("result", {})),
                    "market_segment": self._get_market_segment(job_data.get("zip_code")),
                    "pipeline_version": "v3"
                }
                self.save_json(job_id, "business_intelligence.json", bi_data)
            
            # 4. Enhanced V3 Data Collection - AI Training & Analytics
            await self._save_enhanced_v3_data(job_id, job_data)
            
            logger.info(f"📊 Saved complete data set for job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to save complete job data for {job_id}: {e}")
    
    async def _save_enhanced_v3_data(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """
        Save enhanced V3 pipeline data for training, analytics, and debugging
        This captures the rich intermediate results from the V3 pipeline
        """
        try:
            result = job_data.get("result", {})
            
            # Extract raw extractions if available (from pipeline_v3 result)
            raw_extractions = result.get("raw_extractions", {})
            
            # 4A. AI Training Data - Vision processing results
            if raw_extractions.get("vision"):
                ai_training_data = {
                    "job_id": job_id,
                    "construction_context": raw_extractions.get("construction_context", {}),
                    "thermal_intelligence": raw_extractions.get("vision", {}).get("thermal_intelligence", {}),
                    "construction_specs": raw_extractions.get("vision", {}).get("construction_specs", []),
                    "ai_confidence": raw_extractions.get("vision", {}).get("confidence", 0.0),
                    "vision_processing_time": raw_extractions.get("vision", {}).get("processing_time", 0),
                    "openai_model_used": raw_extractions.get("vision", {}).get("model", "gpt-4o"),
                    "prompt_tokens": raw_extractions.get("vision", {}).get("prompt_tokens", 0),
                    "completion_tokens": raw_extractions.get("vision", {}).get("completion_tokens", 0)
                }
                self.save_json(job_id, "ai_training_data.json", ai_training_data)
                logger.info(f"📊 Saved AI training data: {ai_training_data['ai_confidence']:.1%} confidence")
            
            # 4B. Scale Detection Analytics
            if raw_extractions.get("scale"):
                scale_analytics = {
                    "job_id": job_id,
                    "scale_detection": raw_extractions["scale"],
                    "scale_success": raw_extractions["scale"].get("scale_found", False),
                    "scale_method": raw_extractions["scale"].get("method", "unknown"),
                    "scale_confidence": raw_extractions["scale"].get("confidence", 0.0),
                    "scale_px_per_ft": raw_extractions["scale"].get("scale_px_per_ft", 0)
                }
                self.save_json(job_id, "scale_analytics.json", scale_analytics)
            
            # 4C. Room Detection & Space Analytics
            if raw_extractions.get("spaces"):
                space_analytics = {
                    "job_id": job_id,
                    "spaces_detected": raw_extractions["spaces"].get("count", 0),
                    "total_area_detected": raw_extractions["spaces"].get("total_area", 0),
                    "detection_confidence": raw_extractions["spaces"].get("confidence", 0.0),
                    "space_detection_method": "vector_extraction",
                    "garage_data": raw_extractions.get("garage", {}),
                    "foundation_data": raw_extractions.get("foundation", {}),
                    "fenestration_data": raw_extractions.get("fenestration", {}),
                    "mechanical_data": raw_extractions.get("mechanical", {})
                }
                self.save_json(job_id, "space_analytics.json", space_analytics)
            
            # 4D. Energy Specifications Training Data
            if raw_extractions.get("energy_specs"):
                energy_training_data = {
                    "job_id": job_id,
                    "energy_specs": raw_extractions["energy_specs"],
                    "extraction_source": raw_extractions["energy_specs"].get("extraction_source", "none"),
                    "specs_confidence": raw_extractions["energy_specs"].get("confidence", 0.0),
                    "r_values_found": {
                        "wall": raw_extractions["energy_specs"].get("wall_r_value"),
                        "ceiling": raw_extractions["energy_specs"].get("ceiling_r_value"),
                        "floor": raw_extractions["energy_specs"].get("floor_r_value")
                    },
                    "window_specs": {
                        "u_factor": raw_extractions["energy_specs"].get("window_u_factor"),
                        "shgc": raw_extractions["energy_specs"].get("window_shgc")
                    }
                }
                self.save_json(job_id, "energy_training_data.json", energy_training_data)
            
            # 4E. Performance Metrics
            performance_metrics = {
                "job_id": job_id,
                "total_processing_time": result.get("processing_time_seconds", 0),
                "success": job_data.get("status") == "completed",
                "warning_count": len(result.get("warnings", [])),
                "confidence_final": result.get("confidence_score", 0.0),
                "zones_created": result.get("zones_created", 0),
                "spaces_detected": result.get("spaces_detected", 0),
                "hvac_load_magnitude": {
                    "heating_btu_hr": result.get("heating_load_btu_hr", 0),
                    "cooling_btu_hr": result.get("cooling_load_btu_hr", 0),
                    "heating_per_sqft": result.get("heating_per_sqft", 0),
                    "cooling_per_sqft": result.get("cooling_per_sqft", 0)
                },
                "pipeline_version": "v3",
                "timestamp": job_data.get("created_at")
            }
            self.save_json(job_id, "performance_metrics.json", performance_metrics)
            
            logger.info(f"📊 Enhanced V3 data saved: {len(raw_extractions)} extraction categories")
            
        except Exception as e:
            logger.error(f"Failed to save enhanced V3 data for {job_id}: {e}")
            # Don't fail the main job if enhanced data collection fails
    
    def _categorize_hvac_load(self, result: Dict[str, Any]) -> str:
        """Categorize HVAC load for market analysis"""
        heating_load = result.get("heating_load_btu_hr", 0)
        if heating_load < 30000:
            return "small_residential"
        elif heating_load < 80000:
            return "medium_residential"  
        elif heating_load < 150000:
            return "large_residential"
        else:
            return "commercial_small"
    
    def _infer_building_type(self, result: Dict[str, Any]) -> str:
        """Infer building type from analysis results"""
        if result.get("garage_detected"):
            if result.get("bonus_over_garage"):
                return "multi_story_with_bonus"
            return "single_family_with_garage"
        elif result.get("zones", 0) > 2:
            return "multi_zone_residential"
        else:
            return "basic_residential"
    
    def _get_market_segment(self, zip_code: str) -> str:
        """Basic market segmentation by zip code region"""
        if not zip_code:
            return "unknown"
        
        first_digit = zip_code[0] if zip_code else "0"
        region_map = {
            "0": "northeast", "1": "northeast", "2": "mid_atlantic",
            "3": "southeast", "4": "southeast", "5": "midwest", 
            "6": "south_central", "7": "south_central", 
            "8": "mountain", "9": "pacific"
        }
        return region_map.get(first_digit, "unknown")

# Singleton instance
try:
    storage_service = S3StorageService()
except Exception as e:
    logger.error(f"Failed to initialize S3 storage service: {e}")
    # Create a disabled instance
    class DisabledS3Service:
        enabled = False
        async def save_upload(self, *args, **kwargs): return ""
        def save_json(self, *args, **kwargs): return ""
        async def save_complete_job_data(self, *args, **kwargs): pass
    
    storage_service = DisabledS3Service()