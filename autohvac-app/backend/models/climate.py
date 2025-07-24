"""
Climate data models
Exact match to TypeScript definitions in shared/types.ts  
"""
from pydantic import BaseModel, Field

class ClimateData(BaseModel):
    zip_code: str = Field(..., pattern=r'^\d{5}$')
    zone: str = Field(..., min_length=2, max_length=3)  # "3A", "4A", etc.
    heating_degree_days: int = Field(..., ge=0, le=10000)
    cooling_degree_days: int = Field(..., ge=0, le=6000)
    winter_design_temp: int = Field(..., ge=-40, le=70)  # °F
    summer_design_temp: int = Field(..., ge=70, le=120)  # °F
    humidity: float = Field(..., ge=0.005, le=0.030)  # humidity ratio