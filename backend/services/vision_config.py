"""
Vision Model Configuration - GPT-5 and fallback settings
Centralized configuration for vision models and API parameters
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for a specific vision model"""
    name: str
    max_tokens: int
    supports_temperature: bool = True
    default_temperature: float = 1.0
    supports_reasoning_effort: bool = False
    supports_verbosity: bool = False
    image_detail: str = "high"
    timeout_seconds: int = 300  # 5 minutes default
    
    def get_api_params(self) -> Dict[str, Any]:
        """Get API parameters for this model"""
        params = {
            "model": self.name,
            "max_completion_tokens": self.max_tokens,
        }
        
        # Only add temperature if supported and not default
        if self.supports_temperature and self.default_temperature != 1.0:
            params["temperature"] = self.default_temperature
        
        return params
    
    def get_extra_body(self) -> Optional[Dict[str, Any]]:
        """Get extra body parameters for advanced models"""
        extra = {}
        
        if self.supports_reasoning_effort:
            extra["reasoning_effort"] = "high"  # For complex blueprint analysis
        
        if self.supports_verbosity:
            extra["verbosity"] = "low"  # We want concise JSON output
        
        return extra if extra else None


@dataclass
class VisionConfig:
    """Central configuration for vision processing"""
    
    # API configuration
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # Model hierarchy (in order of preference)
    models: List[ModelConfig] = field(default_factory=lambda: [
        ModelConfig(
            name="gpt-5",
            max_tokens=16384,
            supports_temperature=False,  # GPT-5 only supports default
            supports_reasoning_effort=True,
            supports_verbosity=True,
            timeout_seconds=600  # 10 minutes for complex analysis
        ),
        ModelConfig(
            name="gpt-5-mini",
            max_tokens=8192,
            supports_temperature=False,
            supports_reasoning_effort=True,
            supports_verbosity=True,
            timeout_seconds=300
        ),
        ModelConfig(
            name="gpt-4-turbo",
            max_tokens=4096,
            default_temperature=0.1,  # Lower temperature for consistency
            timeout_seconds=300
        ),
        ModelConfig(
            name="gpt-4-vision-preview",
            max_tokens=4096,
            default_temperature=0.1,
            timeout_seconds=300
        )
    ])
    
    # Processing settings
    use_gpt5_only: bool = field(default_factory=lambda: os.getenv("USE_GPT5_ONLY", "true").lower() == "true")
    skip_traditional_extraction: bool = field(default_factory=lambda: os.getenv("USE_GPT5_ONLY", "true").lower() == "true")
    
    # PDF processing
    pdf_dpi: int = 200  # DPI for rendering PDFs to images
    max_pages_per_request: int = 5  # Maximum pages to send in one API call
    auto_detect_floor_plans: bool = True  # Let GPT-5 identify floor plan pages
    
    # Responses API settings (for GPT-5)
    use_responses_api: bool = True
    responses_api_version: str = "v1"
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    
    # Schema validation
    strict_schema_validation: bool = True
    allow_partial_results: bool = True  # Return partial data if some parsing fails
    
    # Climate data
    default_climate_zone: str = "4A"  # Default ASHRAE climate zone
    default_zip_code: str = "99006"  # Default ZIP if not provided
    
    # HVAC calculation defaults
    default_ceiling_height_ft: float = 8.0
    default_wall_r_value: float = 13.0
    default_ceiling_r_value: float = 30.0
    default_floor_r_value: float = 19.0
    default_air_changes_per_hour: float = 0.5
    
    # Confidence thresholds
    min_room_confidence: float = 0.3  # Minimum confidence to include a room
    min_overall_confidence: float = 0.5  # Minimum confidence for entire analysis
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Get model configuration by name"""
        for model in self.models:
            if model.name == name:
                return model
        return None
    
    def get_primary_model(self) -> ModelConfig:
        """Get the primary (first) model to try"""
        return self.models[0]
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for vision processing")
        
        if not self.models:
            raise ValueError("At least one model must be configured")
        
        return True


# Global configuration instance
vision_config = VisionConfig()

# Export commonly used settings
USE_GPT5_ONLY = vision_config.use_gpt5_only
SKIP_TRADITIONAL = vision_config.skip_traditional_extraction
PDF_DPI = vision_config.pdf_dpi