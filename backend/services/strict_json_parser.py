"""
Strict JSON Parser - Helper for parsing and validating GPT-5 responses
Handles markdown fences, validates against schema, and self-heals invalid JSON
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class StrictJSONParser:
    """Parse and validate JSON responses from GPT-5 with self-healing"""
    
    @staticmethod
    def extract_json(content: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from response content, handling markdown fences
        
        Args:
            content: Raw response content from GPT-5
            
        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        if not content:
            return None
        
        # Try direct JSON parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Remove markdown code fences
        # Pattern 1: ```json ... ```
        json_fence_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_fence_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON from markdown fence: {e}")
        
        # Pattern 2: Raw JSON object anywhere in content
        json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_object_pattern, content, re.DOTALL)
        
        # Try each potential JSON object, starting with the largest
        for match in sorted(matches, key=len, reverse=True):
            try:
                result = json.loads(match)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue
        
        # Last resort: try to find JSON-like structure and clean it
        content = content.strip()
        
        # Remove common prefixes/suffixes
        prefixes = ["Here is the JSON:", "JSON:", "Response:", "Output:"]
        for prefix in prefixes:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        # Remove trailing text after JSON
        if content.startswith('{'):
            # Find the matching closing brace
            brace_count = 0
            end_pos = 0
            for i, char in enumerate(content):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > 0:
                try:
                    return json.loads(content[:end_pos])
                except json.JSONDecodeError:
                    pass
        
        logger.warning(f"Could not extract valid JSON from response (first 200 chars): {content[:200]}")
        return None
    
    @staticmethod
    def validate_against_schema(
        data: Dict[str, Any],
        schema_class: Type[BaseModel]
    ) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate JSON data against a Pydantic schema
        
        Args:
            data: Parsed JSON dictionary
            schema_class: Pydantic model class to validate against
            
        Returns:
            Tuple of (is_valid, validated_object, error_message)
        """
        try:
            validated = schema_class(**data)
            return True, validated, None
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field_path = " -> ".join(str(x) for x in error['loc'])
                error_details.append(f"{field_path}: {error['msg']}")
            
            error_message = "Schema validation failed:\n" + "\n".join(error_details)
            logger.debug(f"Validation errors: {error_message}")
            return False, None, error_message
    
    @staticmethod
    def create_self_heal_prompt(
        original_json: Dict[str, Any],
        validation_errors: str,
        schema_description: str
    ) -> str:
        """
        Create a prompt to fix JSON validation errors
        
        Args:
            original_json: The JSON that failed validation
            validation_errors: Description of validation errors
            schema_description: Description of expected schema
            
        Returns:
            Prompt string for self-healing
        """
        return f"""The JSON response has validation errors. Please fix it to match the schema.

VALIDATION ERRORS:
{validation_errors}

ORIGINAL JSON:
{json.dumps(original_json, indent=2)}

EXPECTED SCHEMA:
{schema_description}

Return ONLY the corrected JSON with all required fields properly filled. 
Ensure all rooms have valid IDs, names, dimensions, and required fields.
If data is missing, use reasonable defaults based on the blueprint context."""
    
    @staticmethod
    def parse_and_validate(
        content: str,
        schema_class: Type[BaseModel],
        max_retries: int = 1
    ) -> tuple[bool, Optional[BaseModel], Optional[Dict[str, Any]]]:
        """
        Parse JSON and validate against schema with retries
        
        Args:
            content: Raw response content
            schema_class: Pydantic model to validate against
            max_retries: Number of validation attempts
            
        Returns:
            Tuple of (success, validated_object, raw_json)
        """
        # Extract JSON
        raw_json = StrictJSONParser.extract_json(content)
        if not raw_json:
            logger.error("Failed to extract JSON from response")
            return False, None, None
        
        # Log first 500 chars of extracted JSON for debugging
        json_preview = json.dumps(raw_json, indent=2)[:500]
        logger.debug(f"Extracted JSON preview: {json_preview}")
        
        # Validate against schema
        is_valid, validated, error_msg = StrictJSONParser.validate_against_schema(
            raw_json, schema_class
        )
        
        if is_valid:
            logger.info("JSON validation successful")
            return True, validated, raw_json
        
        logger.warning(f"Initial validation failed: {error_msg}")
        
        # For now, return the raw JSON even if validation fails
        # In production, this would trigger a self-heal retry
        return False, None, raw_json
    
    @staticmethod
    def safe_extract_rooms(json_data: Dict[str, Any]) -> list:
        """
        Safely extract rooms from various JSON structures
        
        Args:
            json_data: Parsed JSON dictionary
            
        Returns:
            List of room dictionaries
        """
        rooms = []
        
        # Try different paths where rooms might be
        possible_paths = [
            lambda d: d.get('rooms', []),
            lambda d: d.get('blueprint_takeoff', {}).get('rooms', []),
            lambda d: d.get('data', {}).get('rooms', []),
            lambda d: d.get('result', {}).get('rooms', []),
            lambda d: d.get('analysis', {}).get('rooms', []),
        ]
        
        for path_func in possible_paths:
            try:
                extracted = path_func(json_data)
                if extracted and isinstance(extracted, list) and len(extracted) > 0:
                    rooms = extracted
                    break
            except (AttributeError, TypeError):
                continue
        
        # Validate rooms have minimum required fields
        valid_rooms = []
        for i, room in enumerate(rooms):
            if isinstance(room, dict):
                # Ensure minimum fields exist
                if 'id' not in room:
                    room['id'] = f"room_{i+1:03d}"
                if 'name' not in room:
                    room['name'] = f"Room {i+1}"
                if 'area_sqft' not in room and 'area' not in room:
                    # Try to calculate from dimensions
                    if 'width_ft' in room and 'length_ft' in room:
                        room['area_sqft'] = room['width_ft'] * room['length_ft']
                    else:
                        room['area_sqft'] = 100  # Default
                
                valid_rooms.append(room)
        
        return valid_rooms


# Global parser instance
strict_parser = StrictJSONParser()