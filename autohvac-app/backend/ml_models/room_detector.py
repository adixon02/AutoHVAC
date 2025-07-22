import numpy as np
from typing import Dict, Any, List, Tuple
import cv2
from pathlib import Path

class RoomDetector:
    """
    ML-based room detection from blueprint images
    In production, this would use YOLOv8 or similar trained model
    """
    
    def __init__(self):
        self.model = None  # Would load trained model here
        self.room_types = [
            "living_room", "bedroom", "kitchen", "bathroom",
            "dining_room", "hallway", "closet", "garage",
            "laundry", "office", "utility"
        ]
    
    async def detect_rooms(self, blueprint_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect and classify rooms from blueprint data
        """
        # For MVP, use simple heuristics instead of ML
        rooms = []
        
        # Get dimensions
        dimensions = blueprint_data.get("dimensions", {})
        total_width = dimensions.get("width", 0)
        total_height = dimensions.get("height", 0)
        
        # Extract text labels to help identify rooms
        text_elements = blueprint_data.get("text_elements", [])
        room_labels = [t for t in text_elements if t.get("type") == "room_label"]
        
        # Simple grid-based room detection (placeholder for ML model)
        # In production, this would use trained model to detect room boundaries
        
        # Example room detection based on typical residential layout
        sample_rooms = [
            {
                "name": "Living Room",
                "type": "living_room",
                "area": 400,  # sq ft
                "center": (total_width * 0.3, total_height * 0.5),
                "boundary": [(100, 100), (300, 100), (300, 300), (100, 300)],
                "features": {
                    "windows": 2,
                    "doors": 2,
                    "exterior_walls": 1
                }
            },
            {
                "name": "Kitchen",
                "type": "kitchen",
                "area": 200,
                "center": (total_width * 0.7, total_height * 0.3),
                "boundary": [(400, 100), (550, 100), (550, 250), (400, 250)],
                "features": {
                    "windows": 1,
                    "doors": 2,
                    "exterior_walls": 2,
                    "appliances": True
                }
            },
            {
                "name": "Master Bedroom",
                "type": "bedroom",
                "area": 300,
                "center": (total_width * 0.3, total_height * 0.7),
                "boundary": [(100, 400), (350, 400), (350, 600), (100, 600)],
                "features": {
                    "windows": 2,
                    "doors": 1,
                    "exterior_walls": 2,
                    "closet": True
                }
            },
            {
                "name": "Bedroom 2",
                "type": "bedroom", 
                "area": 180,
                "center": (total_width * 0.7, total_height * 0.7),
                "boundary": [(450, 400), (600, 400), (600, 550), (450, 550)],
                "features": {
                    "windows": 1,
                    "doors": 1,
                    "exterior_walls": 1
                }
            },
            {
                "name": "Bathroom",
                "type": "bathroom",
                "area": 80,
                "center": (total_width * 0.5, total_height * 0.5),
                "boundary": [(350, 300), (450, 300), (450, 380), (350, 380)],
                "features": {
                    "windows": 0,
                    "doors": 1,
                    "exterior_walls": 0,
                    "exhaust_required": True
                }
            }
        ]
        
        # Match detected rooms with text labels if available
        for room in sample_rooms:
            # Find matching label
            for label in room_labels:
                if self._fuzzy_match(room["name"], label.get("text", "")):
                    room["detected_label"] = label.get("text")
                    room["label_confidence"] = 0.95
                    break
            
            # Calculate HVAC requirements
            room["hvac_requirements"] = await self._calculate_room_hvac(room)
            
            rooms.append(room)
        
        return rooms
    
    async def _calculate_room_hvac(self, room: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate HVAC requirements for a room
        """
        base_cfm_per_sqft = 1.0  # CFM per square foot
        
        # Adjust based on room type
        cfm_multipliers = {
            "kitchen": 1.2,      # More ventilation needed
            "bathroom": 1.5,     # Exhaust requirements
            "living_room": 1.1,  # Higher occupancy
            "bedroom": 0.9,      # Lower during sleep
            "garage": 0.0        # Usually not conditioned
        }
        
        multiplier = cfm_multipliers.get(room["type"], 1.0)
        required_cfm = room["area"] * base_cfm_per_sqft * multiplier
        
        # Determine supply register size
        if required_cfm < 100:
            register_size = "6 inch"
        elif required_cfm < 200:
            register_size = "8 inch"
        elif required_cfm < 300:
            register_size = "10 inch"
        else:
            register_size = "12 inch"
        
        return {
            "required_cfm": round(required_cfm),
            "register_size": register_size,
            "register_count": 1 if required_cfm < 250 else 2,
            "return_required": room["area"] > 200,
            "exhaust_required": room.get("features", {}).get("exhaust_required", False)
        }
    
    def _fuzzy_match(self, str1: str, str2: str) -> bool:
        """
        Simple fuzzy string matching
        """
        return str1.lower() in str2.lower() or str2.lower() in str1.lower()
    
    async def train_model(self, training_data_path: Path):
        """
        Train room detection model (placeholder for actual training)
        """
        # In production, this would:
        # 1. Load annotated blueprint dataset
        # 2. Train YOLOv8 or similar model
        # 3. Save trained weights
        pass
    
    async def load_model(self, model_path: Path):
        """
        Load pre-trained model
        """
        # Would load actual model weights here
        self.model = "placeholder_model"