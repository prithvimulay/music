# app/db/models/audio_file.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class AudioFile(Base):
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    gdrive_file_id = Column(String, unique=True, nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Fusion-related fields
    is_fusion = Column(Boolean, default=False)  # Whether this is a fusion track
    source_track1_id = Column(String, nullable=True)  # Google Drive ID of source track 1
    source_track2_id = Column(String, nullable=True)  # Google Drive ID of source track 2
    fusion_metadata = Column(Text, nullable=True)  # JSON string with fusion metadata (features, etc.)
    
    # Relationships
    project = relationship("Project", back_populates="audio_files")
    user = relationship("User", back_populates="audio_files")