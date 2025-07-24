"""
Python data models matching the TypeScript types exactly
Following docs/02-development/data-dictionary.md
"""
from .project import ProjectInfo, BuildingCharacteristics, Room
from .climate import ClimateData
from .calculations import LoadCalculation, SystemRecommendation
from .api import CalculationRequest, CalculationResponse, ApiResponse

__all__ = [
    "ProjectInfo",
    "BuildingCharacteristics", 
    "Room",
    "ClimateData",
    "LoadCalculation",
    "SystemRecommendation",
    "CalculationRequest",
    "CalculationResponse",
    "ApiResponse"
]