# app/schemas/fusion.py
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class FusionStatusEnum(str, Enum):
    """Enum for tracking fusion status"""
    PENDING = "pending"
    PROCESSING = "processing"
    FEATURE_EXTRACTION = "feature_extraction"
    GENERATING = "generating"
    ENHANCING = "enhancing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FusionRequest(BaseModel):
    track1_id: int
    track2_id: int
    proj_id: int  # Changed from project_id to proj_id for consistency
    duration: Optional[int] = Field(
        default=15,  # Default to 15 seconds for small model
        ge=5,        # Minimum 5 seconds
        le=30,       # Maximum 30 seconds
        description="Duration of generated audio in seconds (5-30)"
    )
    temperature: Optional[float] = Field(
        default=1.0,  # Default temperature
        ge=0.1,       # Minimum temperature
        le=1.5,       # Maximum temperature
        description="Controls randomness in generation (0.1-1.5)"
    )
    prompt_guidance: Optional[float] = Field(
        default=3.0,  # Default guidance
        ge=1.0,       # Minimum guidance
        le=7.0,       # Maximum guidance
        description="Controls adherence to prompt (1.0-7.0)"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        max_length=500,  # Limit prompt length
        description="User-provided prompt to guide generation"
    )
    
    @validator('track1_id', 'track2_id')
    def tracks_must_be_different(cls, v, values):
        if 'track1_id' in values and v == values['track1_id'] and v == values.get('track2_id'):
            raise ValueError('The two tracks must be different')
        return v

class FusionResponse(BaseModel):
    id: int
    status: FusionStatusEnum
    task_id: Optional[str] = None
    progress: Optional[int] = 0
    error_message: Optional[str] = None
    
    model_config = {"from_attributes": True}

class FusionStatus(BaseModel):
    id: int
    status: FusionStatusEnum
    progress: Optional[int] = 0
    error_message: Optional[str] = None
    output_filename: Optional[str] = None
    gdrive_file_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class FusionPrompt(BaseModel):
    """Schema for returning the generated prompt to the user for confirmation"""
    generated_prompt: str
    track1_id: int
    track2_id: int
    proj_id: int  # Changed from project_id to proj_id for consistency
    feature_data: Dict[str, Any]
    
    model_config = {"from_attributes": True}

class FusionInDB(BaseModel):
    """Complete Fusion model matching the database schema"""
    id: int
    track1_id: int
    track2_id: int
    proj_id: int  # Changed from project_id to proj_id for consistency
    user_id: int
    duration: int
    temperature: float
    prompt_guidance: float
    custom_prompt: Optional[str] = None
    generated_prompt: Optional[str] = None
    output_filename: Optional[str] = None
    output_path: Optional[str] = None
    gdrive_file_id: Optional[str] = None
    task_id: Optional[str] = None
    status: FusionStatusEnum
    error_message: Optional[str] = None
    progress: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    output_track_id: Optional[int] = None
    
    model_config = {"from_attributes": True}