from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Enum
import datetime
import enum

from app.db.base import Base

class GenerationStatus(str, enum.Enum):
    """Enum for tracking music generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GeneratedMusic(Base):
    """
    Database model for AI-generated music tracks.
    """
    __tablename__ = "generated_music"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship to project and user
    proj_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Generation parameters
    text_prompt = Column(Text, nullable=False)
    duration = Column(Integer, default=30, nullable=False)
    
    # Optional conditioning audio
    melody_audio_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    
    # Output information
    job_id = Column(String, nullable=False, unique=True)  # Unique identifier for the generation task
    task_id = Column(String, nullable=True)  # Celery task ID
    
    # Status tracking
    status = Column(String, default=GenerationStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, default=0, nullable=False)  # Progress percentage (0-100)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
                      onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Model configuration used
    model_config = Column(Text, nullable=True)  # JSON string with model parameters
    
    def __repr__(self):
        return f"<GeneratedMusic {self.id}: {self.status}>"
