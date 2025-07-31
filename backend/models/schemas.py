from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Literal

class JobResponse(BaseModel):
    job_id: str
    status: str

class UploadResponse(BaseModel):
    job_id: str = Field(..., alias="jobId")
    status: str
    project_label: str = Field(..., alias="projectLabel")
    message: Optional[str] = None  # For warnings like large file processing time
    
    class Config:
        populate_by_name = True
        by_alias = True

class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    result: Optional[Any] = None
    error: Optional[str] = None
    assumptions_collected: Optional[bool] = None
    progress_percent: Optional[int] = None
    current_stage: Optional[str] = None

class ComponentDetection(BaseModel):
    type: str
    location: Optional[str] = None
    capacity: Optional[str] = None
    material: Optional[str] = None
    total_length: Optional[str] = None
    zones: Optional[int] = None

class BlueprintAnalysis(BaseModel):
    filename: str
    file_size: int
    detected_components: list[ComponentDetection]
    estimated_cost: str
    processing_time: str

class SubscribeRequest(BaseModel):
    email: EmailStr

class SubscribeResponse(BaseModel):
    checkout_url: str

class UploadRequest(BaseModel):
    email: EmailStr

class PaymentRequiredResponse(BaseModel):
    message: str
    checkout_url: str