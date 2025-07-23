#!/usr/bin/env python3
"""
AI Gap Filler - Targeted GPT-4 integration for completing missing blueprint data
Only used when Python extraction has confidence gaps < 90%
Keeps costs under $0.50 per blueprint
"""

from openai import OpenAI
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import asdict
from enhanced_blueprint_processor import ExtractionResult, ProjectInfo, BuildingCharacteristics, Room, InsulationSpecs

logger = logging.getLogger(__name__)

class AIGapFiller:
    """
    Intelligent AI integration that only fills specific data gaps
    Uses targeted prompts to minimize cost and maximize accuracy
    """
    
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            # Load from environment or config
            try:
                api_key = self._load_api_key()
                self.client = OpenAI(api_key=api_key)
            except:
                logger.warning("OpenAI API key not configured. AI gap filling disabled.")
                self.enabled = False
                return
        
        self.enabled = True
        self.cost_tracking = {
            'total_tokens': 0,
            'total_cost': 0.0,
            'requests': 0
        }
    
    def _load_api_key(self) -> str:
        """Load API key from environment or config file"""
        import os
        
        # Try environment variable first
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return api_key
        
        # Try config file
        config_path = Path('config.json')
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config.get('openai_api_key', '')
        
        raise ValueError("OpenAI API key not found")
    
    def fill_gaps(self, extraction_result: ExtractionResult, pdf_path: Path) -> ExtractionResult:
        """
        Main gap filling function - only processes identified gaps
        """
        if not self.enabled:
            logger.warning("AI gap filling disabled - returning original results")
            return extraction_result
        
        if extraction_result.overall_confidence >= 0.90:
            logger.info(f"High confidence extraction ({extraction_result.overall_confidence:.1%}) - skipping AI")
            return extraction_result
        
        logger.info(f"Filling gaps for {len(extraction_result.gaps_identified)} identified issues")
        
        # Process each gap type
        for gap in extraction_result.gaps_identified:
            try:
                if gap == "missing_address":
                    self._fill_address_gap(extraction_result, pdf_path)
                elif gap == "missing_zip_code":
                    self._fill_zip_gap(extraction_result, pdf_path)
                elif gap == "missing_project_name":
                    self._fill_project_name_gap(extraction_result, pdf_path)
                elif gap == "missing_total_area":
                    self._fill_area_gap(extraction_result, pdf_path)
                elif gap == "insufficient_room_data":
                    self._fill_room_data_gap(extraction_result, pdf_path)
                elif gap == "incomplete_insulation_specs":
                    self._fill_insulation_gap(extraction_result, pdf_path)
                
                # Cost safety check
                if self.cost_tracking['total_cost'] > 0.50:
                    logger.warning("Cost limit reached, stopping AI processing")
                    break
                    
            except Exception as e:
                logger.error(f"Error filling gap {gap}: {e}")
        
        # Recalculate confidence after gap filling
        extraction_result.overall_confidence = self._recalculate_confidence(extraction_result)
        
        logger.info(f"Gap filling complete. New confidence: {extraction_result.overall_confidence:.1%}")
        logger.info(f"AI cost: ${self.cost_tracking['total_cost']:.3f}")
        
        return extraction_result
    
    def _fill_address_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill missing address information"""
        
        if result.project_info.address:
            return  # Already have address
        
        prompt = f"""
        Extract the property address from this blueprint.
        
        Current data:
        - Project: {result.project_info.project_name}
        - City: {result.project_info.city}
        - State: {result.project_info.state}
        - ZIP: {result.project_info.zip_code}
        
        Look for the street address (number + street name).
        Respond with ONLY the street address, nothing else.
        If not found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:5000])
        
        if response and response != "NOT_FOUND":
            result.project_info.address = response.strip()
            result.project_info.confidence_score = min(1.0, result.project_info.confidence_score + 0.2)
            logger.info(f"AI filled address: {response.strip()}")
    
    def _fill_zip_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill missing ZIP code"""
        
        if result.project_info.zip_code:
            return
        
        prompt = f"""
        Extract the ZIP code from this blueprint.
        
        Current data:
        - Address: {result.project_info.address}
        - City: {result.project_info.city}
        - State: {result.project_info.state}
        
        Look for a 5-digit ZIP code.
        Respond with ONLY the ZIP code, nothing else.
        If not found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:3000])
        
        if response and response != "NOT_FOUND" and response.isdigit() and len(response) == 5:
            result.project_info.zip_code = response
            result.project_info.confidence_score = min(1.0, result.project_info.confidence_score + 0.15)
            logger.info(f"AI filled ZIP: {response}")
    
    def _fill_project_name_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill missing project name"""
        
        if result.project_info.project_name:
            return
        
        prompt = f"""
        Extract the project name from this blueprint.
        
        Current data:
        - Address: {result.project_info.address}
        - Owner: {result.project_info.owner}
        
        Look for project description like "Smith Residence", "Jones House + ADU", etc.
        Respond with ONLY the project name, nothing else.
        If not found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:3000])
        
        if response and response != "NOT_FOUND":
            result.project_info.project_name = response.strip()
            result.project_info.confidence_score = min(1.0, result.project_info.confidence_score + 0.15)
            logger.info(f"AI filled project name: {response.strip()}")
    
    def _fill_area_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill missing building area information"""
        
        if result.building_chars.total_area > 0:
            return
        
        prompt = f"""
        Extract building area information from this blueprint.
        
        Look for area statements like:
        - "Total: 2500 SF"
        - "Main Level: 1200 SF"
        - "Upper Level: 800 SF"
        - "ADU: 500 SF"
        
        Respond with a JSON object like:
        {"total": 2500, "main": 1200, "upper": 800, "adu": 500}
        
        If not found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:4000])
        
        if response and response != "NOT_FOUND":
            try:
                area_data = json.loads(response)
                if 'total' in area_data:
                    result.building_chars.total_area = float(area_data['total'])
                if 'main' in area_data:
                    result.building_chars.main_residence_area = float(area_data.get('main', 0))
                if 'adu' in area_data:
                    result.building_chars.adu_area = float(area_data.get('adu', 0))
                
                result.building_chars.confidence_score = min(1.0, result.building_chars.confidence_score + 0.3)
                logger.info(f"AI filled area data: {area_data}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON response for area data: {response}")
    
    def _fill_room_data_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill insufficient room data"""
        
        if len(result.rooms) >= 5:
            return  # Sufficient room data
        
        prompt = f"""
        Extract room information from this blueprint.
        
        Current rooms found: {[room.name for room in result.rooms]}
        
        Look for additional rooms like bedrooms, bathrooms, kitchen, living room, etc.
        
        Respond with a JSON array of rooms:
        [{"name": "Master Bedroom", "area": 200}, {"name": "Kitchen", "area": 150}]
        
        If no additional rooms found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:5000])
        
        if response and response != "NOT_FOUND":
            try:
                room_data = json.loads(response)
                existing_names = set(room.name.lower() for room in result.rooms)
                
                for room_info in room_data:
                    if room_info['name'].lower() not in existing_names:
                        new_room = Room(
                            name=room_info['name'],
                            area=float(room_info.get('area', 100)),
                            floor_type='main',
                            confidence_score=0.7
                        )
                        result.rooms.append(new_room)
                        logger.info(f"AI added room: {new_room.name} ({new_room.area} SF)")
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON response for room data: {response}")
    
    def _fill_insulation_gap(self, result: ExtractionResult, pdf_path: Path):
        """Fill missing insulation specifications"""
        
        if result.insulation.confidence_score >= 0.8:
            return
        
        prompt = f"""
        Extract insulation R-values from this blueprint.
        
        Current values:
        - Wall: R-{result.insulation.wall_r_value}
        - Ceiling: R-{result.insulation.ceiling_r_value}
        - Foundation: R-{result.insulation.foundation_r_value}
        
        Look for R-values like "R-13 walls", "R-30 ceiling", "R-10 foundation".
        
        Respond with JSON:
        {"wall": 13, "ceiling": 30, "foundation": 10}
        
        If not found, respond with "NOT_FOUND".
        """
        
        response = self._call_ai_with_text(prompt, result.raw_data['combined_text'][:4000])
        
        if response and response != "NOT_FOUND":
            try:
                r_values = json.loads(response)
                
                if 'wall' in r_values and r_values['wall'] > 0:
                    result.insulation.wall_r_value = float(r_values['wall'])
                if 'ceiling' in r_values and r_values['ceiling'] > 0:
                    result.insulation.ceiling_r_value = float(r_values['ceiling'])
                if 'foundation' in r_values and r_values['foundation'] > 0:
                    result.insulation.foundation_r_value = float(r_values['foundation'])
                
                result.insulation.confidence_score = min(1.0, result.insulation.confidence_score + 0.3)
                logger.info(f"AI filled R-values: {r_values}")
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON response for R-values: {response}")
    
    def _call_ai_with_text(self, prompt: str, context_text: str) -> Optional[str]:
        """Make a targeted AI call with text context"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at reading architectural blueprints. Extract only the specific information requested. Be precise and concise."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nBlueprint text:\n{context_text}"
                }
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,  # Keep responses short to minimize cost
                temperature=0,   # Deterministic responses
            )
            
            # Track usage and cost
            usage = response.usage
            self.cost_tracking['total_tokens'] += usage.total_tokens
            self.cost_tracking['total_cost'] += usage.total_tokens * 0.00003  # Approx GPT-4 cost
            self.cost_tracking['requests'] += 1
            
            result = response.choices[0].message.content.strip()
            logger.debug(f"AI response: {result} (cost: ${usage.total_tokens * 0.00003:.4f})")
            
            return result
            
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return None
    
    def _recalculate_confidence(self, result: ExtractionResult) -> float:
        """Recalculate overall confidence after gap filling"""
        
        scores = [
            result.project_info.confidence_score,
            result.building_chars.confidence_score,
            result.insulation.confidence_score
        ]
        
        if result.rooms:
            avg_room_score = sum(room.confidence_score for room in result.rooms) / len(result.rooms)
            scores.append(avg_room_score)
        
        return sum(scores) / len(scores)

# Example usage and testing
if __name__ == "__main__":
    from enhanced_blueprint_processor import EnhancedBlueprintProcessor
    
    # Test the complete pipeline
    processor = EnhancedBlueprintProcessor()
    gap_filler = AIGapFiller()  # Will disable if no API key
    
    blueprint_path = Path("/Users/austindixon/Documents/AutoHVAC/reference-files/Permit Plans - 25196 Wyvern (6).pdf")
    
    if blueprint_path.exists():
        # Step 1: Python extraction
        print("🔍 Running Python extraction...")
        result = processor.process_blueprint(blueprint_path)
        
        print(f"\n📊 INITIAL RESULTS")
        print(f"Confidence: {result.overall_confidence:.1%}")
        print(f"Gaps: {', '.join(result.gaps_identified) if result.gaps_identified else 'None'}")
        
        # Step 2: AI gap filling (if needed)
        if result.overall_confidence < 0.90 and gap_filler.enabled:
            print(f"\n🤖 Running AI gap filling...")
            result = gap_filler.fill_gaps(result, blueprint_path)
            
            print(f"\n📊 FINAL RESULTS")
            print(f"Confidence: {result.overall_confidence:.1%}")
            print(f"AI Cost: ${gap_filler.cost_tracking['total_cost']:.3f}")
        else:
            print(f"\n✅ High confidence - AI gap filling skipped")
        
        # Display final results
        print(f"\n📍 FINAL PROJECT INFO")
        print(f"Name: {result.project_info.project_name}")
        print(f"Address: {result.project_info.address}, {result.project_info.city}, {result.project_info.state} {result.project_info.zip_code}")
        print(f"Total Area: {result.building_chars.total_area:,.0f} SF")
        print(f"Rooms: {len(result.rooms)} found")
        print(f"R-Values: Wall R-{result.insulation.wall_r_value}, Ceiling R-{result.insulation.ceiling_r_value}")
        
    else:
        print(f"❌ Blueprint file not found: {blueprint_path}")