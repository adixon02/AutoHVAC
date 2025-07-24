"""
AI-Powered Blueprint Analysis Service
Uses OpenAI GPT-4V for visual blueprint interpretation
Complements regex-based extraction with intelligent analysis
"""
import logging
import base64
import openai
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import pdfplumber  # PDF processing for image conversion
import os
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class AIExtractedData:
    """AI-extracted building data from visual analysis"""
    room_layouts: List[Dict] = None  # Room positions, orientations, adjacencies
    window_orientations: Dict[str, List[str]] = None  # {"north": ["bedroom1", "living"], "south": [...]}
    building_envelope: Dict[str, Any] = None  # Wall types, roof details, foundation
    hvac_existing: Dict[str, Any] = None  # Existing HVAC equipment/ductwork
    architectural_details: Dict[str, Any] = None  # Ceiling heights, structural elements
    extraction_confidence: float = 0.0

class AIBlueprintAnalyzer:
    """
    AI-powered blueprint analysis using OpenAI GPT-4V
    Focuses on visual elements that regex extraction cannot capture
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )
        if not self.client.api_key:
            raise ValueError("OpenAI API key required for AI blueprint analysis")
        
        logger.info("AI Blueprint Analyzer initialized with OpenAI GPT-4V")
    
    async def analyze_blueprint_visual(self, pdf_path: str) -> AIExtractedData:
        """
        Perform visual analysis of blueprint PDF using AI
        
        Args:
            pdf_path: Path to PDF blueprint file
            
        Returns:
            AIExtractedData with visual analysis results
        """
        try:
            logger.info(f"Starting AI visual analysis of {pdf_path}")
            
            # Convert PDF pages to images
            blueprint_images = self._pdf_to_images(pdf_path)
            
            # Analyze each page with AI
            analysis_results = []
            for page_num, image_data in enumerate(blueprint_images):
                logger.info(f"Analyzing page {page_num + 1} with AI")
                
                page_analysis = await self._analyze_page_with_ai(
                    image_data, 
                    page_num + 1,
                    len(blueprint_images)
                )
                analysis_results.append(page_analysis)
            
            # Combine results from all pages
            combined_data = self._combine_analysis_results(analysis_results)
            
            logger.info("AI visual analysis completed")
            return combined_data
            
        except Exception as e:
            logger.error(f"AI blueprint analysis failed: {e}")
            raise
    
    def _pdf_to_images(self, pdf_path: str, dpi: int = 150) -> List[str]:
        """Convert PDF pages to base64-encoded images for AI analysis"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                images = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Convert page to PIL Image
                    image = page.to_image(resolution=dpi).original
                    
                    # Convert to base64 for API
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    image_base64 = base64.b64encode(buffer.getvalue()).decode()
                    
                    images.append(image_base64)
                    logger.info(f"Converted page {page_num + 1} to image ({len(image_base64)} chars)")
                
                return images
            
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {e}")
            raise
    
    async def _analyze_page_with_ai(self, image_base64: str, page_num: int, total_pages: int) -> Dict:
        """Analyze single blueprint page with OpenAI GPT-4V"""
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_analysis_prompt(page_num, total_pages)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # GPT-4 with vision
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content
            
            try:
                analysis_data = json.loads(response_text)
                logger.info(f"AI analysis completed for page {page_num}")
                return analysis_data
                
            except json.JSONDecodeError:
                logger.warning(f"AI response was not valid JSON for page {page_num}")
                return {"error": "Invalid JSON response", "raw_response": response_text}
            
        except Exception as e:
            logger.error(f"AI analysis failed for page {page_num}: {e}")
            return {"error": str(e)}
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for blueprint analysis"""
        return """You are an expert HVAC engineer and blueprint reader. Analyze architectural drawings to extract precise building data for Manual J load calculations.

Focus on extracting:
1. Room layouts with dimensions and orientations
2. Window and door locations with cardinal directions
3. Building envelope details (wall types, insulation callouts)
4. Existing HVAC systems and ductwork
5. Structural elements affecting heat transfer

Always respond with valid JSON format. Be precise with measurements and confident in your identifications."""
    
    def _get_analysis_prompt(self, page_num: int, total_pages: int) -> str:
        """Get specific analysis prompt for this page"""
        return f"""Analyze this blueprint page ({page_num} of {total_pages}) and extract building data for Manual J calculations.

