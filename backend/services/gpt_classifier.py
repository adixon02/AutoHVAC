"""
GPT Room Label Classifier
Uses GPT for semantic classification ONLY - no numerical extraction
All geometry comes from vector/OCR extraction
"""

import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI
import asyncio
import concurrent.futures

logger = logging.getLogger(__name__)

# Room types GPT can classify
ROOM_TYPES = [
    "living", "kitchen", "dining", "bedroom", "bathroom", 
    "hallway", "closet", "laundry", "garage", "porch",
    "mechanical", "storage", "office", "bonus", "other"
]

# Tight JSON schema for function calling
CLASSIFICATION_SCHEMA = {
    "name": "classify_room_labels",
    "parameters": {
        "type": "object",
        "properties": {
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chip_id": {"type": "string"},
                        "label_text": {"type": "string"},
                        "room_type": {"type": "string", "enum": ROOM_TYPES}
                    },
                    "required": ["chip_id", "label_text", "room_type"]
                }
            },
            "floor_name": {"type": "string"}
        },
        "required": ["rooms"]
    }
}


@dataclass
class LabelChip:
    """A cropped label region from the blueprint"""
    chip_id: str
    image_base64: str
    binarized_base64: Optional[str] = None
    position: Optional[Dict[str, float]] = None  # x, y coordinates if needed


class GPTRoomClassifier:
    """
    Classifies room labels using GPT - NO NUMERICAL EXTRACTION
    All measurements come from geometry/scale detection
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-2024-11-20"  # Latest GPT-4o model
        self.timeout = 30  # 30 second timeout
        self.max_tokens = 600  # Small response size
        
    def classify_labels(
        self, 
        label_chips: List[LabelChip],
        floor_hint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Classify room labels with a single batched GPT call
        
        Args:
            label_chips: List of cropped label regions
            floor_hint: Optional floor name hint
            
        Returns:
            Classification results or None if failed
        """
        try:
            # Build the image content for the message
            image_content = []
            
            # Add instruction text
            prompt = self._build_classification_prompt(len(label_chips), floor_hint)
            
            # Add each label chip (both raw and binarized if available)
            for chip in label_chips:
                # Add raw image
                image_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{chip.image_base64}",
                        "detail": "low"  # Low detail for label chips
                    }
                })
                
                # Add binarized version if available
                if chip.binarized_base64:
                    image_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{chip.binarized_base64}",
                            "detail": "low"
                        }
                    })
            
            # Make the GPT call with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a blueprint label classifier. Identify room types from labels ONLY. Do not extract or report any numbers."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            *image_content
                        ]
                    }
                ],
                functions=[CLASSIFICATION_SCHEMA],
                function_call={"name": "classify_room_labels"},
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                temperature=0.1  # Low temperature for consistency
            )
            
            # Extract the function call response
            if response.choices[0].message.function_call:
                result = json.loads(response.choices[0].message.function_call.arguments)
                logger.info(f"Successfully classified {len(result.get('rooms', []))} room labels")
                return result
            else:
                logger.warning("GPT response did not include function call")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"GPT classification timed out after {self.timeout}s")
            return None
        except Exception as e:
            logger.warning(f"GPT classification failed: {e}")
            return None
    
    def _build_classification_prompt(self, num_chips: int, floor_hint: Optional[str]) -> str:
        """Build the classification prompt"""
        floor_str = f" (likely {floor_hint})" if floor_hint else ""
        
        return f"""I'm showing you {num_chips} room label images from a blueprint{floor_str}.

For each label image, identify:
1. The text you can read (room name)
2. The room type category

IMPORTANT RULES:
- Focus ONLY on reading the text and classifying the room type
- Do NOT extract or mention any numbers (dimensions, areas, etc.)
- If you see "BR" or "BED" → bedroom
- If you see "BA" or "BATH" → bathroom
- If you see "KIT" → kitchen
- If you see "LR" or "LIVING" → living
- If you see "GAR" → garage
- If text is unclear, use your best judgment for room type

Classify each label into one of these types:
{', '.join(ROOM_TYPES)}"""
    
    def fallback_regex_classification(self, ocr_text: str) -> str:
        """
        Fallback classification using regex patterns
        Used when GPT fails or times out
        """
        text = ocr_text.upper()
        
        # Simple pattern matching
        if any(x in text for x in ["BED", "BR", "BDRM"]):
            return "bedroom"
        elif any(x in text for x in ["BATH", "BA", "BTH"]):
            return "bathroom"
        elif any(x in text for x in ["KIT", "KITCHEN"]):
            return "kitchen"
        elif any(x in text for x in ["LIVING", "LR", "GREAT", "FAMILY"]):
            return "living"
        elif any(x in text for x in ["DINING", "DIN"]):
            return "dining"
        elif any(x in text for x in ["GARAGE", "GAR"]):
            return "garage"
        elif any(x in text for x in ["CLOSET", "CLO", "CL"]):
            return "closet"
        elif any(x in text for x in ["HALL", "CORRIDOR"]):
            return "hallway"
        elif any(x in text for x in ["LAUNDRY", "WASH", "UTIL"]):
            return "laundry"
        elif any(x in text for x in ["OFFICE", "STUDY", "DEN"]):
            return "office"
        elif any(x in text for x in ["BONUS", "LOFT"]):
            return "bonus"
        elif any(x in text for x in ["PORCH", "DECK", "PATIO"]):
            return "porch"
        elif any(x in text for x in ["STORAGE", "STOR"]):
            return "storage"
        elif any(x in text for x in ["MECH", "MECHANICAL", "FURNACE"]):
            return "mechanical"
        else:
            return "other"


async def classify_with_cancellation(
    classifier: GPTRoomClassifier,
    label_chips: List[LabelChip],
    cancel_token: asyncio.Event
) -> Optional[Dict[str, Any]]:
    """
    Classify labels with cancellation support
    
    Args:
        classifier: GPT classifier instance
        label_chips: Label regions to classify
        cancel_token: Cancellation event
        
    Returns:
        Classification results or None if cancelled/failed
    """
    # Run classification in executor to make it cancellable
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = loop.run_in_executor(
            executor,
            classifier.classify_labels,
            label_chips
        )
        
        # Wait for either completion or cancellation
        try:
            while not cancel_token.is_set():
                try:
                    result = await asyncio.wait_for(
                        asyncio.shield(future),
                        timeout=1.0  # Check cancel token every second
                    )
                    return result
                except asyncio.TimeoutError:
                    continue  # Check cancel token again
                    
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return None
        
        # Cancelled
        logger.info("Classification cancelled by token")
        return None


# Module-level instance for convenience
import os
_classifier = None

def get_classifier() -> GPTRoomClassifier:
    """Get or create the global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = GPTRoomClassifier()
    return _classifier