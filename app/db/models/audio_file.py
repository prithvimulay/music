# app/db/models/audio_file.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime
from app.db.base import Base

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    gdrive_file_id = Column(String, nullable=False)
    proj_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New fields for fusion tracks
    is_fusion = Column(Boolean, default=False)
    source_track1_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    source_track2_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    fusion_metadata = Column(Text, nullable=True)
    status = Column(String, default="PENDING")
    task_id = Column(String, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="audio_files")
    user = relationship("User", back_populates="audio_files")
    
    # Self-referential relationships for source tracks
    source_track1 = relationship("AudioFile", foreign_keys=[source_track1_id], remote_side=[id], backref="fusion_tracks1")
    source_track2 = relationship("AudioFile", foreign_keys=[source_track2_id], remote_side=[id], backref="fusion_tracks2")