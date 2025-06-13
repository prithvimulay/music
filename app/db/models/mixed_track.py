from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
import datetime
import json

from app.db.base import Base

class MixedTrack(Base):
    """
    Database model for mixed tracks created from stems.
    """
    __tablename__ = "mixed_tracks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship to generated music
    generated_music_id = Column(Integer, ForeignKey("generated_music.id"), nullable=False)
    
    # Relationship to project and user
    proj_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Mix information
    selected_stems = Column(Text, nullable=False)  # JSON string with selected stem types
    volume_levels = Column(Text, nullable=True)    # JSON string with volume adjustments
    
    # Output file information
    filename = Column(String, nullable=False)
    gdrive_file_id = Column(String, nullable=True)  # Will be populated when mix is complete
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True, default="audio/wav")
    
    # Status tracking
    status = Column(String, default="pending", nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # Progress percentage (0-100)
    error_message = Column(Text, nullable=True)
    task_id = Column(String, nullable=True)  # Celery task ID
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
                      onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MixedTrack {self.id}: {self.status}>"
    
    def get_selected_stems(self):
        """Get selected stems as a list"""
        if not self.selected_stems:
            return []
        return json.loads(self.selected_stems)
    
    def get_volume_levels(self):
        """Get volume levels as a dictionary"""
        if not self.volume_levels:
            return {}
        return json.loads(self.volume_levels)
