from sqlalchemy import Boolean, Column, Integer, String
from app.db.base import Base
from sqlalchemy.orm import relationship
class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    audio_files = relationship("AudioFile", back_populates="user")