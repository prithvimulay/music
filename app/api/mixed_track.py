from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, List, Optional
import uuid
import datetime
import json

from app.api.auth import get_current_user, get_db
from app.db.models.mixed_track import MixedTrack
from app.db.models.generated_music import GeneratedMusic
from app.db.models.stem import Stem
from app.db.models.project import Project
from app.celeryworker.tasks import mix_stems
from app.schemas.mixed_track import (
    MixedTrackCreate,
    MixedTrackResponse,
    MixedTrackListResponse
)

router = APIRouter()

@router.post("/mix-stems", response_model=MixedTrackResponse, status_code=status.HTTP_202_ACCEPTED)
def create_mixed_track(
    background_tasks: BackgroundTasks,
    mix_data: MixedTrackCreate,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Mix selected stems from a generated music track.
    
    This endpoint:
    1. Validates the project ownership
    2. Checks if the stems are available
    3. Creates a MixedTrack record
    4. Triggers an asynchronous Celery task for mixing
    5. Returns the record ID for status tracking
    """
    # Validate project ownership
    project = db.query(Project).filter(
        Project.id == mix_data.proj_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access to it"
        )
    
    # Check if generated music exists and is completed
    generated_music = db.query(GeneratedMusic).filter(
        GeneratedMusic.id == mix_data.generated_music_id
    ).first()
    
    if not generated_music:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated music not found"
        )
    
    if generated_music.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated music is not ready for mixing (status: {generated_music.status})"
        )
    
    # Check if user has access to the generated music
    if generated_music.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this generated music"
        )
    
    # Check if the requested stems exist
    available_stems = db.query(Stem).filter(
        Stem.generated_music_id == mix_data.generated_music_id,
        Stem.stem_type.in_(mix_data.selected_stems)
    ).all()
    
    if len(available_stems) != len(mix_data.selected_stems):
        # Find which stems are missing
        available_stem_types = [stem.stem_type for stem in available_stems]
        missing_stems = [stem_type for stem_type in mix_data.selected_stems if stem_type not in available_stem_types]
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some requested stems are not available: {missing_stems}"
        )
    
    # Create a filename for the mixed track
    filename = f"mix_{uuid.uuid4().hex[:8]}.wav"
    
    # Create MixedTrack record
    mixed_track = MixedTrack(
        generated_music_id=mix_data.generated_music_id,
        proj_id=mix_data.proj_id,
        user_id=current_user.id,
        selected_stems=json.dumps(mix_data.selected_stems),
        volume_levels=json.dumps(mix_data.volume_levels) if mix_data.volume_levels else None,
        filename=filename,
        status="pending"
    )
    
    db.add(mixed_track)
    db.commit()
    db.refresh(mixed_track)
    
    # Trigger Celery task asynchronously
    task = mix_stems.delay(
        mixed_track_id=mixed_track.id,
        selected_stems=mix_data.selected_stems,
        volume_levels=mix_data.volume_levels
    )
    
    # Update record with task ID
    mixed_track.task_id = task.id
    db.commit()
    
    return MixedTrackResponse(
        id=mixed_track.id,
        generated_music_id=mixed_track.generated_music_id,
        proj_id=mixed_track.proj_id,
        user_id=mixed_track.user_id,
        selected_stems=mix_data.selected_stems,
        volume_levels=mix_data.volume_levels,
        filename=mixed_track.filename,
        status=mixed_track.status,
        created_at=mixed_track.created_at,
        task_id=task.id
    )

@router.get("/mixed-tracks/{mixed_track_id}", response_model=MixedTrackResponse)
def get_mixed_track(
    mixed_track_id: int,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get details of a mixed track.
    """
    # Get the mixed track record
    mixed_track = db.query(MixedTrack).filter(
        MixedTrack.id == mixed_track_id
    ).first()
    
    if not mixed_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mixed track not found"
        )
    
    # Check ownership
    if mixed_track.user_id != current_user.id:
        # Check if user has access to the project
        project = db.query(Project).filter(
            Project.id == mixed_track.proj_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this mixed track"
            )
    
    # Parse JSON fields
    selected_stems = json.loads(mixed_track.selected_stems) if mixed_track.selected_stems else []
    volume_levels = json.loads(mixed_track.volume_levels) if mixed_track.volume_levels else {}
    
    # Create response
    return MixedTrackResponse(
        id=mixed_track.id,
        generated_music_id=mixed_track.generated_music_id,
        proj_id=mixed_track.proj_id,
        user_id=mixed_track.user_id,
        selected_stems=selected_stems,
        volume_levels=volume_levels,
        filename=mixed_track.filename,
        gdrive_file_id=mixed_track.gdrive_file_id,
        file_size=mixed_track.file_size,
        status=mixed_track.status,
        progress=mixed_track.progress,
        error_message=mixed_track.error_message,
        created_at=mixed_track.created_at,
        updated_at=mixed_track.updated_at,
        completed_at=mixed_track.completed_at,
        task_id=mixed_track.task_id
    )

@router.get("/mixed-tracks", response_model=MixedTrackListResponse)
def list_mixed_tracks(
    proj_id: Optional[int] = None,
    generated_music_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List mixed tracks for the current user.
    Optionally filter by project ID or generated music ID.
    """
    # Build query
    query = db.query(MixedTrack).filter(
        MixedTrack.user_id == current_user.id
    )
    
    # Filter by project if specified
    if proj_id is not None:
        query = query.filter(MixedTrack.proj_id == proj_id)
    
    # Filter by generated music if specified
    if generated_music_id is not None:
        query = query.filter(MixedTrack.generated_music_id == generated_music_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.order_by(MixedTrack.created_at.desc()).offset(skip).limit(limit).all()
    
    # Create response
    response = MixedTrackListResponse(
        items=[
            MixedTrackResponse(
                id=item.id,
                generated_music_id=item.generated_music_id,
                proj_id=item.proj_id,
                user_id=item.user_id,
                selected_stems=json.loads(item.selected_stems) if item.selected_stems else [],
                volume_levels=json.loads(item.volume_levels) if item.volume_levels else {},
                filename=item.filename,
                gdrive_file_id=item.gdrive_file_id,
                file_size=item.file_size,
                status=item.status,
                progress=item.progress,
                error_message=item.error_message,
                created_at=item.created_at,
                updated_at=item.updated_at,
                completed_at=item.completed_at,
                task_id=item.task_id
            ) for item in items
        ],
        total=total,
        skip=skip,
        limit=limit
    )
    
    return response
