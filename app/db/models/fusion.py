from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Enum
import datetime
import enum

from app.db.base import Base

class FusionStatus(str, enum.Enum):
    """Enum for tracking fusion status"""
    PENDING = "pending"
    PROCESSING = "processing"
    FEATURE_EXTRACTION = "feature_extraction"
    GENERATING = "generating"
    ENHANCING = "enhancing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Fusion(Base):
    """
    Database model for music fusion tracks.
    """
    __tablename__ = "fusions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship to source tracks
    track1_id = Column(Integer, ForeignKey("audio_files.id"), nullable=False)
    track2_id = Column(Integer, ForeignKey("audio_files.id"), nullable=False)
    
    # Relationship to project and user
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Fusion parameters
    duration = Column(Integer, default=15, nullable=False)
    temperature = Column(Float, default=1.0, nullable=False)
    prompt_guidance = Column(Float, default=3.0, nullable=False)
    custom_prompt = Column(Text, nullable=True)
    
    # Generated prompt based on features
    generated_prompt = Column(Text, nullable=True)
    
    # Output information
    output_filename = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    gdrive_file_id = Column(String, nullable=True)
    
    # Celery task ID for tracking
    task_id = Column(String, nullable=True)
    
    # Status tracking - use String instead of Enum for better database compatibility
    status = Column(String, default=FusionStatus.PENDING.value, nullable=False)
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, default=0, nullable=False)  # Progress percentage (0-100)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Output track relationship (one-to-one)
    output_track_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    
    # Relationships are defined in app.db.models.relationships
    
    def __repr__(self):
        return f"<Fusion {self.id}: {self.status}>"
