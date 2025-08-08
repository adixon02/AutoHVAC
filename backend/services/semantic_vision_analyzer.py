"""
Semantic Vision Analyzer - Labels Only, No Measurements
Uses Vision models ONLY for semantic understanding (room types, labels, schedules)
Never asks the model to measure or calculate dimensions
"""

import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image
import io

logger = logging.getLogger(__name__)


@dataclass
class SemanticRoom:
    """Room semantics without measurements"""
    label: str  # Text label from blueprint (e.g., "MASTER BEDROOM")
    room_type: str  # Classified type: bedroom, bathroom, kitchen, etc.
    features: List[str]  # Observed features: windows, doors, fixtures
    adjacencies: List[str]  # What rooms it connects to
    confidence: float
    
    # These come from geometry, NOT vision
    geometry_id: Optional[str] = None  # Links to geometry-detected room
    area_sqft: Optional[float] = None  # From geometry calculation
    polygon: Optional[List[Tuple[float, float]]] = None  # From geometry


@dataclass  
class WindowSchedule:
    """Window information from schedule"""
    mark: str  # Window mark (W1, W2, etc.)
    window_type: str  # Double hung, casement, fixed, etc.
    rough_opening: Optional[str] = None  # Text like "3'-0" x 4'-0""
    u_factor: Optional[float] = None
    shgc: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class DoorSchedule:
    """Door information from schedule"""
    mark: str  # Door mark (D1, D2, etc.)
    door_type: str  # Exterior, interior, french, sliding
    material: Optional[str] = None  # Wood, steel, fiberglass
    rough_opening: Optional[str] = None  # Text like "3'-0" x 6'-8""
    u_factor: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class EnvelopeInfo:
    """Building envelope information from notes/schedules"""
    wall_type: Optional[str] = None  # 2x4, 2x6, etc.
    wall_r_value: Optional[float] = None
    ceiling_r_value: Optional[float] = None
    floor_r_value: Optional[float] = None
    foundation_type: Optional[str] = None  # slab, crawl, basement
    roof_type: Optional[str] = None  # hip, gable, flat
    insulation_notes: List[str] = None
    construction_year: Optional[int] = None


@dataclass
class SemanticAnalysis:
    """Complete semantic analysis - labels only, no measurements"""
    # Room semantics
    rooms: List[SemanticRoom]
    
    # Building info
    building_type: str  # residential, commercial
    num_stories: Optional[int] = None
    
    # Schedules
    window_schedule: List[WindowSchedule]
    door_schedule: List[DoorSchedule]
    
    # Envelope
    envelope: EnvelopeInfo
    
    # Equipment (if visible)
    hvac_equipment: List[str]  # Any HVAC equipment labels found
    
    # General
    project_name: Optional[str] = None
    architect: Optional[str] = None
    drawing_date: Optional[str] = None
    north_arrow: bool = False
    
    # Metadata
    confidence: float
    raw_response: Dict[str, Any]


class SemanticVisionAnalyzer:
    """
    Semantic-only vision analyzer
    CRITICAL: Never asks model to measure, only to read labels and classify
    """
    
    def __init__(self):
        """Initialize with OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - semantic vision analysis unavailable")
            self.client = None
            return
            
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4-vision-preview"  # Use stable model
        self.max_tokens = 4096
    
    def analyze_semantics(
        self,
        image_path: str,
        page_type: str = "floor_plan"
    ) -> SemanticAnalysis:
        """
        Extract semantic information from blueprint image.
        
        Args:
            image_path: Path to blueprint image
            page_type: Type of page (floor_plan, schedule, elevation, etc.)
            
        Returns:
            Semantic analysis with labels and classifications only
        """
        if not self.client:
            logger.warning("OpenAI client not initialized - returning empty analysis")
            return self._empty_analysis()
        
        # Load and encode image
        with open(image_path, "rb") as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Create appropriate prompt based on page type
        if page_type == "floor_plan":
            prompt = self._create_floorplan_prompt()
        elif page_type == "schedule":
            prompt = self._create_schedule_prompt()
        else:
            prompt = self._create_general_prompt()
        
        # Send to Vision API
        try:
            logger.info(f"Requesting semantic analysis for {page_type} page")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a blueprint reader who extracts text labels and classifies spaces. You NEVER measure or calculate dimensions."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Low temperature for consistency
            )
            
            # Parse response
            result = response.choices[0].message.content
            logger.info("Semantic analysis complete")
            
            return self._parse_response(result, page_type)
            
        except Exception as e:
            logger.error(f"Semantic vision analysis failed: {e}")
            return self._empty_analysis()
    
    def _create_floorplan_prompt(self) -> str:
        """Prompt for floor plan semantic analysis"""
        return """Analyze this floor plan blueprint and extract ONLY text labels and classifications.

