from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import datetime

class MixedTrackBase(BaseModel):
    """Base schema for mixed track"""
    generated_music_id: int = Field(..., description="ID of the generated music to mix stems from")
    proj_id: int = Field(..., description="Project ID")
    selected_stems: List[str] = Field(..., description="List of stem types to include in the mix")
    volume_levels: Optional[Dict[str, float]] = Field(None, description="Optional volume adjustments for each stem (0.0-1.0)")

class MixedTrackCreate(MixedTrackBase):
    """Schema for creating a new mixed track record"""
    pass

class MixedTrackResponse(MixedTrackBase):
    """Schema for mixed track response"""
    id: int
    user_id: int
    filename: str
    gdrive_file_id: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    progress: Optional[int] = 0
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    task_id: Optional[str] = None
    
    class Config:
        orm_mode = True

class MixedTrackListResponse(BaseModel):
    """Schema for paginated list of mixed tracks"""
    items: List[MixedTrackResponse]
    total: int
    skip: int
    limit: int
    
    class Config:
        orm_mode = True
