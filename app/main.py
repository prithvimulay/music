from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.audio_files import router as audio_files_router
from app.api.generated_music import router as generated_music_router
from app.api.mixed_track import router as mixed_track_router
from app.api.test_musicgen import router as test_musicgen_router
from app.api.test import router as test_generation_router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(
    title="PureMusic API",
    description="Backend API for PureMusic application",
    version="0.1.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(audio_files_router, prefix="/api/v1/audio-files", tags=["audio-files"])
app.include_router(generated_music_router, prefix="/api/v1/generated-music", tags=["generated-music"])
app.include_router(mixed_track_router, prefix="/api/v1/mixed-tracks", tags=["mixed-tracks"])
app.include_router(test_musicgen_router, prefix="/api/v1/test", tags=["test"])
app.include_router(test_generation_router, prefix="/api/v1/test", tags=["test"])

@app.get("/")
async def root():
    return {"message": "Welcome to PureMusic API"}

@app.get("/health", status_code=200)
async def health_check():
    """Health check endpoint for Docker healthchecks"""
    return {"status": "healthy"}