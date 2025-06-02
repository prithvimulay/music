# app/db/models/audio_file.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.sql import func
import datetime
from app.db.base import Base

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    gdrive_file_id = Column(String, nullable=False)
    proj_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)   

    # New fields for fusion tracks
    is_fusion = Column(Boolean, default=False)
    source_track1_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    source_track2_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    fusion_metadata = Column(Text, nullable=True)
    status = Column(String, default="PENDING")
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    task_id = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships are defined in app.db.models.relationships