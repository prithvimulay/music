"""
Database models package.
"""
# First import all models
from app.db.models.user import User
from app.db.models.project import Project
from app.db.models.audio_file import AudioFile
from app.db.models.generated_music import GeneratedMusic
from app.db.models.stem import Stem
from app.db.models.mixed_track import MixedTrack

# Then import relationships to configure them after all models are defined
from app.db.models.relationships import *  # This will set up all the relationships