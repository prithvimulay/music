# app/schemas/audio_file.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class AudioFileBase(BaseModel):
    filename: str
    proj_id: int

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileUpdate(AudioFileBase):
    filename: Optional[str] = None
    proj_id: Optional[int] = None

class AudioFileInDBBase(AudioFileBase):
    id: int
    gdrive_file_id: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_fusion: Optional[bool] = False
    status: Optional[str] = "PENDING"
    task_id: Optional[str] = None
    source_track1_id: Optional[int] = None
    source_track2_id: Optional[int] = None
    fusion_metadata: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AudioFile(AudioFileInDBBase):
    pass