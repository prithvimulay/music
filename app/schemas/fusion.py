# app/schemas/fusion.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

class FusionRequest(BaseModel):
    track1_id: int
    track2_id: int
    project_id: int
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
    status: str
    task_id: str

class FusionStatus(BaseModel):
    id: int
    status: str
    filename: str
    created_at: datetime

class FusionPrompt(BaseModel):
    """Schema for returning the generated prompt to the user for confirmation"""
    generated_prompt: str
    track1_id: int
    track2_id: int
    project_id: int
    feature_data: dict