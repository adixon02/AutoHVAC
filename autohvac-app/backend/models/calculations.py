"""
Load calculation and system recommendation models
Exact match to TypeScript definitions in shared/types.ts
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List

class LoadCalculation(BaseModel):
    project_id: str
    total_cooling_load: int = Field(..., ge=0)  # BTU/hr
    total_heating_load: int = Field(..., ge=0)  # BTU/hr
    cooling_tons: float = Field(..., ge=0.0, le=20.0)  # tons
    heating_tons: float = Field(..., ge=0.0, le=20.0)  # tons
    room_loads: List['RoomLoad']
    calculated_at: datetime

class RoomLoad(BaseModel):
    room_id: str
    cooling_load: int = Field(..., ge=0)  # BTU/hr
    heating_load: int = Field(..., ge=0)  # BTU/hr

class SystemTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"

class CoolingSystem(BaseModel):
    type: str = Field(..., min_length=3, max_length=30)
    size: float = Field(..., ge=0.5, le=20.0)  # tons
    seer: int = Field(..., ge=13, le=25)  # efficiency rating
    brand: str = Field(..., min_length=3, max_length=20)
    model: str = Field(..., min_length=3, max_length=30)
    estimated_cost: int = Field(..., ge=1000, le=50000)  # dollars

class HeatingSystem(BaseModel):
    type: str = Field(..., min_length=3, max_length=30)
    size: int = Field(..., ge=10000, le=300000)  # BTU/hr
    efficiency: float = Field(..., ge=0.8, le=0.98)  # AFUE or HSPF
    brand: str = Field(..., min_length=3, max_length=20)
    model: str = Field(..., min_length=3, max_length=30)
    estimated_cost: int = Field(..., ge=1000, le=50000)  # dollars

class SystemRecommendation(BaseModel):
    tier: SystemTier
    cooling_system: CoolingSystem
    heating_system: HeatingSystem

# Update forward reference
LoadCalculation.model_rebuild()