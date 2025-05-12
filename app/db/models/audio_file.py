# app/db/models/audio_file.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
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
    
    # Relationships
    project = relationship("Project", back_populates="audio_files")
    user = relationship("User", back_populates="audio_files")