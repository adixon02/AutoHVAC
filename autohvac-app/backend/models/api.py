"""
API request/response models
Exact match to TypeScript definitions in shared/types.ts
"""
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List
from .project import ProjectInfo, BuildingCharacteristics, Room
from .calculations import LoadCalculation, SystemRecommendation

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None

class CalculationRequest(BaseModel):
    project: ProjectInfo
    building: BuildingCharacteristics
    rooms: List[Room]

class CalculationResponse(BaseModel):
    load_calculation: LoadCalculation
    recommendations: List[SystemRecommendation]