"""
This module configures all relationships between models after they have been defined.
This approach avoids circular import issues in SQLAlchemy.
"""
from sqlalchemy.orm import relationship

from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.audio_file import AudioFile
from app.db.models.fusion import Fusion

# Configure User relationships
User.projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
User.audio_files = relationship("AudioFile", back_populates="user")
User.fusions = relationship("Fusion", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

# Configure Project relationships
Project.user = relationship("User", back_populates="projects")
Project.audio_files = relationship("AudioFile", back_populates="project", cascade="all, delete-orphan")
Project.fusions = relationship("Fusion", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

# Configure AudioFile relationships
AudioFile.project = relationship("Project", back_populates="audio_files")
AudioFile.user = relationship("User", back_populates="audio_files")
AudioFile.source_tracks = relationship(
    "AudioFile", 
    primaryjoin="or_(AudioFile.id==AudioFile.source_track1_id, AudioFile.id==AudioFile.source_track2_id)",
    remote_side="AudioFile.id"
)
AudioFile.fusions_as_track1 = relationship(
    "Fusion", 
    foreign_keys="Fusion.track1_id", 
    back_populates="track1", 
    lazy="selectin"
)
AudioFile.fusions_as_track2 = relationship(
    "Fusion", 
    foreign_keys="Fusion.track2_id", 
    back_populates="track2", 
    lazy="selectin"
)

# Configure Fusion relationships
Fusion.track1 = relationship("AudioFile", foreign_keys="Fusion.track1_id", back_populates="fusions_as_track1")
Fusion.track2 = relationship("AudioFile", foreign_keys="Fusion.track2_id", back_populates="fusions_as_track2")
Fusion.project = relationship("Project", back_populates="fusions")
Fusion.user = relationship("User", back_populates="fusions")
Fusion.output_track = relationship("AudioFile", foreign_keys="Fusion.output_track_id")
