from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import datetime

class GeneratedMusicBase(BaseModel):
    """Base schema for generated music"""
    text_prompt: str = Field(..., description="Text prompt for music generation")
    duration: int = Field(30, description="Duration in seconds (default: 30)")
    proj_id: int = Field(..., description="Project ID")
    melody_audio_id: Optional[int] = Field(None, description="Optional audio file ID to use as melody conditioning")

class GeneratedMusicCreate(GeneratedMusicBase):
    """Schema for creating a new generated music record"""
    pass

class StemResponse(BaseModel):
    """Schema for stem response"""
    id: int
    stem_type: str
    filename: str
    gdrive_file_id: str
    file_size: Optional[int] = None
    created_at: datetime.datetime
    
    class Config:
        orm_mode = True

class GeneratedMusicResponse(GeneratedMusicBase):
    """Schema for generated music response"""
    id: int
    user_id: int
    job_id: str
    status: str
    progress: int = 0
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    stems: Optional[List[StemResponse]] = None
    
    class Config:
        orm_mode = True

class GeneratedMusicListResponse(BaseModel):
    """Schema for paginated list of generated music"""
    items: List[GeneratedMusicResponse]
    total: int
    skip: int
    limit: int
    
    class Config:
        orm_mode = True