DO NOT measure anything. DO NOT calculate dimensions. DO NOT estimate sizes.
ONLY read text that is already written on the blueprint.

Extract the following semantic information:

1. ROOM LABELS (read the text labels exactly as written):
   - Room names (e.g., "MASTER BEDROOM", "KITCHEN", "BATH")
   - Room numbers if present (e.g., "BEDROOM 2")
   - Classify each into: bedroom, bathroom, kitchen, living, dining, closet, hallway, garage, utility, other

2. FEATURES (identify what you see, don't measure):
   - Door symbols (just note "door to X")
   - Window symbols (just note "window")
   - Fixtures (toilets, sinks, tubs - just note presence)
   - Appliances (just note what's shown)
   - Stairs (just note "stairs up" or "stairs down")

3. TITLE BLOCK (read text only):
   - Project name/address
   - Architect/designer name
   - Drawing date
   - Sheet title

4. BUILDING INFO:
   - Is this single story or multi-story? (based on stair presence)
   - Building type (residential/commercial)
   - Any special spaces (garage, deck, porch)

Return JSON format:
{
  "rooms": [
    {
      "label": "exact text from blueprint",
      "room_type": "classified type",
      "features": ["list of observed features"],
      "connects_to": ["adjacent room labels"],
      "confidence": 0.0-1.0
    }
  ],
  "building_info": {
    "type": "residential/commercial",
    "has_stairs": true/false,
    "special_spaces": ["garage", "deck", etc]
  },
  "title_block": {
    "project": "text if found",
    "architect": "text if found",
    "date": "text if found"
  }
}

REMEMBER: Only read text labels. Do not measure or calculate anything."""
    
    def _create_schedule_prompt(self) -> str:
        """Prompt for schedule/table analysis"""
        return """Analyze this schedule/table and extract the text information.

DO NOT calculate or measure. ONLY read the text and numbers already in the table.

Look for:

1. WINDOW SCHEDULE:
   - Window marks (W1, W2, etc.)
   - Window types (text description)
   - Any U-factor or SHGC values shown
   - Size text if written (don't measure, just read)

2. DOOR SCHEDULE:
   - Door marks (D1, D2, etc.)
   - Door types (interior/exterior)
   - Material descriptions
   - Size text if written

3. ROOM FINISH SCHEDULE:
   - Room names
   - Floor/wall/ceiling finishes

4. GENERAL NOTES:
   - Insulation specifications (R-values)
   - Construction notes
   - Building codes referenced

Return JSON format:
{
  "window_schedule": [
    {
      "mark": "window mark",
      "type": "window type text",
      "size_text": "size as written",
      "u_factor": null or number,
      "shgc": null or number
    }
  ],
  "door_schedule": [
    {
      "mark": "door mark",
      "type": "door type",
      "material": "if specified",
      "size_text": "size as written"
    }
  ],
  "notes": {
    "insulation": ["R-values or insulation notes"],
    "construction": ["construction notes"],
    "other": ["other relevant notes"]
  }
}

ONLY read what's written. Don't interpret or calculate."""
    
    def _create_general_prompt(self) -> str:
        """Generic prompt for other page types"""
        return """Read and classify the text labels on this architectural drawing.

DO NOT measure or calculate anything. ONLY read existing text.

Extract:
- All text labels you can read
- Drawing title
- Any specifications or notes
- Sheet number/name

Return as JSON with the text you found organized by category."""
    
    def _parse_response(self, response: str, page_type: str) -> SemanticAnalysis:
        """Parse GPT response into SemanticAnalysis"""
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                # Find JSON object in response
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            # Parse rooms
            rooms = []
            for room_data in data.get("rooms", []):
                rooms.append(SemanticRoom(
                    label=room_data.get("label", "Unknown"),
                    room_type=room_data.get("room_type", "other"),
                    features=room_data.get("features", []),
                    adjacencies=room_data.get("connects_to", []),
                    confidence=room_data.get("confidence", 0.8)
                ))
            
            # Parse schedules if present
            windows = []
            for w in data.get("window_schedule", []):
                windows.append(WindowSchedule(
                    mark=w.get("mark", ""),
                    window_type=w.get("type", ""),
                    rough_opening=w.get("size_text"),
                    u_factor=w.get("u_factor"),
                    shgc=w.get("shgc"),
                    notes=w.get("notes")
                ))
            
            doors = []
            for d in data.get("door_schedule", []):
                doors.append(DoorSchedule(
                    mark=d.get("mark", ""),
                    door_type=d.get("type", ""),
                    material=d.get("material"),
                    rough_opening=d.get("size_text"),
                    u_factor=d.get("u_factor"),
                    notes=d.get("notes")
                ))
            
            # Parse envelope info
            notes = data.get("notes", {})
            envelope = EnvelopeInfo(
                insulation_notes=notes.get("insulation", [])
            )
            
            # Parse R-values from notes if present
            for note in envelope.insulation_notes:
                if "wall" in note.lower() and "r-" in note.lower():
                    try:
                        r_val = float(note.lower().split("r-")[1].split()[0])
                        envelope.wall_r_value = r_val
                    except:
                        pass
                # Similar for ceiling and floor...
            
            building_info = data.get("building_info", {})
            
            return SemanticAnalysis(
                rooms=rooms,
                building_type=building_info.get("type", "residential"),
                num_stories=1 if not building_info.get("has_stairs") else 2,
                window_schedule=windows,
                door_schedule=doors,
                envelope=envelope,
                hvac_equipment=building_info.get("hvac_equipment", []),
                project_name=data.get("title_block", {}).get("project"),
                architect=data.get("title_block", {}).get("architect"),
                drawing_date=data.get("title_block", {}).get("date"),
                north_arrow=building_info.get("north_arrow", False),
                confidence=0.8,
                raw_response=data
            )
            
        except Exception as e:
            logger.error(f"Failed to parse semantic response: {e}")
            return self._empty_analysis()
    
    def _empty_analysis(self) -> SemanticAnalysis:
        """Return empty analysis when vision is unavailable"""
        return SemanticAnalysis(
            rooms=[],
            building_type="residential",
            num_stories=1,
            window_schedule=[],
            door_schedule=[],
            envelope=EnvelopeInfo(),
            hvac_equipment=[],
            confidence=0.0,
            raw_response={}
        )
    
    def match_rooms_to_geometry(
        self,
        semantic_rooms: List[SemanticRoom],
        geometry_rooms: List[Dict[str, Any]]
    ) -> List[SemanticRoom]:
        """
        Match semantic room labels to geometry-detected rooms.
        This links the labels to the actual measured spaces.
        
        Args:
            semantic_rooms: Rooms with labels from vision
            geometry_rooms: Rooms with polygons/areas from geometry
            
        Returns:
            Semantic rooms with geometry links added
        """
        # Simple matching based on relative positions
        # In practice, would use more sophisticated matching
        
        matched = []
        used_geometry = set()
        
        for sem_room in semantic_rooms:
            best_match = None
            best_score = 0
            
            for i, geom_room in enumerate(geometry_rooms):
                if i in used_geometry:
                    continue
                
                # Score based on features
                score = 0
                
                # Match room type if possible
                geom_type = geom_room.get("room_type", "")
                if geom_type and sem_room.room_type == geom_type:
                    score += 0.5
                
                # Match features
                geom_features = geom_room.get("features", [])
                common_features = set(sem_room.features) & set(geom_features)
                score += len(common_features) * 0.1
                
                # Size consistency (if we have a general sense)
                # Bedrooms typically 100-200 sqft, bathrooms 40-80, etc.
                area = geom_room.get("area", 0)
                if sem_room.room_type == "bedroom" and 80 < area < 300:
                    score += 0.2
                elif sem_room.room_type == "bathroom" and 30 < area < 100:
                    score += 0.2
                elif sem_room.room_type == "kitchen" and 100 < area < 400:
                    score += 0.2
                
                if score > best_score:
                    best_score = score
                    best_match = (i, geom_room)
            
            if best_match:
                idx, geom = best_match
                used_geometry.add(idx)
                
                # Link geometry to semantics
                sem_room.geometry_id = f"room_{idx}"
                sem_room.area_sqft = geom.get("area", 0)
                sem_room.polygon = geom.get("polygon")
                
            matched.append(sem_room)
        
        return matched


# Singleton instance
semantic_vision_analyzer = SemanticVisionAnalyzer()