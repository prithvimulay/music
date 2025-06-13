from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, List, Optional
import uuid
import datetime
import json

from app.api.auth import get_current_user, get_db
from app.db.models.generated_music import GeneratedMusic, GenerationStatus
from app.db.models.stem import Stem
from app.db.models.project import Project
from app.db.models.audio_file import AudioFile
from app.celeryworker.tasks import generate_music_with_stems
from app.schemas.generated_music import (
    GeneratedMusicCreate,
    GeneratedMusicResponse,
    GeneratedMusicListResponse
)

router = APIRouter()

@router.post("/generate-music", response_model=GeneratedMusicResponse, status_code=status.HTTP_202_ACCEPTED)
def create_music_generation(
    background_tasks: BackgroundTasks,
    music_data: GeneratedMusicCreate,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate music with separated stems using MusicGen-Stem via Hugging Face API.
    
    This endpoint:
    1. Validates the project ownership
    2. Creates a GeneratedMusic record
    3. Triggers an asynchronous Celery task for generation
    4. Returns the record ID for status tracking
    """
    # Validate project ownership
    project = db.query(Project).filter(
        Project.id == music_data.proj_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access to it"
        )
    
    # Create a unique job ID
    job_id = f"gen_{uuid.uuid4().hex[:8]}"
    
    # Create GeneratedMusic record
    generated_music = GeneratedMusic(
        proj_id=music_data.proj_id,
        user_id=current_user.id,
        text_prompt=music_data.text_prompt,
        duration=music_data.duration,
        melody_audio_id=music_data.melody_audio_id if music_data.melody_audio_id else None,
        job_id=job_id,
        status=GenerationStatus.PENDING.value,
        progress=0,
        model_config=json.dumps({
            "model": "facebook/musicgen-stereo-small",
            "api": "huggingface"
        })
    )
    
    db.add(generated_music)
    db.commit()
    db.refresh(generated_music)
    
    # Trigger Celery task asynchronously
    # First, get the Google Drive file ID if melody_audio_id is provided
    melody_gdrive_id = None
    if music_data.melody_audio_id and music_data.melody_audio_id != 1:
        # Query the audio file from database to get its Google Drive ID
        audio_file = db.query(AudioFile).filter(
            AudioFile.id == music_data.melody_audio_id,
            AudioFile.user_id == current_user.id
        ).first()
        
        if audio_file:
            melody_gdrive_id = audio_file.gdrive_file_id
    
    task = generate_music_with_stems.delay(
        generated_music_id=generated_music.id,
        prompt=music_data.text_prompt,
        duration=music_data.duration,
        melody_id=melody_gdrive_id,  # Pass the Google Drive ID, not the database ID
        proj_id=music_data.proj_id,
        user_id=current_user.id
    )
    
    # Update record with task ID
    generated_music.task_id = task.id
    db.commit()
    
    return GeneratedMusicResponse(
        id=generated_music.id,
        proj_id=generated_music.proj_id,
        user_id=generated_music.user_id,
        text_prompt=generated_music.text_prompt,
        duration=generated_music.duration,
        melody_audio_id=generated_music.melody_audio_id,
        job_id=generated_music.job_id,
        status=generated_music.status,
        progress=generated_music.progress,
        created_at=generated_music.created_at,
        task_id=task.id
    )

@router.get("/generated-music/{generated_music_id}", response_model=GeneratedMusicResponse)
def get_generated_music(
    generated_music_id: int,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get details of a generated music record, including its stems.
    """
    # Get the generated music record
    generated_music = db.query(GeneratedMusic).filter(
        GeneratedMusic.id == generated_music_id
    ).first()
    
    if not generated_music:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated music not found"
        )
    
    # Check ownership
    if generated_music.user_id != current_user.id:
        # Check if user has access to the project
        project = db.query(Project).filter(
            Project.id == generated_music.proj_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this generated music"
            )
    
    # Get stems
    stems = db.query(Stem).filter(
        Stem.generated_music_id == generated_music_id
    ).all()
    
    # Create response
    response = GeneratedMusicResponse(
        id=generated_music.id,
        proj_id=generated_music.proj_id,
        user_id=generated_music.user_id,
        text_prompt=generated_music.text_prompt,
        duration=generated_music.duration,
        melody_audio_id=generated_music.melody_audio_id,
        job_id=generated_music.job_id,
        status=generated_music.status,
        progress=generated_music.progress,
        created_at=generated_music.created_at,
        updated_at=generated_music.updated_at,
        completed_at=generated_music.completed_at,
        task_id=generated_music.task_id,
        error_message=generated_music.error_message,
        stems=[{
            "id": stem.id,
            "stem_type": stem.stem_type,
            "filename": stem.filename,
            "gdrive_file_id": stem.gdrive_file_id,
            "file_size": stem.file_size,
            "created_at": stem.created_at
        } for stem in stems]
    )
    
    return response

@router.get("/generated-music", response_model=GeneratedMusicListResponse)
def list_generated_music(
    proj_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List generated music records for the current user.
    Optionally filter by project ID.
    """
    # Build query
    query = db.query(GeneratedMusic).filter(
        GeneratedMusic.user_id == current_user.id
    )
    
    # Filter by project if specified
    if proj_id is not None:
        query = query.filter(GeneratedMusic.proj_id == proj_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.order_by(GeneratedMusic.created_at.desc()).offset(skip).limit(limit).all()
    
    # Create response
    response = GeneratedMusicListResponse(
        items=[
            GeneratedMusicResponse(
                id=item.id,
                proj_id=item.proj_id,
                user_id=item.user_id,
                text_prompt=item.text_prompt,
                duration=item.duration,
                melody_audio_id=item.melody_audio_id,
                job_id=item.job_id,
                status=item.status,
                progress=item.progress,
                created_at=item.created_at,
                updated_at=item.updated_at,
                completed_at=item.completed_at,
                task_id=item.task_id,
                error_message=item.error_message
            ) for item in items
        ],
        total=total,
        skip=skip,
        limit=limit
    )
    
    return response