Return JSON with this exact structure:
{{
    "page_type": "floor_plan|elevation|section|detail|title",
    "rooms": [
        {{
            "name": "Living Room",
            "dimensions": {{"length_ft": 16.5, "width_ft": 12.0}},
            "windows": [
                {{"orientation": "south", "width_ft": 4.0, "height_ft": 3.5}},
                {{"orientation": "east", "width_ft": 3.0, "height_ft": 3.5}}
            ],
            "doors": [
                {{"type": "exterior", "orientation": "north", "width_ft": 3.0}}
            ],
            "ceiling_height_ft": 9.0,
            "adjacent_rooms": ["Kitchen", "Hallway"]
        }}
    ],
    "building_envelope": {{
        "wall_construction": "2x6 framed with R-21 batt + R-5 ci",
        "window_specifications": "U-0.30, SHGC-0.65",
        "roof_assembly": "R-49 blown cellulose",
        "foundation": "slab on grade with R-10 edge"
    }},
    "hvac_systems": {{
        "existing_equipment": "heat pump outdoor unit",
        "ductwork_visible": true,
        "return_air_locations": ["hallway ceiling"]
    }},
    "building_orientation": {{
        "north_arrow_direction": "up|right|down|left",  
        "primary_glazing_orientation": "south"
    }},
    "confidence_score": 0.85,
    "notes": "Any additional observations or uncertainties"
}}

Only extract what you can clearly see. Use null for missing data. Be conservative with confidence scores."""
    
    def _combine_analysis_results(self, analysis_results: List[Dict]) -> AIExtractedData:
        """Combine AI analysis from multiple pages into unified data"""
        try:
            combined_rooms = []
            window_orientations = {"north": [], "south": [], "east": [], "west": []}
            building_envelope = {}
            hvac_existing = {}
            architectural_details = {}
            total_confidence = 0.0
            valid_pages = 0
            
            for result in analysis_results:
                if "error" in result:
                    continue
                
                # Combine room data
                if "rooms" in result and result["rooms"]:
                    combined_rooms.extend(result["rooms"])
                
                # Aggregate window orientations
                if "rooms" in result:
                    for room in result["rooms"]:
                        if "windows" in room:
                            for window in room["windows"]:
                                orientation = window.get("orientation", "").lower()
                                if orientation in window_orientations:
                                    window_orientations[orientation].append(room["name"])
                
                # Merge building envelope data
                if "building_envelope" in result:
                    building_envelope.update(result["building_envelope"])
                
                # Merge HVAC data
                if "hvac_systems" in result:
                    hvac_existing.update(result["hvac_systems"])
                
                # Track confidence
                if "confidence_score" in result:
                    total_confidence += result["confidence_score"]
                    valid_pages += 1
            
            # Calculate average confidence
            avg_confidence = total_confidence / valid_pages if valid_pages > 0 else 0.0
            
            # Remove duplicate rooms (by name)
            unique_rooms = []
            seen_names = set()
            for room in combined_rooms:
                room_name = room.get("name", "unknown")
                if room_name not in seen_names:
                    unique_rooms.append(room)
                    seen_names.add(room_name)
            
            ai_data = AIExtractedData(
                room_layouts=unique_rooms,
                window_orientations=window_orientations,
                building_envelope=building_envelope,
                hvac_existing=hvac_existing,
                architectural_details=architectural_details,
                extraction_confidence=avg_confidence
            )
            
            logger.info(f"Combined AI analysis: {len(unique_rooms)} rooms, confidence: {avg_confidence:.2f}")
            return ai_data
            
        except Exception as e:
            logger.error(f"Failed to combine AI analysis results: {e}")
            # Return empty data with zero confidence
            return AIExtractedData(extraction_confidence=0.0)
    
    async def validate_extraction_with_ai(self, extracted_data: Dict, pdf_path: str) -> Dict[str, float]:
        """
        Use AI to validate extracted data against blueprint
        Returns confidence scores for each extracted field
        """
        try:
            # Convert first page to image for validation
            blueprint_images = self._pdf_to_images(pdf_path)
            if not blueprint_images:
                return {}
            
            validation_prompt = f"""Compare this extracted building data against the blueprint image and rate the accuracy of each field on a scale of 0.0 to 1.0:

Extracted Data:
{json.dumps(extracted_data, indent=2)}

Return JSON with confidence scores:
{{
    "floor_area_accuracy": 0.85,
    "insulation_values_accuracy": 0.90,
    "window_data_accuracy": 0.75,
    "room_dimensions_accuracy": 0.80,
    "overall_confidence": 0.82,
    "discrepancies_found": ["Window count may be underestimated", "Missing ceiling height data"]
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": validation_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{blueprint_images[0]}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            validation_result = json.loads(response.choices[0].message.content)
            logger.info(f"AI validation completed: {validation_result.get('overall_confidence', 0):.2f} confidence")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            return {"overall_confidence": 0.5, "error": str(e)}