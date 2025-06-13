"""
This module configures all relationships between models after they have been defined.
This approach avoids circular import issues in SQLAlchemy.
"""
from sqlalchemy.orm import relationship

from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.audio_file import AudioFile
from app.db.models.generated_music import GeneratedMusic
from app.db.models.stem import Stem
from app.db.models.mixed_track import MixedTrack

# Configure User relationships
User.projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
User.audio_files = relationship("AudioFile", back_populates="user")
User.generated_music = relationship("GeneratedMusic", back_populates="user", cascade="all, delete-orphan")
User.mixed_tracks = relationship("MixedTrack", back_populates="user", cascade="all, delete-orphan")

# Configure Project relationships
Project.user = relationship("User", back_populates="projects")
Project.audio_files = relationship("AudioFile", back_populates="project", cascade="all, delete-orphan")
Project.generated_music = relationship("GeneratedMusic", back_populates="project", cascade="all, delete-orphan")
Project.mixed_tracks = relationship("MixedTrack", back_populates="project", cascade="all, delete-orphan")

# Configure AudioFile relationships
AudioFile.project = relationship("Project", back_populates="audio_files")
AudioFile.user = relationship("User", back_populates="audio_files")
AudioFile.melody_for_generations = relationship(
    "GeneratedMusic",
    foreign_keys="GeneratedMusic.melody_audio_id",
    back_populates="melody_audio"
)

# Configure GeneratedMusic relationships
GeneratedMusic.project = relationship("Project", back_populates="generated_music")
GeneratedMusic.user = relationship("User", back_populates="generated_music")
GeneratedMusic.melody_audio = relationship("AudioFile", foreign_keys="GeneratedMusic.melody_audio_id", back_populates="melody_for_generations")
GeneratedMusic.stems = relationship("Stem", back_populates="generated_music", cascade="all, delete-orphan")
GeneratedMusic.mixed_tracks = relationship("MixedTrack", back_populates="generated_music", cascade="all, delete-orphan")

# Configure Stem relationships
Stem.generated_music = relationship("GeneratedMusic", back_populates="stems")

# Configure MixedTrack relationships
MixedTrack.project = relationship("Project", back_populates="mixed_tracks")
MixedTrack.user = relationship("User", back_populates="mixed_tracks")
MixedTrack.generated_music = relationship("GeneratedMusic", back_populates="mixed_tracks")
